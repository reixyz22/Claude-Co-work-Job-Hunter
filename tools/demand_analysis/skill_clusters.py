#!/usr/bin/env python3
"""skill_clusters -- what the sweep logs say the market asks for TOGETHER.

A frequency tally answers "which skills come up most." That is the wrong question
for deciding what to build, because the top-N skills across all postings rarely
appear in the SAME posting, and a portfolio project has to satisfy one posting at
a time. This reads the sweep logs a workspace has already accumulated, rebuilds
one skill set per distinct posting, and reports which sets actually co-occur.

Method: keyword extraction against a controlled vocabulary, one set per posting,
deduplicated by posting identity so a lead carried over for six nights counts
once -- then Apriori frequent-itemset mining over those sets.

Stdlib only. No network.

    python3 skill_clusters.py --workspace ~/path/to/workspace
    python3 skill_clusters.py --workspace . --min-support 0.06 --out report.md

Known limits, stated because they change how you read the output:
  * The corpus is sweep PROSE about postings, not raw JD text. A skill named in
    commentary rather than in the posting inflates its count. Lines naming the
    user are dropped for this reason (--user), but the effect is not zero.
  * The corpus only contains postings this pipeline surfaced. It is evidence
    about the reachable market, not about the market. See the mirror check.
"""
import argparse, glob, os, re, sys
from collections import Counter, defaultdict
from itertools import combinations

# ------------------------------------------------------------------ vocabulary
# Canonical name -> pattern. Patterns are matched case-sensitively where the
# token is an acronym or a proper noun, which is most of them.
VOCAB = {
    "Python":            r"\bPython\b",
    "Java":              r"\bJava\b(?!Script)",
    "JavaScript":        r"\bJavaScript\b",
    "TypeScript":        r"\bTypeScript\b",
    "C#":                r"C#|\bC-sharp\b",
    ".NET / ASP.NET":    r"\.NET\b|\bASP\.NET\b|\bdotnet\b|\bEF Core\b",
    "C++":               r"C\+\+",
    "Go":                r"\bGolang\b|\bGo\b(?=[,)/]|\s+(?:service|services|backend|API|HTTP|goroutine))",
    "PHP":               r"\bPHP\b|\bSymfony\b|\bLaravel\b",
    "Ruby / Rails":      r"\bRuby\b|\bRails\b",
    "Kotlin":            r"\bKotlin\b",
    "Swift / iOS":       r"\bSwift\b|\biOS\b",
    "Lua / Luau":        r"\bLua\b|\bLuau\b",
    "SQL":               r"\bSQL\b(?!\s*Server)|\brelational database",
    "SQL Server":        r"\bSQL Server\b|\bT-SQL\b|\bMSSQL\b",
    "PostgreSQL":        r"\bPostgres(?:QL)?\b",
    "MySQL":             r"\bMySQL\b",
    "MongoDB":           r"\bMongo(?:DB)?\b",
    "Azure":             r"\bAzure\b",
    "AWS":               r"\bAWS\b|\bAmazon Web Services\b|\bEC2\b|\bECS\b|\bS3\b",
    "GCP":               r"\bGCP\b|\bGoogle Cloud\b|\bFirebase\b",
    "Docker":            r"\bDocker\b|\bcontainer(?:iz|is)",
    "Kubernetes":        r"\bKubernetes\b|\bK8s\b|\bEKS\b",
    "Terraform / IaC":   r"\bTerraform\b|\bInfrastructure as Code\b|\bIaC\b",
    "CI/CD":             r"\bCI/CD\b|\bcontinuous integration\b|\bJenkins\b|\bGitHub Actions\b|\bGitLab CI\b|\bAzure DevOps\b",
    "Testing":           r"\bunit test|\bintegration test|\bpytest\b|\bJUnit\b|\bSelenium\b|\bPlaywright\b|\bCypress\b|\btest automation\b|\bSDET\b|\bQA\b",
    "React":             r"\bReact\b(?!ive)",
    "Angular":           r"\bAngular\b",
    "Vue":               r"\bVue\b",
    "Next.js":           r"\bNext\.js\b",
    "Node.js":           r"\bNode\.js\b",
    "REST APIs":         r"\bREST\b|\bRESTful\b",
    "GraphQL":           r"\bGraphQL\b",
    "Python web":        r"\bFlask\b|\bDjango\b|\bFastAPI\b",
    "Spring":            r"\bSpring Boot\b|\bSpring Framework\b",
    "Kafka / queues":    r"\bKafka\b|\bRabbitMQ\b|\bCelery\b|\bmessage queue",
    "Git / GitHub":      r"\bGit\b|\bGitHub\b|\bGitLab\b",
    "Agile / Scrum":     r"\bAgile\b|\bScrum\b",
    "Linux":             r"\bLinux\b|\bUnix\b",
    "PowerShell":        r"\bPowerShell\b",
    "LLM / GenAI":       r"\bLLM\b|\bGenAI\b|\bgenerative AI\b|\blarge language model",
    "AI agents / MCP":   r"\bagentic\b|\bAI agent|\btool-calling\b|\bMCP\b",
    "Prompt engineering": r"\bprompt engineering\b",
    "AI coding tools":   r"\bClaude Code\b|\bCursor\b|\bCopilot\b",
    "RAG":               r"\bRAG\b|\bretrieval[- ]augmented",
    "ML / data science": r"\bmachine learning\b|\bTensorFlow\b|\bPyTorch\b|\bscikit|\bpandas\b|\bNumPy\b",
    "BI / analytics":    r"\bPower BI\b|\bTableau\b|\bLooker\b",
    "Unreal":            r"\bUnreal\b|\bUE5\b",
    "Unity":             r"\bUnity\b",
    "Healthcare IT":     r"\bHL7\b|\bFHIR\b|\bEHR\b|\bEpic systems\b|\bEpic\b(?!\s(?:Games|Kids))",
    "Salesforce":        r"\bSalesforce\b",
    "ServiceNow":        r"\bServiceNow\b",
}
COMPILED = {k: re.compile(v) for k, v in VOCAB.items()}

CORPUS_GLOBS = ("nightly-leads-*.md", "morning-brief*.md", "brief-*.md",
                "email-check-*.md", "sweep-*.md", "daily-sweep-*.md",
                "afternoon-sweep-*.md")

HEADING = re.compile(r"^(#{2,4})\s+(.*)$")

# A block counts as ONE posting only if its heading names one employer. Roundup
# sections ("two leads worth chasing", "everything else that died tonight") name
# six employers in a single block; counting one of those as a posting invents
# co-occurrence no JD ever asked for. Dropping them changed the top 3-skill
# cluster on this corpus, which is the whole reason the filter is here.
NOISE_HEADING = re.compile(
    r"^(kills?\b|everything else|source ledger|learning\b|curriculum|housekeeping|"
    r"channel notes|counts\b|what\b|why\b|how\b|note\b|summary|top\b|standing rules|"
    r"application pipeline|killed today|unresolved|pipeline\b|leads?\b.*\b(worth|chasing)|"
    r"new tonight|carryover\b|the useful part|search pollution)", re.I)
# Leading decoration before the employer name: "STANDING #1 — ", "Lead 3 | ", "1. ".
NOISE_LEAD = re.compile(
    r"^(?:standing\s*#?\d*|the\s+lead|lead\s*#?\d*|top\s+lead|new\s+lead|"
    r"confirmed\s+kill[^—–|:]*|#?\d+[.)]?)\s*[—–|:.\-]+\s*", re.I)
# A real posting write-up cites something checkable.
POSTING_SIGNAL = re.compile(
    r"https?://|\$\s?\d|\breq\b|\brequisition\b|\bposted\b|\bapply\b|\bJD\b", re.I)
NOT_A_COMPANY = {"lead", "leads", "new", "kills", "killed", "everything", "unresolved",
                 "carryover", "pipeline", "the", "other", "others", "rest", "noise",
                 "misc", "standing", "top", "confirmed", "also", "one", "two", "three"}


def posting_key(heading):
    """Identity of a posting, so a lead carried six nights counts once.

    Returns None when the heading does not name a single employer.
    """
    h = heading.strip()
    for _ in range(3):
        h2 = NOISE_LEAD.sub("", h)
        if h2 == h:
            break
        h = h2
    if not re.search(r"[|—–,]", h):          # no employer/role separator
        return None
    company = re.split(r"[|—–,]", h)[0]
    company = re.sub(r"\*\*|\(.*?\)", " ", company)
    company = re.sub(r"[^A-Za-z0-9 &.]", " ", company).strip().lower()
    words = [w for w in company.split() if w not in NOT_A_COMPANY]
    if not words or len("".join(words)) < 3:
        return None
    return " ".join(words[:4])


def blocks(path, user):
    """Yield (heading, body) for each heading-delimited block in a log file."""
    cur, buf = None, []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = HEADING.match(line)
        if m:
            if cur:
                yield cur, "\n".join(buf)
            cur, buf = m.group(2).strip(), []
        elif cur:
            if user and user.lower() in line.lower():
                continue                          # commentary about the user, not the JD
            buf.append(line)
    if cur:
        yield cur, "\n".join(buf)


def skills_in(text):
    return {name for name, rx in COMPILED.items() if rx.search(text)}


def apriori(sets, min_count, max_len=5):
    """Frequent itemsets by support. Small vocab, small corpus -- brute force is fine."""
    items = Counter()
    for s in sets:
        items.update(s)
    level = {frozenset([i]): c for i, c in items.items() if c >= min_count}
    out = dict(level)
    k = 2
    while level and k <= max_len:
        cands = set()
        keys = list(level)
        for a, b in combinations(keys, 2):
            u = a | b
            if len(u) == k:
                cands.add(u)
        nxt = {}
        for c in cands:
            n = sum(1 for s in sets if c <= s)
            if n >= min_count:
                nxt[c] = n
        out.update(nxt)
        level = nxt
        k += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".", help="folder holding the sweep logs")
    ap.add_argument("--min-support", type=float, default=0.05,
                    help="minimum share of postings an itemset must appear in")
    ap.add_argument("--user", default="", help="name to strip from commentary lines")
    ap.add_argument("--have", default="",
                    help="comma-separated skills already credible (for the gap view)")
    ap.add_argument("--out", default="", help="write the report here instead of stdout")
    a = ap.parse_args()

    ws = os.path.expanduser(a.workspace)
    files = sorted(f for g in CORPUS_GLOBS for f in glob.glob(os.path.join(ws, g)))
    if not files:
        sys.exit("no sweep logs found in %s" % ws)

    postings, sources, first_seen = defaultdict(set), defaultdict(set), {}
    for path in files:
        day = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
        day = day.group(1) if day else "?"
        for heading, body in blocks(path, a.user):
            if NOISE_HEADING.match(heading):
                continue
            key = posting_key(heading)
            if not key:
                continue
            if not POSTING_SIGNAL.search(body):    # nothing checkable in the block
                continue
            found = skills_in(heading + "\n" + body)
            if len(found) < 2:                     # not a posting write-up
                continue
            postings[key] |= found
            sources[key].add(os.path.basename(path))
            first_seen.setdefault(key, day)

    sets = list(postings.values())
    n = len(sets)
    have = {s.strip() for s in a.have.split(",") if s.strip()}
    min_count = max(3, int(round(a.min_support * n)))

    L = []
    w = L.append
    w("# Skill co-occurrence across the sweep logs\n")
    w("Corpus: %d log files, %s to %s. **%d distinct postings** after "
      "deduplicating carried-over leads.\n" % (
          len(files), min(first_seen.values()), max(first_seen.values()), n))
    w("Support threshold: an itemset must appear in at least %d postings (%.0f%%).\n"
      % (min_count, 100.0 * min_count / n))

    w("\n## 1. Frequency — the ranked list, for reference\n")
    freq = Counter()
    for s in sets:
        freq.update(s)
    w("| Skill | Postings | Share |")
    w("|---|---:|---:|")
    for skill, c in freq.most_common(25):
        w("| %s | %d | %.0f%% |" % (skill, c, 100.0 * c / n))

    itemsets = apriori(sets, min_count)
    w("\n## 2. Co-occurrence — what actually appears together\n")
    for size in (2, 3, 4, 5):
        rows = sorted(((v, k) for k, v in itemsets.items() if len(k) == size),
                      reverse=True)[:12]
        if not rows:
            continue
        w("\n### %d-skill combinations\n" % size)
        w("| Combination | Postings | Share | Lift |")
        w("|---|---:|---:|---:|")
        for cnt, iset in rows:
            expected = 1.0
            for i in iset:
                expected *= freq[i] / n
            lift = (cnt / n) / expected if expected else 0
            w("| %s | %d | %.0f%% | %.1fx |" % (
                " + ".join(sorted(iset)), cnt, 100.0 * cnt / n, lift))

    if have:
        w("\n## 3. Gap view — the same clusters, minus what is already credible\n")
        w("Treating as already credible: %s.\n" % ", ".join(sorted(have)))
        gap_sets = [s - have for s in sets]
        gaps = apriori([g for g in gap_sets if g], min_count)
        for size in (1, 2, 3):
            rows = sorted(((v, k) for k, v in gaps.items() if len(k) == size),
                          reverse=True)[:10]
            if not rows:
                continue
            w("\n**%d-skill gaps**\n" % size)
            w("| Missing combination | Postings | Share |")
            w("|---|---:|---:|")
            for cnt, iset in rows:
                w("| %s | %d | %.0f%% |" % (" + ".join(sorted(iset)), cnt,
                                            100.0 * cnt / n))

        w("\n## 4. Mirror check\n")
        covered = sum(1 for s in sets if s and s <= have)
        w("- Postings whose entire detected stack is already credible: "
          "**%d of %d (%.0f%%)**." % (covered, n, 100.0 * covered / n))
        w("- Postings needing at least one skill that is not: **%d (%.0f%%)**."
          % (n - covered, 100.0 * (n - covered) / n))
        w("\nA corpus that mostly reflects the searcher back at themselves skews to "
          "the first number. A corpus describing a market skews to the second.")

    w("\n## 5. Coverage — what one project could answer\n")
    best = sorted(((v, k) for k, v in itemsets.items() if 3 <= len(k) <= 5),
                  reverse=True)[:5]
    for cnt, iset in best:
        w("\n**%s** — %d postings (%.0f%%)" % (" + ".join(sorted(iset)), cnt,
                                               100.0 * cnt / n))
        ex = [k for k, s in postings.items() if iset <= s][:6]
        w("  examples: %s" % ", ".join(ex))

    text = "\n".join(L) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print("wrote %s (%d postings, %d log files)" % (a.out, n, len(files)))
    else:
        print(text)


if __name__ == "__main__":
    main()
