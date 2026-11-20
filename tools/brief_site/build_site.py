#!/usr/bin/env python3
"""
Parse the workspace's markdown into the JSON the dashboard renders.

Reads:  brief-YYYY-MM-DD-{1am,6am}.md, applied.md, ghost.md, holds.md,
        skills-to-learn.md, applications/*/
Writes: data/briefs.json, data/leads.json, data/stats.json

Everything here is read-only against the workspace. The dashboard never
mutates a markdown file; only a sweep does, by draining the event log.
"""
import json, os, re, sys, glob
from datetime import datetime, timezone, date


def find_root(explicit=None):
    """Locate the workspace. Order: --root, $JOBHUNT_ROOT, walk up from this file
    looking for CLAUDE.md, then the Linux-mount default. Written this way because
    the same files run from a Windows folder, a WSL mount and a plugin install,
    and a hard-coded ~/mnt/Claude silently finds nothing on two of the three."""
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("JOBHUNT_ROOT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(d, "CLAUDE.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.expanduser("~/mnt/Claude")



ROOT = None  # resolved in main()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# --- freshness gate (2026-11-18): 14 days hard kill, internships exempt ---
MAX_AGE_DAYS = 14

AGE_RE = re.compile(r"(\d+)\s*(day|days|d|week|weeks|w|hour|hours|h|month|months|mo)\b", re.I)
INTERN_RE = re.compile(r"\bintern(ship)?\b|\bco-?op\b|summer\s+20\d\d\s+program", re.I)
CLOSE_RE = re.compile(r"clos(?:es|ing|e date)[^0-9]{0,12}(20\d\d-\d\d-\d\d)", re.I)


def age_days(age_text):
    """Days old from an EMPLOYER-SOURCED age string. None when unparseable --
    which is NOT 'fresh' and NOT 'old'. Older briefs used different columns, so
    unknown here usually means this parser's gap, not an undated posting."""
    if not age_text:
        return None
    t = str(age_text)
    if re.search(r"\btoday\b", t, re.I):
        return 0
    if re.search(r"\byesterday\b", t, re.I):
        return 1
    m = AGE_RE.search(t)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("w"):
        return n * 7
    if unit.startswith("mo"):
        return n * 30
    if unit.startswith("h"):
        return 0
    return n


def is_internship(*fields):
    return any(INTERN_RE.search(str(f or "")) for f in fields)


def closes_on(*fields):
    for f in fields:
        m = CLOSE_RE.search(str(f or ""))
        if m:
            return m.group(1)
    return None


BRIEF_RE = re.compile(r"(?:brief|email-check)-(\d{4}-\d{2}-\d{2})-(\dam|\d+am|\d+pm)[^/]*\.md$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s|)\]]+")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
TABLE_HEAD_RE = re.compile(r"^#{1,4}\s*(links and materials|links & materials)", re.I)

# Column name -> the keywords that identify it in a header row. Brief tables have
# used 3, 5 and 7 columns across 63 briefs; assuming a fixed shape silently
# mis-maps cells (comp read as age, link column never read at all), which is
# exactly how leads ended up on the dashboard with no apply button.
COLUMN_KEYS = [
    ("rank",      ("#", "item", "rank")),
    ("title",     ("employer", "lead", "role", "company", "item")),
    ("location",  ("where", "location", "loc")),
    ("comp",      ("pay", "comp", "salary")),
    ("age",       ("age", "posted", "freshness", "employer-side", "date")),
    ("url",       ("link", "apply", "url")),
    ("materials", ("material", "status")),
]


def clean(s):
    s = BOLD_RE.sub(r"\1", s or "")
    s = LINK_RE.sub(r"\1", s)
    return s.replace("`", "").strip()


def any_url(*cells):
    for c in cells:
        if not c:
            continue
        m = LINK_RE.search(c)
        if m and m.group(2).startswith("http"):
            return m.group(2)
        m = BARE_URL_RE.search(c)
        if m:
            return m.group(0).rstrip(".,;")
    return None


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def map_columns(header_cells):
    """Header-driven mapping. Returns {field: index}. A field only binds once,
    to the first column whose header mentions one of its keywords."""
    mapping, taken = {}, set()
    low = [c.lower() for c in header_cells]
    for field, keys in COLUMN_KEYS:
        for i, h in enumerate(low):
            if i in taken or field in mapping:
                continue
            if any(k in h for k in keys):
                mapping[field] = i
                taken.add(i)
                break
    return mapping


def ats_kind(url):
    if not url:
        return "none"
    u = url.lower()
    for key, name in [
        ("greenhouse", "greenhouse"), ("lever.co", "lever"), ("ashbyhq", "ashby"),
        ("myworkdayjobs", "workday"), ("smartrecruiters", "smartrecruiters"),
        ("workable", "workable"), ("icims", "icims"), ("breezy", "breezy"),
        ("applicantstack", "applicantstack"), ("paylocity", "paylocity"),
        ("joinhandshake", "handshake"), ("taleo", "taleo"), ("recruitee", "recruitee"),
        ("jobvite", "jobvite"), ("rippling", "rippling"), ("google.com/search", "search"),
    ]:
        if key in u:
            return name
    return "careers"


def employer_of(title):
    """'Acme — Associate SWE I (R001)' -> 'acme'. Used for detail matching,
    dedupe and the deprioritised list."""
    t = re.split(r"\s+[—\-–|]\s+|\s*\(", title or "", 1)[0]
    t = re.sub(r"\b(inc|llc|ltd|corp|co|group|solutions|technologies|systems)\b\.?", "", t, flags=re.I)
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def guess_url(title, location=""):
    """He asked for a best guess when there is no exact link, rather than a dead
    button. A scoped search lands on the employer's own careers page most of the
    time, and is labelled as a guess in the UI so it is never mistaken for a
    verified apply link."""
    emp = employer_of(title)
    role = ""
    parts = re.split(r"\s+[—\-–|]\s+", title or "", 1)
    if len(parts) > 1:
        role = re.sub(r"\([^)]*\)", "", parts[1]).strip()
    q = " ".join(x for x in [emp, role, "careers apply"] if x)
    from urllib.parse import quote_plus
    return "https://www.google.com/search?q=" + quote_plus(q)


def find_detail(text, title):
    """Attach the brief's own write-up to a lead by EMPLOYER NAME, not by rank.
    Rank matching only ever caught the top few; everything else rendered bare."""
    emp = employer_of(title)
    if not emp or len(emp) < 3:
        return None, None
    needle = emp.split()[0]
    lines = text.splitlines()

    # 1) a narrative section whose heading names the employer
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s", line) and needle in line.lower():
            body = []
            for nxt in lines[i + 1:]:
                if re.match(r"^#{2,3}\s", nxt):
                    break
                body.append(nxt)
            b = "\n".join(body).strip()
            if len(b) > 60:
                return b, "section"

    # 2) a one-liner bullet, plus its continuation lines
    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*]\s", line) and needle in line.lower():
            body = [line.strip().lstrip("-* ").strip()]
            for nxt in lines[i + 1:]:
                if re.match(r"^\s*[-*]\s", nxt) or re.match(r"^#{1,3}\s", nxt) or not nxt.strip():
                    break
                body.append(nxt.strip())
            b = " ".join(body).strip()
            if len(b) > 50:
                return b, "one-liner"
    return None, None


def summarize(detail, limit=240):
    """Two-sentence gist for the collapsed card."""
    if not detail:
        return ""
    t = re.sub(r"\s+", " ", BOLD_RE.sub(r"\1", LINK_RE.sub(r"\1", detail))).strip()
    t = re.sub(r"https?://\S+", "", t).strip()
    # briefs often open a section with "Apply: <url>" -- that is chrome, not content
    t = re.sub(r"^\s*(apply|link|apply link)\s*:?\s*", "", t, flags=re.I).strip()
    t = re.sub(r"^[\s·•\-–—|]+", "", t).strip()
    out, n = [], 0
    for sent in re.split(r"(?<=[.!?])\s+", t):
        if not sent:
            continue
        out.append(sent)
        n += len(sent)
        if n >= limit or len(out) >= 2:
            break
    return " ".join(out).strip()


def parse_brief(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = BRIEF_RE.search(os.path.basename(path))
    d, slot = (m.group(1), m.group(2)) if m else ("", "")

    leads, in_table, cols = [], False, None
    for line in text.splitlines():
        s_ = line.strip()
        if TABLE_HEAD_RE.match(s_):
            in_table, cols = True, None
            continue
        if not in_table:
            continue
        if s_.startswith("|"):
            cells = split_row(s_)
            if all(set(c) <= set("-: ") for c in cells):      # separator row
                continue
            if cols is None:                                   # first row = header
                cols = map_columns(cells)
                continue
            def cell(name):
                i = cols.get(name)
                return cells[i] if i is not None and i < len(cells) else ""
            title = clean(cell("title"))
            if not title or title.lower().startswith(("employer", "lead", "item", "#", "(no ")):
                continue
            # Kill detail stays out of sight (2026-11-18 design rule): a row the
            # brief itself marks KILLED is screened out, never a lead card.
            if re.search(r"\bKILL(ED)?\b", s_):
                continue
            url = any_url(cell("url"), *cells)
            guessed = False
            if not url:
                url = guess_url(title, clean(cell("location")))
                guessed = True
            age_txt = clean(cell("age"))
            ad = age_days(age_txt)
            intern = is_internship(title, age_txt)
            detail, dsrc = find_detail(text, title)
            mats = clean(cell("materials"))
            leads.append({
                "rank": clean(cell("rank")),
                "title": title,
                "employer": employer_of(title),
                "location": clean(cell("location")),
                "comp": clean(cell("comp")),
                "age": age_txt,
                "age_days": ad,
                "internship": intern,
                "closes": closes_on(age_txt, mats),
                "expired": bool(ad is not None and ad > MAX_AGE_DAYS and not intern),
                "url": url,
                "url_guess": guessed,
                "ats": ats_kind(url),
                "materials": mats,
                # "NOT BUILT" contains "BUILT": that used to mark every unbuilt lead ready
                "ready": bool(re.search(r"\bREADY\b|(?<!NOT )\bBUILT\b", mats.upper()))
                         and not re.search(r"\bNOT (BUILT|READY|RECOMMENDED)\b", mats.upper()),
                "detail": detail or "",
                "detail_source": dsrc or "",
                "summary": summarize(detail),
                "brief_date": d,
                "brief_slot": slot,
            })
            continue
        if s_ and not s_.startswith("|"):
            in_table = False

    sections = []
    cur = None
    for line in text.splitlines():
        if re.match(r"^##\s+", line):
            if cur:
                sections.append(cur)
            cur = {"heading": line.lstrip("# ").strip(), "body": []}
        elif cur:
            cur["body"].append(line)
    if cur:
        sections.append(cur)
    for s_ in sections:
        s_["body"] = "\n".join(s_["body"]).strip()

    return {"date": d, "slot": slot, "file": os.path.basename(path),
            "leads": leads, "sections": sections, "bytes": len(text), "raw": text}


def load_applied():
    p = os.path.join(ROOT, "applied.md")
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
            if not m or "|" not in m.group(2):
                continue  # skip prose lists inside the carve-out notes
            n, rest = m.group(1), m.group(2)
            parts = [x.strip() for x in rest.split("|")]
            status = ""
            for x in parts:
                sm = re.search(r"Status:\s*\*{0,2}([A-Z]+)", x)
                if sm:
                    status = sm.group(1)
            out.append({
                "n": int(n),
                "company": parts[0] if parts else rest[:60],
                "role": parts[1] if len(parts) > 1 else "",
                "status": status or "PENDING",
            })
    return out


def count_reds():
    """Adblocker-style counter. No detail surfaced anywhere, by design --
    just the number, so the screening work is visible without being noise."""
    kills = 0
    g = os.path.join(ROOT, "ghost.md")
    if os.path.exists(g):
        with open(g, encoding="utf-8") as f:
            for line in f:
                if re.match(r"^(RED|YELLOW|GREEN)\s*\|", line.strip()):
                    kills += 1
    # plus everything named in a brief's kill sections
    for p in glob.glob(os.path.join(ROOT, "brief-*.md")):
        try:
            with open(p, encoding="utf-8") as f:
                t = f.read()
        except Exception:
            continue
        kills += len(re.findall(r"^\s*[-•]\s+\*\*[^*]+\*\*.*(?:KILL|killed|404|gate)", t, re.M | re.I))
    return kills


def _user_name():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("config.json", "config.example.json"):
        try:
            return (json.load(open(os.path.join(here, name), encoding="utf-8")).get("user_name") or "").strip()
        except Exception:
            continue
    return ""


def main():
    global ROOT
    ROOT = find_root(os.environ.get("JOBHUNT_ROOT"))
    os.makedirs(OUT, exist_ok=True)
    # 1pm email checks are briefs too (2026-11-19: "make sure this part is
    # plugged into the job center"). Order by date then slot, newest first, so the
    # two filename prefixes interleave correctly.
    def _order(p):
        m = BRIEF_RE.search(os.path.basename(p))
        if not m:
            return ("", 0)
        sl = m.group(2)
        h = int(re.match(r"\d+", sl).group()) % 12 + (12 if sl.endswith("pm") else 0)
        return (m.group(1), h)
    paths = sorted(glob.glob(os.path.join(ROOT, "brief-*.md"))
                   + glob.glob(os.path.join(ROOT, "email-check-*.md")),
                   key=_order, reverse=True)
    briefs = []
    for p in paths:
        try:
            briefs.append(parse_brief(p))
        except Exception as e:
            print(f"  ! skipped {os.path.basename(p)}: {e}", file=sys.stderr)

    # Dedupe by MERGING, newest-first. The same lead appears in several briefs and
    # the tables differ in width -- a 3-column 6am table has no comp or age, a
    # 7-column 1am table has both. Taking whichever brief came first threw away
    # real data and produced the "decorative" rows. Newest wins on conflict;
    # anything blank is backfilled from older sightings.
    MERGE_FILL = ("comp", "location", "age", "age_days", "url", "detail",
                  "summary", "materials", "closes", "rank", "detail_source")
    by_key, order = {}, []
    for b in briefs:
        for L in b["leads"]:
            base = (L.get("url") if not L.get("url_guess") else "") or L["title"]
            key = re.sub(r"[^a-z0-9]+", "-", base.lower())[:80].strip("-")
            L["key"] = key
            if key not in by_key:
                by_key[key] = L
                order.append(key)
                L["sightings"] = 1
                continue
            cur = by_key[key]
            cur["sightings"] = cur.get("sightings", 1) + 1
            for f in MERGE_FILL:
                if not cur.get(f) and L.get(f):
                    cur[f] = L[f]
            # a real link always beats a guessed one
            if cur.get("url_guess") and L.get("url") and not L.get("url_guess"):
                cur["url"], cur["url_guess"], cur["ats"] = L["url"], False, L["ats"]
            if L.get("ready"):
                cur["ready"] = True
    leads = [by_key[k] for k in order]

    # --- the JD itself (2026-11-19: "click to expand is supposed to show
    # a JD, not your thoughts"). Found through the path the brief puts in the
    # Materials cell: an applications/<folder>/ (its jd.md) or a jds/<file>.md.
    jd_re = re.compile(r"((?:applications/[\w.\-]+/?)|(?:jds/[\w.\-]+\.md))")
    for L in leads:
        L["jd"], L["jd_source"] = "", ""
        for m in jd_re.finditer(L.get("materials") or ""):
            rel = m.group(1)
            fp = (os.path.join(ROOT, rel.rstrip("/"), "jd.md") if rel.startswith("applications")
                  else os.path.join(ROOT, rel))
            if os.path.isfile(fp):
                try:
                    L["jd"] = open(fp, encoding="utf-8", errors="replace").read()[:30000]
                    L["jd_source"] = os.path.relpath(fp, ROOT).replace(os.sep, "/")
                except Exception:
                    pass
                break

    # --- deprioritised companies (config.json, hand-editable) ---
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(cfg_path):  # config.json is personal + gitignored
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.json")
    depri = []
    if os.path.exists(cfg_path):
        try:
            depri = json.load(open(cfg_path, encoding="utf-8")).get("deprioritized_companies", [])
        except Exception:
            depri = []
    for L in leads:
        hay = (L.get("employer", "") + " " + L.get("title", "")).lower()
        for d in depri:
            if d.get("match", "").lower() in hay:
                L["deprioritized"] = True
                L["depri_reason"] = d.get("reason", "")
                break
    # sink them to the bottom without removing them
    leads.sort(key=lambda L: 1 if L.get("deprioritized") else 0)

    if not briefs or not any(b["leads"] for b in briefs):
        # A workspace with no briefs is almost always a wrong --root, not an
        # empty pipeline. Refuse rather than overwrite good JSON with nothing.
        print(f"REFUSING TO WRITE: parsed {len(briefs)} brief(s) but extracted 0 leads "
              f"under {ROOT}. That is a parser failure, not an empty pipeline -- "
              f"existing data/*.json left untouched.", file=sys.stderr)
        return

    applied = load_applied()
    today = date.today().isoformat()
    latest = briefs[0]["date"] if briefs else ""

    with open(os.path.join(OUT, "briefs.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in b.items() if k != "raw"} for b in briefs],
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "briefs_raw.json"), "w", encoding="utf-8") as f:
        json.dump({b["file"]: b["raw"] for b in briefs[:40]}, f, ensure_ascii=False)
    with open(os.path.join(OUT, "leads.json"), "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as f:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "today": today,
            "latest_brief": latest,
            "user_name": _user_name(),
            "brief_count": len(briefs),
            "lead_count": len(leads),
            "ready_count": sum(1 for L in leads if L["ready"]),
            "applied": applied,
            "applied_count": len(applied),
            "screened_out": count_reds(),
            "stale": latest != today,
        }, f, ensure_ascii=False, indent=1)
    print(f"built: {len(briefs)} briefs, {len(leads)} leads, "
          f"{len(applied)} applied, {count_reds()} screened out")


if __name__ == "__main__":
    main()
