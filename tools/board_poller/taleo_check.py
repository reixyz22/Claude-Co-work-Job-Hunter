#!/usr/bin/env python3
"""
Taleo checker -- Cook County + any other Taleo careersection.

WHY THIS IS SEPARATE FROM poll_boards.py
----------------------------------------
Taleo's REST endpoint (/careersection/rest/jobboard/searchjobs) is session-locked on
the Cook County instance: three body schemas were tried on 2026-09-01, all returned
HTTP 400 "An Error Occurred in TEE", and the careersection issues no JSESSIONID to a
plain client. So the LIST cannot be fetched headless.

But the DETAIL pages CAN: `jobdetail.ftl?job=<REQ_ID>&lang=en` is fully server-rendered
and returns the whole JD (verified 2026-09-01 against a live req on that board -- minimum quals and
salary both present in the raw HTML).

So this is a two-stage tool, and stage 1 is deliberately manual:

  STAGE 1 (Chrome, ~2 calls, once per sweep)
    navigate  https://cookcountyil.taleo.net/careersection/100/jobsearch.ftl?lang=en
    set "Results per page" to 100   (form_input on the combobox)
    get_page_text                   -> paste/scrape the "Requisition ID: 00139xxx" lines

  STAGE 2 (this script, 0 tokens)
    python3 taleo_check.py --ids <req-id> <req-id> ...
    python3 taleo_check.py --ids-file <workspace>/taleo-ids.txt
    ...fetches each detail page, parses quals/salary/dates, applies the 0-YoE +
    tech-relevance filters, and writes taleo-postings.md.

Do NOT try to brute-force the requisition ID range. The IDs are dense enough that
walking them looks tempting, but probing hundreds of URLs a day is abusive and will
get the pipeline blocked. A browser reads the real list in one call; use that.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "taleo-postings.md")
SEEN = os.path.join(HERE, "taleo-seen.json")

# Registered Taleo careersections. Cook County runs SEVERAL separate ones --
# careersection 100 is "Offices Under the President" ONLY. Sheriff, Clerk of the
# Circuit Court, Assessor, Treasurer, Board of Review and Cook County Health all
# post elsewhere. Add them here as their hosts/sections are confirmed.
SECTIONS = {
    "cookcounty-oup": {
        "host": "cookcountyil.taleo.net",
        "cs": "100",
        "label": "Cook County - Offices Under the President",
        "list_url": "https://cookcountyil.taleo.net/careersection/100/jobsearch.ftl?lang=en",
    },
}

# Titles worth surfacing. Deliberately WIDER than pure SWE: on a public-sector
# board the same work is posted under analyst / systems / IT / business-systems
# titles at least as often as under "software engineer", so a pure-SWE filter
# misses most of what is actually there.
TECH = re.compile(
    r"\b(software|programmer|developer|engineer|application|applications|systems?|"
    r"data|database|information (security|technology)|security|IT|technology|"
    r"technical|analyst|web|network|integration|automation|reporting|business systems)\b",
    re.I)

# Titles that look tech but are not, or are out of level for an early-career search.
OUT_OF_SCOPE = re.compile(
    r"\b(director|chief|deputy|senior|sr\.?|supervisor|manager|managing|principal|"
    r"lead|architect|administrator ii+|physician|nurse|dentist|pharmac|attorney|"
    r"paralegal|investigator|custodial|environmental|forestry|social work|"
    r"clerk|records|food|recreation|medical)\b", re.I)

YEARS = re.compile(
    r"(?:(\d+)|one|two|three|four|five|six|seven|eight|nine|ten)\s*\(?\d*\)?\s*"
    r"(?:\+|or more)?\s*years?", re.I)
WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _clean(raw):
    """Taleo double-encodes JD bodies: %3C/u%3E etc. Unwrap, then strip tags."""
    try:
        raw = urllib.parse.unquote(raw)
    except Exception:
        pass
    raw = raw.replace("%3C", "<").replace("%3E", ">").replace("%22", '"')
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&#39;", "'").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", txt).strip()


def fetch_detail(host, cs, req_id, retries=3):
    url = "https://%s/careersection/%s/jobdetail.ftl?job=%s&lang=en" % (host, cs, req_id)
    for a in range(retries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=30) as resp:
                return url, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and a < retries - 1:
                time.sleep(2 * (a + 1))
                continue
            return url, None
        except Exception:
            if a < retries - 1:
                time.sleep(1 + a)
                continue
            return url, None
    return url, None


def min_years(text):
    """Lowest stated years-of-experience anywhere in the JD. None == no gate found.

    Cook County writes its minimums as an OR-list, e.g.
      'Bachelor's Degree or higher OR High School Diploma and Four (4) years ...'
    A degree-satisfies-it req therefore CONTAINS a years number that does not apply
    to a degree holder. We surface the number but flag degree_ok separately.
    """
    lows = []
    for m in YEARS.finditer(text):
        g = m.group(1)
        if g:
            try:
                lows.append(int(g))
            except ValueError:
                pass
        else:
            w = m.group(0).split()[0].lower()
            if w in WORD_NUM:
                lows.append(WORD_NUM[w])
    return min(lows) if lows else None


def degree_satisfies(text):
    """True when a bachelor's alone clears the minimum quals."""
    t = text.lower()
    pats = [
        r"bachelor'?s degree or higher\s*(?:or|•|$)",
        r"graduation from an accredited college or university with a bachelor'?s degree or higher",
        r"bachelor'?s degree[^.]{0,40}\bor\b[^.]{0,80}high school diploma",
    ]
    return any(re.search(p, t) for p in pats)


def parse(html_raw, url, req_id, label):
    """Taleo detail pages are NOT labelled HTML.

    Layout confirmed 2026-09-01 against a live req on that board:
      - the human title is in  <meta name="title" property="og:title" content="...">
      - every field value sits in one big `!|!`-delimited blob, URL-encoded
        (`%24` for $, `%5C:` for colon), with the JD body HTML-encoded inside it
      - the visible LABELS ("Posting Salary", "Closing Date") come from a separate
        resource bundle that appears BEFORE the values, so label-anchored regexes
        match the bundle and return nothing. Parse the values positionally instead.
    """
    txt = _clean(html_raw)

    m = re.search(r'<meta[^>]+og:title[^>]+content="([^"]+)"', html_raw, re.I)
    if not m:
        m = re.search(r'<meta[^>]+name="title"[^>]+content="([^"]+)"', html_raw, re.I)
    title = _clean(m.group(1)) if m else "(title not parsed)"

    # Field VALUES live in the `!|!` blob. Parse the blob fields directly -- the
    # page's visible labels come from a resource bundle rendered earlier, so any
    # label-anchored regex matches the bundle and returns junk (or nav chrome).
    blob = urllib.parse.unquote(html_raw).replace("\\:", ":")
    parts = [p.strip() for p in blob.split("!|!")]

    salary = ""
    for p in parts:
        m2 = re.match(r"^\$\s?([\d,]+(?:\.\d+)?)\s*-\s*\$?\s?([\d,]+(?:\.\d+)?)\s*/?\s*"
                      r"(Yearly|Hourly|yearly|hourly|HRLY|YEARLY)\.?$", p)
        if m2:
            salary = "$%s - $%s/%s" % (m2.group(1), m2.group(2), m2.group(3))
            break
        m2 = re.match(r"^\$\s?([\d,]+(?:\.\d+)?)\s*/?\s*(Yearly|Hourly|yearly|hourly|HRLY)\.?$", p)
        if m2 and not salary:
            salary = "$%s/%s" % (m2.group(1), m2.group(2))

    # Blob dates run posting-first, then closing. NOTE the closing value is stored
    # in UTC and reads one day LATER than the portal displays (portal: Sep 7
    # 11:59 PM CT -> blob: Sep 8 12:59 AM). Subtracting is not safe across DST, so
    # the report prints the blob date with an explicit warning instead.
    raw_dts = [p for p in parts if re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}", p)]
    dts = []
    for d in raw_dts:                       # blob repeats each date; dedupe in order
        short = ",".join(d.split(",")[:2]).strip()
        if short not in dts:
            dts.append(short)
    posted = dts[0] if dts else ""
    closes = ""
    if len(dts) > 1:                        # closing = latest date after the posting date
        def _k(x):
            try:
                return datetime.strptime(x, "%b %d, %Y")
            except ValueError:
                return datetime.min
        closes = max(dts[1:], key=_k)

    location = ""
    for p in parts:
        if re.match(r"^(Central|North|South|West|East|Far South|Northwest|Southwest|"
                    r"Cook County)\b", p) and len(p) < 120:
            location = p
            break

    return {
        "req_id": req_id,
        "source": label,
        "title": title,
        "url": url,
        "salary": salary,
        "posted": posted,
        "closes": closes,
        "location": location,
        "min_years": min_years(txt),
        "degree_ok": degree_satisfies(txt),
        # "Collective Bargaining Unit" is a LABEL on every page -- only the union
        # NAMES appear as values, so match those.
        "union": bool(re.search(r"\b(AFSCME|SEIU)\b", txt)),
        "grant_funded": bool(re.search(r"grant funded", txt, re.I)),
        "drivers_license": bool(re.search(r"valid driver'?s license", txt, re.I)),
        "safety_sensitive": bool(re.search(r"safety[- ]sensitive", txt, re.I)),
        "oncall_247": bool(re.search(r"work 24/7|24/7, including holidays", txt, re.I)),
        "text_len": len(txt),
    }


def interesting(p):
    """Surface it? Tech-ish title, not obviously out of level, and reachable on quals."""
    t = p["title"]
    if not TECH.search(t):
        return False, "not a tech title"
    if OUT_OF_SCOPE.search(t):
        return False, "title is above level or non-tech"
    if not p["degree_ok"] and (p["min_years"] or 0) >= 2:
        return False, "experience gate %syr, degree does not satisfy" % p["min_years"]
    return True, ""


def load_seen():
    try:
        return set(json.load(open(SEEN)))
    except Exception:
        return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default="cookcounty-oup", choices=sorted(SECTIONS))
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--ids-file")
    ap.add_argument("--all", action="store_true",
                    help="report every req, not just the ones that pass the filter")
    ap.add_argument("--no-seen", action="store_true", help="ignore taleo-seen.json")
    a = ap.parse_args()

    sec = SECTIONS[a.section]
    ids = list(a.ids)
    if a.ids_file:
        raw = open(a.ids_file).read()
        ids += re.findall(r"\b(\d{8})\b", raw)
    ids = [i for i in dict.fromkeys(ids)]
    if not ids:
        print("no requisition IDs given.\n\nStage 1 first -- read the list in Chrome:\n  %s\n"
              "then pass the 'Requisition ID:' values with --ids or --ids-file."
              % sec["list_url"])
        return 2

    seen = set() if a.no_seen else load_seen()
    rows, errors = [], []
    for rid in ids:
        url, html_raw = fetch_detail(sec["host"], sec["cs"], rid)
        if not html_raw:
            errors.append(rid)
            continue
        rows.append(parse(html_raw, url, rid, sec["label"]))
        time.sleep(0.7)

    hits, skipped = [], []
    for p in rows:
        ok, why = interesting(p)
        (hits if ok else skipped).append((p, why))

    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    L = ["# Taleo postings -- %s" % ts,
         "", "Section: **%s** (`%s`)" % (sec["label"], sec["list_url"]),
         "Checked %d requisition(s), %d fetch error(s)." % (len(rows), len(errors)), ""]

    L.append("## Worth a look (%d)" % len(hits))
    if not hits:
        L.append("_none_")
    for p, _ in hits:
        flags = []
        if p["degree_ok"]:
            flags.append("**degree satisfies minimum quals**")
        if p["min_years"]:
            flags.append("JD mentions %syr (check whether it is the OR-branch)" % p["min_years"])
        if p["union"]:
            flags.append("UNION req -- check for internal-bid seniority language")
        if p["grant_funded"]:
            flags.append("GRANT FUNDED (term/funding risk)")
        if p["drivers_license"]:
            flags.append("requires driver's license + auto insurance")
        if p["safety_sensitive"]:
            flags.append("safety-sensitive: drug screen")
        if p["oncall_247"]:
            flags.append("24/7 availability language")
        star = " **NEW**" if p["req_id"] not in seen else ""
        L += ["", "- **%s** (%s)%s" % (p["title"], p["req_id"], star),
              "  - %s | posted %s | **closes %s**" % (p["salary"] or "salary n/s",
                                                      p["posted"] or "?", p["closes"] or "?"),
              "  - %s" % (p["location"] or "location n/s"),
              "  - %s" % ("; ".join(flags) if flags else "no special flags"),
              "  - %s" % p["url"]]

    L += ["", "## Filtered out (%d)" % len(skipped)]
    for p, why in skipped:
        L.append("- %s (%s) -- %s" % (p["title"], p["req_id"], why))
    if errors:
        L += ["", "## Fetch errors", "- " + ", ".join(errors)]

    open(OUT, "w").write("\n".join(L) + "\n")
    if not a.no_seen:
        json.dump(sorted(set(list(seen) + [p["req_id"] for p in rows])),
                  open(SEEN, "w"))
    print("checked %d, %d worth a look, %d filtered, %d errors -> %s"
          % (len(rows), len(hits), len(skipped), len(errors), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
