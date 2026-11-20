"""
Instant materials builds from the dashboard. If the user is in the headspace to
click "Build materials", they likely mean to apply right then, not after the next
scheduled sweep.

When the Claude Code CLI (`claude`) is on PATH, a Build-materials click starts an
unattended `claude -p` run in the workspace. Claude Code auto-loads the
workspace's CLAUDE.md, so the build follows the same rules as the scheduled
sweeps. Status lives in state/builds/<key>.json; the full transcript in
state/builds/<key>.log. If the CLI is missing or the run fails, nothing is lost:
the request is still in the event log and the next sweep builds it.

Never applies, never submits, never edits applied.md or ghost.md.
"""
import json, os, re, shutil, subprocess, threading, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDS = os.path.join(HERE, "state", "builds")
_LOCK = threading.Lock()
_RUNNING = {}
MAX_PARALLEL = 2

TOOLS = ",".join([
    "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
    "Bash(pdflatex:*)", "Bash(xelatex:*)", "Bash(python:*)", "Bash(python3:*)", "Bash(py:*)",
    "Bash(curl:*)", "Bash(mkdir:*)", "Bash(ls:*)", "Bash(cp:*)", "Bash(cd:*)",
])

PROMPT = """You are running UNATTENDED, started by the user's job-hunt dashboard because
they clicked "Build materials" on a lead and intend to apply right away. Nobody can
answer questions; make reasonable choices and state them in apply-notes.md.

LEAD: {title}
LINK: {url}
USER'S NOTE: {note}
TODAY: {today}

The workspace CLAUDE.md is loaded; its rules are binding (no fabricated experience,
never name a weakness in anything the employer reads, reuse only the user's
approved resume sources and canonical blocks, one page). Also follow the
materials steps in the plugin's skills/nightly/SKILL.md.

Do this:
1. Kill check: if the company/role is in applied.md (already applied) or is RED or
   recent YELLOW in ghost.md, print "SKIPPED: <one-line reason>" and stop.
2. Open the posting on the employer's own site / ATS API. Save the full JD body
   verbatim to applications/<slug>-{today}/jd.md with a header (capture date,
   URL, comp, location, employer posting date). If the employer page cannot be
   reached, use the link above and say so in the header.
3. Build applications/<slug>-{today}/<Name>_<Role>_Resume.tex from the user's
   master resume and canonical blocks named in CLAUDE.md, tailored to this JD.
   Compile it (pdflatex, or typst for a .typ template) in that folder. It must be
   exactly 1 page: check the page count, then Read the PDF and look at it for
   header clipping and lines holding one or two dangling words. Fix and
   recompile until clean.
4. Write apply-notes.md: apply link, provenance, requirements quoted verbatim vs
   the user's evidence, gaps (internal only), and a draft for any required
   free-text question on the application form. No cover letter unless the form
   requires one, and then only an outline.
5. Write brief-{today}-{hour}-build.md in the workspace root containing exactly:
   a heading, then "## Links and materials status" followed IMMEDIATELY by the
   table header "| # | Lead | Comp | Location | Apply link | Age | Verified | Materials |",
   one row for this lead with Materials = "READY - `applications/<slug>-{today}/`",
   then a short paragraph about the lead.
6. Run the dashboard rebuild: python "{build_site}"
7. Finish by printing one line: BUILT applications/<slug>-{today}/  (or SKIPPED: reason)

Only write inside applications/, jds/ and that one brief file. Never submit or
apply to anything. Never edit applied.md, ghost.md or CLAUDE.md.
"""


def cli_path(cfg):
    return shutil.which((cfg or {}).get("claude_cli") or "claude")


def _safe(key):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", key)[:120]


def _write_status(key, **kw):
    os.makedirs(BUILDS, exist_ok=True)
    p = os.path.join(BUILDS, _safe(key) + ".json")
    cur = status(key) or {}
    cur.update(kw)
    cur["key"] = key
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return cur


def status(key):
    p = os.path.join(BUILDS, _safe(key) + ".json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def all_status():
    out = {}
    if os.path.isdir(BUILDS):
        for f in os.listdir(BUILDS):
            if f.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(BUILDS, f), encoding="utf-8"))
                    out[d.get("key", f[:-5])] = d
                except Exception:
                    pass
    return out


def start(key, req, root, cfg):
    """Returns the status dict. 'queued-for-sweep' when the CLI isn't available."""
    exe = cli_path(cfg)
    if not exe:
        return _write_status(key, state="queued-for-sweep",
                             reason="Claude Code (claude) is not installed on this PC")
    with _LOCK:
        live = [k for k, t in _RUNNING.items() if t.is_alive()]
        if key in live:
            return status(key)
        if len(live) >= MAX_PARALLEL:
            return _write_status(key, state="queued-for-sweep",
                                 reason=f"{MAX_PARALLEL} builds already running")
        st = _write_status(key, state="building", title=req.get("title", ""),
                           started=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           result="")
        t = threading.Thread(target=_run, args=(key, req, root, cfg, exe), daemon=True)
        _RUNNING[key] = t
        t.start()
        return st


def _run(key, req, root, cfg, exe):
    now = datetime.now()
    prompt = PROMPT.format(title=req.get("title") or req.get("employer") or "(unnamed lead)",
                           url=req.get("url") or "(none given)",
                           note=req.get("note") or "(none)",
                           today=now.strftime("%Y-%m-%d"),
                           hour=now.strftime("%I%p").lstrip("0").lower(),
                           build_site=os.path.join(HERE, "build_site.py"))
    log = os.path.join(BUILDS, _safe(key) + ".log")
    cmd = [exe, "-p", "--permission-mode", "acceptEdits", "--allowedTools", TOOLS]
    if cfg.get("build_cli_model"):
        cmd += ["--model", cfg["build_cli_model"]]
    flags = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW
    try:
        with open(log, "w", encoding="utf-8", errors="replace") as lf:
            r = subprocess.run(cmd, input=prompt, stdout=lf, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", cwd=root,
                               timeout=int(cfg.get("build_timeout", 1800)), creationflags=flags)
        tail = open(log, encoding="utf-8", errors="replace").read()[-4000:]
        m = re.search(r"^(BUILT .*|SKIPPED.*)$", tail, re.M)
        ok = bool(r.returncode == 0 and m and m.group(1).startswith("BUILT"))
        last = (tail.strip().splitlines() or [""])[-1]
        _write_status(key, state="done" if ok else ("skipped" if m else "failed"),
                      result=(m.group(1) if m else last)[:300],
                      finished=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    except subprocess.TimeoutExpired:
        _write_status(key, state="failed", result="timed out",
                      finished=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    except Exception as e:
        _write_status(key, state="failed", result=str(e)[:300],
                      finished=datetime.now(timezone.utc).isoformat(timespec="seconds"))
