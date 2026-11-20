#!/usr/bin/env python3
"""
Parse events.md (the IRL Event Finder's append-only log) and applied.md into the
calendar / history JSON the dashboard renders.

Reads:  events.md, applied.md, brief-*.md / email-check-*.md (dates only)
Writes: data/events.json, data/history_static.json

Read-only on the workspace, same contract as build_site.py. Kept as its own
file so the event finder and the job sweeps can evolve without editing each
other's parser.

events.md conventions this understands (see skills/event-finder/SKILL.md):
  ## YYYY-MM-DD (...run...)          -> a run; its year anchors undated "Nov 17"
  ### Ranked / One-liners / New ...  -> surfaced events, one per line
  ### Killed ...                     -> | Event | Reason | table
  STATUS | <title> | YYYY-MM-DD | WENT|GOING|SKIPPED|MISSED | <note>
                                     -> the user's outcome for an event
"""
import json, os, re, sys, glob, hashlib
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DATE_RE = re.compile(
    r"\b(?:(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+)?"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?!\d)", re.I)
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:-|–|to)?\s*(?:\d{1,2}(?::\d{2})?\s*)?(am|pm)\b", re.I)
STARTS_RE = re.compile(r"STARTS\s+(\d{1,2})(?::(\d{2}))?\s*(AM|PM)", re.I)
LEAVE_RE = re.compile(r"LEAVE BY\s+(~?\d{1,2}(?::\d{2})?\s*(?:AM|PM))", re.I)
ENDS_RE = re.compile(r"ends\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM))", re.I)
URL_RE = re.compile(r"((?:https?://)?(?:www\.)?(?:luma\.com|lu\.ma|meetup\.com|eventbrite\.com|chipy\.org|"
                    r"chicookworks\.org|hackerx\.org|devpost\.com|mlh\.io)/[^\s)|,*\"']+)", re.I)
TIER_RE = re.compile(r"\bT([1-5])\b(\+)?")
COST_RE = re.compile(r"\b(free|\$\d+(?:\.\d\d)?)\b", re.I)
STATUS_RE = re.compile(r"^\s*\*{0,2}STATUS\*{0,2}\s*\|", re.I)

SURFACE_SEC = re.compile(r"ranked|one-liner|surfaced|new finds|still live|carried|leads to resolve", re.I)
KILL_SEC = re.compile(r"killed", re.I)


def find_root(explicit=None):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("JOBHUNT_ROOT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    d = HERE
    for _ in range(6):
        if os.path.exists(os.path.join(d, "CLAUDE.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.expanduser("~/mnt/Claude")


def strip_md(s):
    s = re.sub(r"\*\*|__|`", "", s)
    s = re.sub(r"(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)", "", s)
    return s.strip()


def norm_title(t):
    t = strip_md(t).lower()
    t = re.sub(r"^(?:[-•*]\s*)?(?:★\s*)?(?:\d+\.\s*)?(?:t5:\s*)?", "", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    words = [w for w in t.split() if w not in ("the", "a", "an", "chicago", "meetup", "new", "nov",
                                                 "november", "december", "dec", "oct")]
    return " ".join(words[:7])


def resolve_date(mon, day, run_date):
    m = MONTHS.get(mon[:3].lower())
    if not m:
        return None
    y = run_date.year
    # an event logged in a December run for "Jan 14" is next year
    if m < run_date.month - 6:
        y += 1
    try:
        return date(y, m, int(day))
    except ValueError:
        return None


def fmt_time(h, mi, ap):
    return f"{int(h)}:{mi or '00'} {ap.upper()}"


def to24(t):
    m = re.match(r"~?(\d{1,2})(?::(\d{2}))?\s*(AM|PM)", t or "", re.I)
    if not m:
        return ""
    h = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "PM" else 0)
    return f"{h:02d}:{m.group(2) or '00'}"


def parse_line(line, run_date, section):
    raw = line.rstrip()
    body = raw.lstrip("-•* ").strip()
    if "|" not in body:
        return None
    t5 = bool(re.match(r"\*{0,2}T5:", body))
    flat = strip_md(body)
    flat = re.sub(r"^T5:\s*", "", flat)
    # split head (pipe fields) from the trailing description after " - "
    head, desc = flat, ""
    m = re.search(r"\s(?:-|—)\s(?=[A-Z\"'(])", flat)
    parts = [p.strip() for p in flat.split("|")]
    title = re.sub(r"^(?:★\s*)?(?:\d+\.\s*)", "", parts[0]).strip(" .")
    if len(title) < 10 and len(parts) > 2 and not DATE_RE.search(parts[1]):
        title = f"{title} | {parts[1]}"
        parts = [title] + parts[2:]
    if not title or len(title) < 4:
        return None
    rest = " | ".join(parts[1:])
    # description = text after the last pipe-field that is followed by " - "
    dm = re.search(r"\|\s*[^|]*?\b(?:NEW|CARRIED[^|-]*|T[1-5][^|-]*)\s+-\s+(.*)$", flat)
    if dm:
        desc = dm.group(1).strip()
    dt = None
    for p in parts[1:] + [parts[0]]:
        mm = DATE_RE.search(p)
        if mm:
            dt = resolve_date(mm.group(2), mm.group(3), run_date)
            if dt:
                break
    if not dt:
        return None
    start = leave = end = ""
    sm = STARTS_RE.search(rest)
    if sm:
        start = fmt_time(*sm.groups())
    else:
        for p in parts[1:]:
            if DATE_RE.search(p):
                after = p[DATE_RE.search(p).end():]
                tm = TIME_RE.search(after) or TIME_RE.search(p)
                if tm:
                    start = fmt_time(tm.group(1), tm.group(2), tm.group(3))
                else:
                    bm = re.match(r"[\s,]*(\d{1,2})(?::(\d{2}))?(?!\d)", after)
                    if bm and 1 <= int(bm.group(1)) <= 11:
                        h = int(bm.group(1))
                        start = fmt_time(h, bm.group(2), "AM" if 8 <= h <= 11 else "PM")
                break
    lm = LEAVE_RE.search(rest)
    if lm:
        leave = lm.group(1).lstrip("~")
    em = ENDS_RE.search(rest)
    if em:
        end = em.group(1)
    venue = ""
    for p in parts[1:]:
        if DATE_RE.search(p) or STARTS_RE.search(p):
            continue
        if COST_RE.fullmatch(p.split(",")[0].strip()) or re.match(r"^(free|\$)", p, re.I):
            continue
        if re.match(r"^T[1-5]", p):
            continue
        if len(p) > 4:
            venue = p[:140]
            break
    cost = ""
    for p in parts[1:]:
        cm = COST_RE.search(p)
        if cm and len(p) < 70:
            cost = p[:60]
            break
    tier = "T5" if t5 else ""
    if not tier:
        tm = TIER_RE.search(rest)
        if tm:
            tier = "T" + tm.group(1) + (tm.group(2) or "")
    catch = ""
    cm = re.search(r"CATCH:\s*(.+)$", flat)
    if cm:
        catch = cm.group(1).strip()
    url = ""
    um = URL_RE.search(raw)
    if um:
        url = um.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        url = url.rstrip(".;:")
    if not desc:
        desc = " | ".join(parts[2:])[:600]
    return {
        "title": title[:160], "date": dt.isoformat(), "start": start, "start24": to24(start),
        "leave_by": leave, "end": end, "venue": venue, "cost": cost, "tier": tier,
        "catch": catch[:500], "url": url, "desc": desc[:900], "line": raw[:1600],
        "section": section, "rank": (re.match(r"\*{0,2}(\d+)\.", body) or [None, ""])[1] or "",
        "social": t5 or tier == "T5",
    }


STOP = set("the a an of and with on in at for by to x chicago meetup group user talk talks night "
           "nov november dec december oct october tue wed thu mon fri sat sun building ai data how can "
           "your from tech new agentic engineering community events event".split())


def toks(t):
    return {w for w in re.sub(r"[^a-z0-9 ]+", " ", strip_md(t).lower()).split()
            if w not in STOP and len(w) > 1}


def same_event(a, b):
    if a["date"] != b["date"]:
        return False
    ta, tb = toks(a["title"]), toks(b["title"])
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return bool(a["url"] and a["url"] == b["url"]) or (inter >= 1 and inter / min(len(ta), len(tb)) >= 0.6)


FILL = ("start", "start24", "leave_by", "end", "venue", "cost", "tier", "catch", "url", "rank")


def merge_same_day(evs):
    """Runs re-log the same event under slightly different names ("Data Night:
    Jane Doe (Acme)" vs "Data Night (Jane Doe)"). Collapse
    them: the most recently logged version wins, gaps are filled from the others,
    and the longest description is kept."""
    groups = []
    for e in sorted(evs, key=lambda x: x["last_seen"]):
        for g in groups:
            if any(same_event(e, o) for o in g):
                g.append(e)
                break
        else:
            groups.append([e])
    out = []
    for g in groups:
        g.sort(key=lambda x: (x["last_seen"], len(x["line"])))
        best = dict(g[-1])
        for o in reversed(g[:-1]):
            for k in FILL:
                if not best.get(k) and o.get(k):
                    best[k] = o[k]
        richest = max(g, key=lambda x: len(x["desc"]))
        if len(richest["desc"]) > len(best["desc"]) * 1.5:
            best["desc"] = richest["desc"]
        best["first_seen"] = min(x["first_seen"] for x in g)
        best["runs"] = sum(x["runs"] for x in g)
        best["aliases"] = sorted({x["title"] for x in g} - {best["title"]})
        best["history"] = [{"run": x["last_seen"], "line": x["line"]} for x in g]
        out.append(best)
    out.sort(key=lambda e: (e["date"], e["start24"] or "99"))
    return out


def parse_events(path):
    if not os.path.exists(path):
        return [], [], {}
    text = open(path, encoding="utf-8", errors="replace").read()
    run_date, section = None, ""
    events, kills, status = {}, [], {}
    in_kill_table = False
    for line in text.splitlines():
        h2 = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
        if h2:
            run_date = datetime.strptime(h2.group(1), "%Y-%m-%d").date()
            section, in_kill_table = "", False
            continue
        h3 = re.match(r"^###\s+(.*)", line)
        if h3:
            section = h3.group(1).strip()
            in_kill_table = bool(KILL_SEC.search(section))
            continue
        if STATUS_RE.match(line):
            f = [x.strip() for x in strip_md(line).split("|")]
            if len(f) >= 4:
                status[norm_title(f[1])] = {"title": f[1], "date": f[2], "status": f[3].upper(),
                                            "note": f[4] if len(f) > 4 else ""}
            continue
        if not run_date:
            continue
        if in_kill_table and line.strip().startswith("|"):
            cells = [strip_md(c) for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and not re.match(r"^:?-+", cells[0]) and cells[0].lower() != "event":
                kills.append({"run": run_date.isoformat(), "event": cells[0][:200],
                              "reason": cells[1][:400]})
            continue
        if not SURFACE_SEC.search(section):
            continue
        if not (line.startswith("**") or line.startswith("- ")):
            continue
        ev = parse_line(line, run_date, section)
        if not ev:
            continue
        key = norm_title(ev["title"]) + "@" + ev["date"]
        ev["id"] = "ev-" + hashlib.sha1(key.encode()).hexdigest()[:10]
        prev = events.get(key)
        ev["first_seen"] = prev["first_seen"] if prev else run_date.isoformat()
        ev["runs"] = (prev["runs"] if prev else 0) + 1
        ev["last_seen"] = run_date.isoformat()
        # later runs win, but don't let a terse one-liner erase a detailed write-up
        if prev and len(prev["line"]) > len(ev["line"]) * 1.8 and ev["section"].lower().startswith("one"):
            for k in ("first_seen", "runs", "last_seen"):
                prev[k] = ev[k]
            continue
        events[key] = ev
    events = merge_same_day(list(events.values()))
    # killed-this-run titles mark a surfaced event dead
    killed_norm = {}
    for k in kills:
        killed_norm.setdefault(norm_title(k["event"])[:30], k)
    out = []
    for ev in events:
        nt = norm_title(ev["title"])
        k = killed_norm.get(nt[:30])
        if k and k["run"] >= ev["last_seen"]:
            ev["killed"] = k["reason"]
        st = status.get(nt)
        if not st:
            for sk, sv in status.items():
                if sk and (sk in nt or nt in sk) and sv.get("date", "")[:10] == ev["date"]:
                    st = sv
                    break
        if st:
            ev["status"] = st["status"]
            ev["status_note"] = st["note"]
            um = URL_RE.search(st["note"])
            if um and not ev.get("url"):
                ev["url"] = "https://" + um.group(1) if not um.group(1).startswith("http") else um.group(1)
        out.append(ev)
    out.sort(key=lambda e: (e["date"], e["start24"] or "99"))
    return out, kills, status


def parse_applied(path):
    """-> [{date, company, role, status}] from 'Applied <date>' in applied.md"""
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\d+[a-z]?)\.\s+(.*)", line.strip())
        if not m or "|" not in line:
            continue
        f = [x.strip() for x in m.group(2).split("|")]
        if len(f) < 3 or "NOT APPLIED" in line[:400] or "DUPLICATE" in line[:200]:
            continue
        ap = next((x for x in f if x.lower().startswith("applied")), "")
        d = None
        im = re.search(r"(20\d\d)-(\d\d)-(\d\d)", ap)
        if im:
            d = date(int(im.group(1)), int(im.group(2)), int(im.group(3)))
        else:
            mm = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+(20\d\d)", ap, re.I)
            if mm:
                try:
                    d = date(int(mm.group(3)), MONTHS[mm.group(1)[:3].lower()], int(mm.group(2)))
                except ValueError:
                    d = None
        if not d:
            continue
        stm = re.search(r"Status:\s*\**([A-Z][A-Z \-/]+)", line)
        role = f[1] if len(f) > 1 and not f[1].lower().startswith("applied") else ""
        out.append({"date": d.isoformat(), "n": m.group(1), "company": f[0][:80],
                    "role": role[:140],
                    "status": (stm.group(1).strip() if stm else "")[:30]})
    return out


def main():
    root = find_root(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None)
    os.makedirs(OUT, exist_ok=True)
    events, kills, status = parse_events(os.path.join(root, "events.md"))
    applied = parse_applied(os.path.join(root, "applied.md"))

    sweeps = {}
    for p in glob.glob(os.path.join(root, "brief-*.md")) + glob.glob(os.path.join(root, "email-check-*.md")):
        m = re.search(r"(20\d\d-\d\d-\d\d)", os.path.basename(p))
        if m:
            sweeps.setdefault(m.group(1), []).append(os.path.basename(p))

    days = {}
    def add(d, item):
        days.setdefault(d, []).append(item)
    for a in applied:
        add(a["date"], {"kind": "applied", "label": f"Applied: {a['company']}" + (f" — {a['role']}" if a["role"] else ""),
                        "detail": a["status"], "source": "applied.md"})
    for ev in events:
        if ev.get("status") in ("WENT", "ATTENDED"):
            add(ev["date"], {"kind": "event", "label": f"Went to {ev['title']}",
                             "detail": ev.get("status_note", ""), "source": "events.md"})
    for d, files in sweeps.items():
        add(d, {"kind": "sweep", "label": f"{len(files)} pipeline run{'s' if len(files) != 1 else ''}",
                "detail": ", ".join(sorted(files)), "source": "workspace"})

    tmp = os.path.join(OUT, "events.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().isoformat(timespec="seconds"),
                   "events": events, "kills": kills[-400:]}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(OUT, "events.json"))
    tmp = os.path.join(OUT, "history_static.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"days": days}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(OUT, "history_static.json"))
    up = [e for e in events if e["date"] >= date.today().isoformat()]
    print(f"events: {len(events)} parsed ({len(up)} upcoming), {len(kills)} kills, "
          f"{len(status)} status lines; history: {len(applied)} applications over {len(days)} days")


if __name__ == "__main__":
    main()
