#!/usr/bin/env python3
"""board_poller -- poll company ATS boards directly, report only what is new.

Stdlib only. No `pip install`. See README.md for the design.

Verified live (2026-08-05, real endpoints): greenhouse, lever, ashby.
Verified live: workday (limit=20 + pagination + browser UA). Unsupported (registered as skip): icims,
taleo, successfactors, ukg.

The diff is the point: seen.json remembers every posting id ever fetched, so each
run after the first surfaces only what appeared since last time. The first run for a
set of boards shows everything currently open (useful baseline), then it is diffs.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import urljoin
import html as _html
from datetime import datetime, timezone

HERE     = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.environ.get("BOARD_REGISTRY", os.path.join(HERE, "registry.json"))
SEEN     = os.environ.get("BOARD_SEEN",     os.path.join(HERE, "seen.json"))
OUT_JSON = os.environ.get("BOARD_OUT",      os.path.join(HERE, "new-postings.json"))
OUT_MD   = os.environ.get("BOARD_OUT_MD",   os.path.join(HERE, "new-postings.md"))
# --standing writes here (separate file so it never clobbers the diff output).
STANDING_JSON = os.environ.get("BOARD_STANDING",    os.path.join(HERE, "standing-postings.json"))
STANDING_MD   = os.environ.get("BOARD_STANDING_MD", os.path.join(HERE, "standing-postings.md"))
# Workspace root (where applied.md / ghost.md live). Default: three levels up from
# tools/board_poller -> the mounted workspace dir.
WORKSPACE = os.environ.get("WORKSPACE",
                           os.path.abspath(os.path.join(HERE, "..", "..", "..")))

UA    = "board_poller/1.0 (personal job-search tool; github.com/reixyz22)"
DELAY = 1.5  # be a good citizen; these are public endpoints

# ---------------------------------------------------------------- title filter
# Negative (seniority) terms BEAT positive ones, so "Senior Associate Engineer"
# is correctly dropped rather than caught by the "associate" rule.
NEVER = re.compile(
    r"\b(sales|teller|cashier|retail|barista|driver|warehouse|custodian|"
    r"nurse|clinical|physician|attorney|counsel|paralegal|recruiter)\b", re.I)
SENIOR = re.compile(
    r"\b(senior|sr|staff|principal|lead|leads|manager|mgr|director|vp|"
    r"vice\s+president|head|architect|expert|distinguished|fellow|chief|"
    r"executive|ii|iii|iv)\b", re.I)
JUNIOR = re.compile(
    r"\b(junior|jr|entry[\s-]?level|entry|new[\s-]?grad|new\s+graduate|"
    r"recent\s+graduate|graduate|grad|associate|early[\s-]?career|apprentice|"
    r"apprenticeship|trainee)\b", re.I)
# "Engineer I" / "Developer I" etc. -- a trailing roman I as a level marker.
LEVEL_I = re.compile(r"\b(engineer|developer|analyst|programmer|scientist)\s+i\b", re.I)
# Title/field is NOT the hard gate (YoE via SENIOR is). This is a broad
# adjacent-professional net; blue-collar/clinical/retail titles simply won't match.
TECH = re.compile(
    r"(engineer|engineering|developer|programmer|software|\bswe\b|\bsde\b|"
    r"full[\s-]?stack|front[\s-]?end|back[\s-]?end|web\b|platform|devops|"
    r"\bqa\b|\btest\b|sdet|machine\s+learning|\bml\b|\bai\b|\bit\b|"
    r"technolog|technical|systems|automation|data\s+(analyst|analytics|scien))", re.I)
# Tightened 2026-08-19: bare business/ops titles (specialist, coordinator, operations,
# business, compliance, finance, ...) generated noise -- "Sanitation Specialist",
# "Content Specialist", "Fraud Specialist" all classified as tech-adjacent. Keep only
# genuinely tech-leaning adjacent terms (the IT/Analyst/QA/Solutions categories a user
# actually tracks). Plain-title tech roles still classify via TECH regardless.
ADJACENT = re.compile(
    r"(analyst|analytics|\bdata\b|solutions|implementation|systems|technical|"
    r"automation|\bit\b|\bqa\b|sdet|quant|business\s+system|information\s+system)", re.I)

# ROLE: does an anchor's text look like a job title? Used by the HTML fallback
# (fetch_raw) for JazzHR/custom career pages. Was referenced but never defined --
# every raw/custom/jazzhr board threw NameError. Defined here (fix 2026-08-19).
ROLE = re.compile("(?:%s)|(?:%s)" % (TECH.pattern, ADJACENT.pattern), re.I)


def classify(title):
    """Return 'junior', 'watch', or None. Tech titles outrank adjacent ones downstream
    (see is_tech); YoE/seniority stays the only hard gate."""
    t = (title or "").strip()
    if not t:
        return None
    if SENIOR.search(t) or NEVER.search(t):
        return None
    if not (TECH.search(t) or ADJACENT.search(t)):
        return None
    if JUNIOR.search(t) or LEVEL_I.search(t):
        return "junior"
    return "watch"


def is_tech(title):
    return bool(TECH.search(title or ""))


# ---------------------------------------------------------------- location filter
# Chicago metro / Illinois or US-remote only. Deterministic string check -- NOT an
# LLM expense. Blank location = keep (unknown; let a human judge). Foreign locales
# and non-nearby US cities (Denver/NYC/SF onsite) are dropped.
LOC_LOCAL   = re.compile(r"\b(chicago|illinois|\bil\b)\b", re.I)
LOC_REMOTE  = re.compile(r"\bremote\b", re.I)
LOC_FOREIGN = re.compile(
    r"(india|bangalore|bengaluru|hyderabad|pune|gurgaon|noida|poland|krak|warsaw|"
    r"wroc|brazil|s[a\u00e3]o\s*paulo|mexico|guadalajara|canada|toronto|vancouver|"
    r"montreal|united\s+kingdom|\buk\b|england|london|scotland|ireland|dublin|"
    r"germany|berlin|munich|france|paris|spain|madrid|barcelona|portugal|lisbon|"
    r"netherlands|amsterdam|singapore|australia|sydney|philippines|manila|romania|"
    r"bucharest|ukraine|serbia|bulgaria|\bemea\b|\bapac\b|\blatam\b|europe)", re.I)


US_ABBR = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA",
    "WA","WV","WI","WY","DC"}
LOC_US = re.compile(r"\b(united\s+states|u\.?s\.?a?\.?|america|alabama|alaska|arizona|"
    r"arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|"
    r"illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|"
    r"michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new\s+hampshire|"
    r"new\s+jersey|new\s+york|north\s+carolina|south\s+carolina|north\s+dakota|"
    r"south\s+dakota|ohio|oklahoma|oregon|pennsylvania|rhode\s+island|tennessee|texas|"
    r"utah|vermont|virginia|washington|west\s+virginia|wisconsin|wyoming)\b", re.I)


def location_ok(loc):
    """Chicago/IL or US-remote. Blank = keep (unknown).

    Fixed 2026-08-19: the old code kept anything containing 'remote', so
    'Remote - Estonia' (and any Remote-<country not in the foreign denylist>)
    leaked through. Remote is now kept only when it's US-tagged or bare 'Remote'
    with no other place attached.
    """
    l = (loc or "").strip()
    if not l:
        return True
    if LOC_LOCAL.search(l):            # Chicago / IL -- always keep
        return True
    if LOC_FOREIGN.search(l):          # explicit foreign locale -- drop
        return False
    if LOC_REMOTE.search(l):
        if LOC_US.search(l):           # 'Remote - US' / 'Remote - California' etc.
            return True
        for tok in re.findall(r"\b[A-Z]{2}\b", loc):   # case-sensitive state abbrev
            if tok in US_ABBR:
                return True
        # strip 'remote' + US tokens + punctuation; if a place-word remains it's foreign
        rest = re.sub(r"\bremote\b|\b(us|usa|united\s+states)\b|[^a-z]", " ",
                      l, flags=re.I)
        return not rest.strip()        # bare 'Remote' -> keep; 'Remote Estonia' -> drop
    return False


# ---------------------------------------------------------------- YoE from JD text
# The #1 kill rule (pattern-signals.md): a stated "1+ years" floor is a kill for a
# ~0-YoE candidate, but "0-2 years" is fine. Title-only classify can't see this, so
# mid-level roles with plain titles ("Software Engineer") slip into the watch bucket.
# We read the JD (free on greenhouse/lever/ashby) and extract the *minimum* stated
# years -- taking the min across all mentions is recall-safe (if any clause says
# "0-2", the role is junior-open). Only YoE mentions sitting next to the word
# "experience" count, so "3 years of college" never triggers a false gate.
YOE = re.compile(r"(\d{1,2})\s*\+?\s*(?:to|through|-|–|—)?\s*\d{0,2}\s*"
                 r"(?:years?|yrs?)[^.\n]{0,40}?experien", re.I)


def _plain(s):
    """HTML -> rough plain text for regexing (unescape entities, drop tags)."""
    if not s:
        return ""
    return _html.unescape(re.sub(r"<[^>]+>", " ", s))


def extract_yoe(text):
    """Minimum required years of experience stated in the JD, or None if unstated."""
    floors = [int(m.group(1)) for m in YOE.finditer(text or "")]
    floors = [f for f in floors if f <= 20]          # sanity: ignore garbage matches
    return min(floors) if floors else None


# ---------------------------------------------------------------- http + fetch
def _get(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h,
                                 method="POST" if data else "GET")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as ex:
            if ex.code in (429, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def _ms(v):
    try:
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def fetch_greenhouse(e):
    # content=true returns the full JD for every job in this one call (no per-job fetch).
    d = _get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true" % e["token"])
    out = []
    for j in d.get("jobs", []):
        out.append(dict(
            id=str(j.get("id")),
            title=j.get("title", "") or "",
            location=(j.get("location") or {}).get("name", "") or "",
            url=j.get("absolute_url", "") or "",
            posted=j.get("first_published") or j.get("updated_at") or "",
            yoe=extract_yoe(_plain(j.get("content", "")))))
    return out


def fetch_lever(e):
    d = _get("https://api.lever.co/v0/postings/%s?mode=json" % e["company"])
    out = []
    for j in d or []:
        cats = j.get("categories") or {}
        # Lever's list already carries the JD (descriptionPlain) + requirement lists.
        jd = j.get("descriptionPlain") or _plain(j.get("description", ""))
        for blk in (j.get("lists") or []):
            jd += " " + _plain(blk.get("content", ""))
        out.append(dict(
            id=str(j.get("id")),
            title=j.get("text", "") or "",
            location=cats.get("location", "") or "",
            url=j.get("hostedUrl") or j.get("applyUrl", "") or "",
            posted=_ms(j.get("createdAt")),
            yoe=extract_yoe(jd)))
    return out


def fetch_ashby(e):
    d = _get("https://api.ashbyhq.com/posting-api/job-board/%s?includeCompensation=true"
             % e["org"])
    out = []
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        loc = j.get("location", "") or ""
        if j.get("workplaceType") == "Remote" or j.get("isRemote"):
            loc = (loc + " / Remote").strip(" /")
        jd = j.get("descriptionPlain") or _plain(j.get("descriptionHtml", ""))
        out.append(dict(
            id=str(j.get("id")),
            title=j.get("title", "") or "",
            location=loc,
            url=j.get("jobUrl") or j.get("applyUrl", "") or "",
            posted=j.get("publishedAt", "") or "",
            comp=((j.get("compensation") or {}).get("compensationTierSummary") or ""),
            yoe=extract_yoe(jd)))
    return out


def fetch_workday(e):
    """Verified 2026-08-05 against Wintrust. Workday caps limit at 20 and paginates;
    it also filters non-browser User-Agents, so send a browser UA. Board name is the
    URL path segment (e.g. 'Search'); tenant defaults to the subdomain."""
    host = e["host"]
    board = e.get("board", "External")
    tenant = e.get("tenant") or host.split(".")[0]
    url = "https://%s/wday/cxs/%s/%s/jobs" % (host, tenant, board)
    hdr = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
           "Accept": "application/json"}
    out, offset, cap = [], 0, 200  # cap at 10 pages so a huge board can't stall a run
    while offset < cap:
        body = json.dumps({"appliedFacets": {}, "limit": 20, "offset": offset,
                           "searchText": e.get("search_text", "")}).encode()
        d = _get(url, data=body, headers=hdr)
        page = d.get("jobPostings", [])
        if not page:
            break
        for j in page:
            path = j.get("externalPath", "")
            out.append(dict(
                id=str(path or j.get("title", "")),
                title=j.get("title", "") or "",
                location=j.get("locationsText", "") or "",
                url=("https://%s%s" % (host, path)) if path else "",
                posted=j.get("postedOn", "") or ""))
        offset += 20
        if offset >= d.get("total", 0):
            break
        time.sleep(0.5)
    return out


def fetch_smartrecruiters(e):
    """Verified 2026-08-05 (M1Finance). Company id is case-sensitive CamelCase."""
    company = e["company"]
    out, offset = [], 0
    while offset < 400:
        d = _get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d"
                 % (company, offset))
        content = d.get("content", [])
        if not content:
            break
        for j in content:
            loc = j.get("location", {}) or {}
            locs = ", ".join(x for x in (loc.get("city"), loc.get("region")) if x)
            if loc.get("remote"):
                locs = (locs + " / Remote").strip(" /")
            out.append(dict(
                id=str(j.get("id")),
                title=j.get("name", "") or "",
                location=locs,
                url="https://jobs.smartrecruiters.com/%s/%s" % (company, j.get("id")),
                posted=j.get("releasedDate", "") or ""))
        offset += 100
        if offset >= d.get("totalFound", 0):
            break
        time.sleep(0.4)
    return out


def fetch_workable(e):
    """Verified 2026-08-05 (high-voltage-software). POST; account is the apply.workable.com slug."""
    acct = e["account"]
    d = _get("https://apply.workable.com/api/v3/accounts/%s/jobs" % acct,
             data=json.dumps({}).encode(),
             headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    out = []
    for j in d.get("results", []):
        loc = j.get("location", {}) or {}
        locs = ", ".join(x for x in (loc.get("city"), loc.get("region")) if x)
        if j.get("remote") or loc.get("telecommuting"):
            locs = (locs + " / Remote").strip(" /")
        sc = j.get("shortcode", "")
        out.append(dict(
            id=str(sc or j.get("id")),
            title=j.get("title", "") or "",
            location=locs,
            url="https://apply.workable.com/%s/j/%s/" % (acct, sc),
            posted=j.get("published", "") or ""))
    return out


def fetch_raw(e):
    """HTML fallback for boards with no JSON API (JazzHR, small custom career pages).
    GET the page and extract anchor links whose text looks like a job title. Works on
    server-rendered pages; JS-only shells (Phenom/SuccessFactors) return little and
    need Selenium instead -- those stay registered as skip until an adapter exists."""
    url = e.get("source_url") or e.get("url") or ""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=25) as r:
        html = r.read().decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        href = m.group(1)
        text = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip())
        if not (4 <= len(text) <= 120) or not ROLE.search(text):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        full = href if href.startswith("http") else urljoin(url, href)
        out.append(dict(id=str(abs(hash(key + href)) % 10**12),
                        title=text, location="", url=full, posted=""))
    return out


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever,
            "ashby": fetch_ashby, "workday": fetch_workday,
            "smartrecruiters": fetch_smartrecruiters, "workable": fetch_workable,
            "jazzhr": fetch_raw, "raw": fetch_raw, "custom": fetch_raw}


# ---------------------------------------------------------------- url parsing
def parse_url(url):
    u = (url or "").strip()
    m = (re.search(r"job-boards\.greenhouse\.io/([\w.-]+)", u)
         or re.search(r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([\w.-]+)", u)
         or re.search(r"boards-api\.greenhouse\.io/v1/boards/([\w.-]+)", u))
    if m:
        return {"ats": "greenhouse", "token": m.group(1), "source_url": url}
    m = (re.search(r"jobs\.lever\.co/([\w.-]+)", u)
         or re.search(r"api\.lever\.co/v0/postings/([\w.-]+)", u))
    if m:
        return {"ats": "lever", "company": m.group(1), "source_url": url}
    m = (re.search(r"jobs\.ashbyhq\.com/([\w.-]+)", u)
         or re.search(r"ashbyhq\.com/posting-api/job-board/([\w.-]+)", u))
    if m:
        return {"ats": "ashby", "org": m.group(1), "source_url": url}
    m = re.search(r"(?:jobs|api)\.smartrecruiters\.com/(?:v1/companies/)?([\w.-]+)", u)
    if m:
        return {"ats": "smartrecruiters", "company": m.group(1), "source_url": url}
    m = (re.search(r"apply\.workable\.com/([\w.-]+)", u)
         or re.search(r"https?://([\w-]+)\.workable\.com", u))
    if m:
        return {"ats": "workable", "account": m.group(1), "source_url": url}
    m = re.search(r"https?://([\w.-]+\.myworkdayjobs\.com)/(?:[\w-]+/)?([\w-]+)", u)
    if m:
        host = m.group(1)
        return {"ats": "workday", "host": host, "tenant": host.split(".")[0],
                "board": m.group(2), "source_url": url}
    for ats, pat in (("icims", r"icims\.com"), ("taleo", r"taleo\.net"),
                     ("successfactors", r"successfactors|sapsf"),
                     ("ukg", r"ultipro\.com|ukg"),
                     ("jazzhr", r"applytojob\.com|jazz\.co")):
        if re.search(pat, u, re.I):
            return {"ats": ats, "url": url, "unsupported": True, "skip": True,
                    "source_url": url}
    return None


# ---------------------------------------------------------------- storage
def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def load_registry():
    return _load(REGISTRY, {"boards": {}})


def save_registry(r):
    with open(REGISTRY, "w") as f:
        json.dump(r, f, indent=2)


def load_seen():
    return set(_load(SEEN, []))


def save_seen(s):
    with open(SEEN, "w") as f:
        json.dump(sorted(s), f)


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _key_of(e):
    return (e.get("token") or e.get("company") or e.get("org")
            or e.get("account") or e.get("tenant"))


# ---------------------------------------------------------------- commands
def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def cmd_add(url, name, probe):
    info = parse_url(url)
    if not info:
        die("could not recognize an ATS from that URL")
    key = name or _key_of(info) or "board"
    if info.get("skip"):
        reg = load_registry()
        reg["boards"][key] = dict(info, added=_today())
        save_registry(reg)
        print("registered '%s' as a known gap (%s, no public JSON API)" % (key, info["ats"]))
        return
    if probe:
        try:
            posts = FETCHERS[info["ats"]](info)
        except Exception as ex:
            die("probe failed for '%s': %s" % (key, ex))
        if not posts:
            die("probe returned 0 postings for '%s' -- refusing to register "
                "(a silent zero is the signature of a wrong id). Use --no-probe to force."
                % key)
        print("probe ok: %d postings on '%s'" % (len(posts), key))
    reg = load_registry()
    reg["boards"][key] = dict(info, added=_today())
    save_registry(reg)
    print("registered:", key)


def cmd_verify(name):
    reg = load_registry()
    e = reg["boards"].get(name)
    if not e:
        die("no board named '%s' (see --list)" % name)
    if e.get("skip"):
        print("%s: skip (unsupported ATS %s)" % (name, e.get("ats")))
        return
    posts = FETCHERS[e["ats"]](e)
    j = sum(1 for p in posts if classify(p["title"]) == "junior")
    w = sum(1 for p in posts if classify(p["title"]) == "watch")
    status = "FAIL (0 postings)" if not posts else "ok"
    print("%s [%s]: %s -- %d total, %d junior, %d watch" % (name, e["ats"], status, len(posts), j, w))
    for p in posts[:8]:
        print("   -", p["title"], "|", p.get("location", ""))


def cmd_list():
    reg = load_registry()
    if not reg["boards"]:
        print("(registry empty -- add boards with --add)")
        return
    for name, e in sorted(reg["boards"].items()):
        tag = " [skip]" if e.get("skip") else ""
        print("%-24s %-12s %s%s" % (name, e["ats"], _key_of(e) or e.get("host", ""), tag))


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def load_exclusions(workspace):
    """Return (red_companies, killed_req_tokens).

    BUG FIXED 2026-09-01 (found in the wild: a live req that --standing should have
    surfaced and never did).
    -----------------------------------------------------------
    This used to return a flat set of COMPANY NAMES harvested from applied.md and
    ghost.md, and _excluded() substring-matched on it. Consequence: a single killed
    req blacklisted the entire employer from --standing forever. One employer had 22
    dead req IDs logged, so its bare name landed in the exclusion set and EVERY live
    posting there -- including a genuinely open AI req -- was invisible to the
    standing inventory. With 254 harvested names, that silently blinded most of the
    target list, and it blinded it QUIETLY: the run still printed a clean report.

    It also contradicted ghost.md's own documented intent, which says of one such
    kill: "this kill is about THIS req, not the company."

    Correct behaviour:
      * COMPANY-level exclusion applies ONLY to RED entries -- the permanent
        blacklist: confirmed scam operations, listing mills, and whatever
        categories the user excluded at setup. There, blocking the whole
        employer is exactly right.
      * YELLOW / GREEN kills and applied.md rows are REQ-level. Harvest the
        requisition identifiers and exclude those specific postings, leaving every
        other req at that employer visible.
    """
    red, tokens = set(), set()

    # Requisition identifier SHAPES seen in the wild, one per ATS vendor. The
    # digits below are synthetic; only the shape matters to the regex:
    #   R00000 / JR000000 (Workday)   00000000 (Taleo)   00-0000 (custom)
    #   J0000-0000 (njoyn)   R00000000 (SmartRecruiters)   000000 (Greenhouse URL)
    REQ = re.compile(r"\b((?:JR|R)\d{5,8}|\d{8}|\d{2}-\d{4}|J\d{4}-\d{4})\b")
    URL_ID = re.compile(r"(?:jobs|postings)/(\d{6,})")

    for fn, field in (("applied.md", 0), ("ghost.md", 1)):
        try:
            txt = open(os.path.join(workspace, fn), encoding="utf-8").read()
        except Exception:
            continue
        for line in txt.splitlines():
            tokens.update(REQ.findall(line))
            tokens.update(URL_ID.findall(line))
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) <= field:
                continue
            cand = re.sub(r"^\d+\.\s*", "", parts[field])      # strip '12.'
            if cand.upper() in ("RED", "YELLOW", "GREEN"):
                continue
            n = _norm(cand)
            if len(n) < 5:
                continue
            # Only a RED-tiered ghost line blacklists the employer itself.
            if fn == "ghost.md" and re.match(r"\s*\**\s*RED\b", parts[0], re.I):
                red.add(n)
    return red, tokens


def _company_blocked(company, red):
    """True only for permanently blacklisted employers (RED tier)."""
    cn = _norm(company)
    if len(cn) < 5:
        return False
    return any((x in cn or cn in x) for x in red if min(len(x), len(cn)) >= 5)


def _req_blocked(post, tokens):
    """True when THIS specific requisition is already applied-to or ghosted."""
    if not tokens:
        return False
    hay = " ".join(str(post.get(k) or "") for k in ("id", "url", "title"))
    return any(t in hay for t in tokens)


def cmd_standing(workspace):
    """Re-surface ALL currently-open junior/watch leads (ignore seen.json), minus
    anything already in applied.md / ghost.md. This is the fix for the dry-sweep
    problem: --run only reports net-new IDs, so standing live inventory stays hidden
    forever. --standing lists what's actually open and un-actioned right now."""
    reg = load_registry()
    red, kill_tokens = load_exclusions(workspace)
    junior, watch, errs = [], [], []
    excludes = [x.lower() for x in reg.get("excludes", [])]
    for name, e in reg["boards"].items():
        if e.get("skip"):
            continue
        if any(x in name.lower() for x in excludes):
            continue
        f = FETCHERS.get(e["ats"])
        if not f:
            errs.append((name, "unsupported ats: %s" % e["ats"]))
            continue
        try:
            posts = f(e)
            time.sleep(DELAY)
        except Exception as ex:
            errs.append((name, str(ex)))
            continue
        for p in posts:
            if not location_ok(p.get("location", "")):
                continue
            bucket = classify(p["title"])
            if not bucket:
                continue
            company = _key_of(e) or name
            if _company_blocked(company, red):
                continue
            if _req_blocked(p, kill_tokens):     # this REQ is applied-to/ghosted
                continue                          # (the employer stays visible)
            rec = dict(p, board=name, company=company, bucket=bucket,
                       tech=is_tech(p["title"]))
            (junior if bucket == "junior" else watch).append(rec)
    write_outputs(junior, watch, errs, False, out_md=STANDING_MD, out_json=STANDING_JSON)
    print("standing inventory: %d junior, %d watch, %d errors "
          "(%d RED companies, %d killed reqs excluded) -> %s"
          % (len(junior), len(watch), len(errs), len(red), len(kill_tokens), STANDING_MD))


def cmd_run(all_=False):
    reg = load_registry()
    known = set() if all_ else load_seen()
    seen = set(load_seen())
    junior, watch, errs = [], [], []
    baseline = not os.path.exists(SEEN)
    excludes = [x.lower() for x in reg.get("excludes", [])]
    for name, e in reg["boards"].items():
        if e.get("skip"):
            continue
        if any(x in name.lower() for x in excludes):
            continue
        f = FETCHERS.get(e["ats"])
        if not f:
            errs.append((name, "unsupported ats: %s" % e["ats"]))
            continue
        try:
            posts = f(e)
            time.sleep(DELAY)
        except Exception as ex:
            errs.append((name, str(ex)))
            continue
        for p in posts:
            key = "%s:%s" % (name, p["id"])
            seen.add(key)
            if not all_ and key in known:
                continue
            if not location_ok(p.get("location", "")):
                continue
            bucket = classify(p["title"])
            if not bucket:
                continue
            rec = dict(p, board=name, company=_key_of(e) or name, bucket=bucket,
                       tech=is_tech(p["title"]))
            (junior if bucket == "junior" else watch).append(rec)
    write_outputs(junior, watch, errs, baseline)   # write the deliverable FIRST
    try:
        save_seen(seen)
    except Exception as ex:
        print("warning: could not save seen-store (%s); outputs written anyway" % ex,
              file=sys.stderr)
    print("run complete: %d junior, %d watch, %d errors -> %s"
          % (len(junior), len(watch), len(errs), OUT_MD))


def write_outputs(junior, watch, errs, baseline, out_md=OUT_MD, out_json=OUT_JSON):
    gen = datetime.now(timezone.utc).isoformat()
    data = {"generated": gen, "baseline_run": baseline,
            "counts": {"junior": len(junior), "watch": len(watch)},
            "junior": junior, "watch": watch,
            "errors": [{"board": b, "error": e} for b, e in errs]}
    with open(out_json, "w") as f:
        json.dump(data, f, indent=2)
    L = ["# New postings -- %s" % gen[:19], ""]
    if baseline:
        L.append("_First run for these boards: showing everything currently open. "
                 "Future runs report only what is new._\n")

    def _age_days(p):
        raw = (p.get("posted") or "").strip()
        m = re.search(r"posted\s+(today)|posted\s+(yesterday)|posted\s+(\d+)\+?\s+day", raw, re.I)
        if m:
            if m.group(1):
                return 0
            if m.group(2):
                return 1
            return int(m.group(3))
        if re.search(r"30\+", raw):
            return 31
        try:
            dt = datetime.fromisoformat(raw[:10])
            return (datetime.now() - dt).days
        except Exception:
            return None

    def _gated(p):
        y = p.get("yoe")
        return y is not None and y >= 2      # >=2 stated years = YoE-gated for a 0-YoE hunt

    def sec(title, items):
        L.append("## %s (%d)" % (title, len(items)))
        if not items:
            L.append("_none_")
        # clean (0-1 YoE) first, then tech over adjacent, then newest first.
        # YoE-gated roles (>=2 stated years) sink to the bottom but are NOT dropped.
        def key(p):
            a = _age_days(p)
            return (1 if _gated(p) else 0, 0 if p.get("tech") else 1,
                    a if a is not None else 9999)
        for p in sorted(items, key=key):
            extra = " -- %s" % p.get("comp") if p.get("comp") else ""
            a = _age_days(p)
            if a is None:
                age = "age unknown"
            elif a > 30:
                age = "STALE %dd" % a
            else:
                age = "%dd old" % a
            tag = "" if p.get("tech") else " [adjacent]"
            y = p.get("yoe")
            yoe_tag = (" `[needs %dyr]`" % y) if (y is not None and y >= 1) else ""
            L.append("- **%s** - %s%s%s - %s%s" % (p["company"], p["title"], tag,
                                                   yoe_tag, p.get("location", ""), extra))
            L.append("  %s  (%s, posted %s)" % (p.get("url", ""), age,
                                                (p.get("posted", "") or "")[:10]))
        L.append("")
    sec("Junior / entry", junior)
    sec("Watch (unmarked level)", watch)
    if errs:
        L.append("## Errors")
        for b, e in errs:
            L.append("- %s: %s" % (b, e))
    with open(out_md, "w") as f:
        f.write("\n".join(L))


def _slugs(name):
    """Candidate ATS slugs from a company name (a few common shapes)."""
    n = re.sub(r"\.com$", "", name.lower().strip())
    words = re.sub(r"[^a-z0-9 ]+", " ", n).split()
    base = "".join(words)
    cands = [base, "-".join(words)]
    if words:
        cands.append(words[0])          # first word (e.g. "fetch")
    cands += [base + "inc"]
    out, seen = [], set()
    for c in cands:
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out


def resolve_name(name):
    """Probe greenhouse/lever/ashby for a company name; return the first live hit."""
    probes = (("greenhouse", fetch_greenhouse, "token"),
              ("lever", fetch_lever, "company"),
              ("ashby", fetch_ashby, "org"),
              ("smartrecruiters", fetch_smartrecruiters, "company"),
              ("workable", fetch_workable, "account"))
    for slug in _slugs(name):
        for ats, fetch, keyf in probes:
            try:
                posts = fetch({"ats": ats, keyf: slug})
            except Exception:
                posts = None
            time.sleep(0.15)
            if posts:
                return {"ats": ats, keyf: slug, "n": len(posts)}
    return None


def cmd_resolve_file(path):
    reg = load_registry()
    hits, misses = 0, []
    for line in open(path):
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        r = resolve_name(name)
        if r:
            slug = r.get("token") or r.get("company") or r.get("org")
            entry = {"ats": r["ats"], "source_url": "resolver:" + name, "added": _today()}
            for kf in ("token", "company", "org"):
                if kf in r:
                    entry[kf] = r[kf]
            reg["boards"][slug] = entry
            print("HIT   %-26s -> %s/%s  (%d open)" % (name, r["ats"], slug, r["n"]))
            hits += 1
        else:
            misses.append(name)
            print("miss  %s" % name)
    save_registry(reg)
    print("\nresolved %d, missed %d" % (hits, len(misses)))
    if misses:
        print("manual --add needed (Workday/SmartRecruiters/custom):", ", ".join(misses))


def main():
    ap = argparse.ArgumentParser(description="Poll ATS boards; report only what is new.")
    ap.add_argument("--add", metavar="URL", help="register a board from its careers URL")
    ap.add_argument("--name", help="custom registry key for --add")
    ap.add_argument("--no-probe", action="store_true", help="register without probing (not advised)")
    ap.add_argument("--verify", metavar="NAME", help="re-check a registered board")
    ap.add_argument("--list", action="store_true", help="list registered boards")
    ap.add_argument("--run", action="store_true", help="poll all boards, report the diff")
    ap.add_argument("--all", action="store_true", help="with --run: ignore seen-store, report everything")
    ap.add_argument("--standing", action="store_true",
                    help="re-surface ALL open junior/watch leads (ignore seen.json), minus applied.md/ghost.md -> standing-postings.md")
    ap.add_argument("--workspace", metavar="DIR",
                    help="workspace dir holding applied.md/ghost.md (default: three levels up)")
    ap.add_argument("--resolve-file", metavar="PATH", help="probe a list of company names (one per line) across greenhouse/lever/ashby and auto-register hits")
    a = ap.parse_args()
    if a.add:
        cmd_add(a.add, a.name, not a.no_probe)
    elif a.verify:
        cmd_verify(a.verify)
    elif a.list:
        cmd_list()
    elif a.standing:
        cmd_standing(a.workspace or WORKSPACE)
    elif a.run:
        cmd_run(a.all)
    elif a.resolve_file:
        cmd_resolve_file(a.resolve_file)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
