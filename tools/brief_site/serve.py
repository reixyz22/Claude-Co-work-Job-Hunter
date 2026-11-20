#!/usr/bin/env python3
"""
Local dashboard for the daily job hunter.  Python stdlib only -- no pip install,
no node, no build step.  Start it and leave the tab open:

    python3 serve.py            # -> http://127.0.0.1:8787
    python3 serve.py --port 9000 --root /path/to/workspace

Binds to 127.0.0.1 only. Nothing is exposed off the machine.
"""
import argparse, json, os, posixpath, re, subprocess, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eventlog import EventLog  # noqa: E402
import points as points_mod  # noqa: E402
import ai as ai_mod  # noqa: E402
import builder  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402


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



STATIC = os.path.join(HERE, "static")
DATA = os.path.join(HERE, "data")
STATE = os.path.join(HERE, "state")
LOG = EventLog(STATE)
ROOT = None


def rebuild():
    """Re-parse the workspace. Safe to call any time; never writes to markdown."""
    env = dict(os.environ, JOBHUNT_ROOT=ROOT)
    outs = []
    for script in ("build_site.py", "build_events.py"):
        try:
            r = subprocess.run([sys.executable, os.path.join(HERE, script)],
                               env=env, capture_output=True, text=True, timeout=120)
            outs.append((r.stdout or r.stderr or "").strip())
        except Exception as e:
            outs.append(f"{script} failed: {e}")
    return "\n".join(o for o in outs if o)


# ---------------------------------------------------------------- calendar + history
def _local_day(ts):
    """Event-log timestamps are UTC; the day they belong to is the user's local day."""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().date().isoformat()
    except Exception:
        return str(ts)[:10]


def _load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def pins():
    """Projection of pin/unpin events. Like checks.json: derived, never truth."""
    live = {}
    for e in LOG.all_events():
        p = e.get("payload") or {}
        if e["kind"] == "pin":
            live[p.get("key")] = dict(p, id=p.get("key"), created=e["ts"])
        elif e["kind"] == "unpin":
            live.pop(p.get("key"), None)
    return sorted(live.values(), key=lambda x: (x.get("date", ""), x.get("time") or "99"))


def history():
    days = {d: list(v) for d, v in _load("history_static.json", {"days": {}}).get("days", {}).items()}
    seen = set()
    for e in LOG.all_events():
        p = e.get("payload") or {}
        k = e["kind"]
        if "smoke" in str(p.get("key", "")).lower() or "SMOKE TEST" in str(p.get("label", "")):
            continue  # setup self-tests are not things the user did
        if k == "check" and p.get("checked") and p.get("key") not in seen:
            seen.add(p.get("key"))
            kind = p.get("kind") or "task"
            label = p.get("label") or p.get("key")
            if kind == "applied":
                label = "Applied: " + label
            days.setdefault(_local_day(e["ts"]), []).append(
                {"kind": kind, "label": label, "source": "dashboard", "id": e["id"]})
        elif k == "win":
            days.setdefault(p.get("date") or _local_day(e["ts"]), []).append(
                {"kind": "win", "label": p.get("text", ""), "source": "you", "id": e["id"]})
        elif k == "note":
            days.setdefault(_local_day(e["ts"]), []).append(
                {"kind": "note", "label": "Note: " + (p.get("text", "")[:120]), "source": "dashboard"})
    # an application logged both by the tick and by applied.md is one thing
    for d, items in days.items():
        out, labels = [], set()
        for it in items:
            sig = re.sub(r"[^a-z0-9]", "", it["label"].lower())[:40]
            if sig in labels:
                continue
            labels.add(sig)
            out.append(it)
        days[d] = out
    return {"days": days}


def ai_context():
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=35)).isoformat()
    lines = []
    ev = _load("events.json", {}).get("events", [])
    up = [e for e in ev if today <= e["date"] <= soon and not e.get("killed")]
    if up:
        lines.append("UPCOMING IRL EVENTS (from events.md, ranked by the event finder):")
        for e in up[:25]:
            lines.append(f"- [{e['id']}] {e['date']} STARTS {e.get('start') or '?'}"
                         f"{' LEAVE BY ' + e['leave_by'] if e.get('leave_by') else ''} | {e['title']} | "
                         f"{e.get('venue','')[:80]} | {e.get('cost','')} | {e.get('tier','')} | "
                         f"{(e.get('catch') or '')[:160]} {e.get('url','')}")
    pp = [p for p in pins() if p.get("date", "") >= today]
    if pp:
        lines.append("PINNED ON THEIR CALENDAR:")
        lines += [f"- {p['date']} {p.get('time','')} {p.get('title','')}" for p in pp[:20]]
    h = history()["days"]
    recent = sorted(h)[-10:]
    if recent:
        lines.append("RECENT ACCOMPLISHMENTS:")
        for d in recent:
            for it in h[d][:8]:
                if it["kind"] != "sweep":
                    lines.append(f"- {d}: {it['label'][:140]}")
    leads = _load("leads.json", [])
    open_leads = [L for L in leads if not L.get("expired")][:12]
    if open_leads:
        lines.append("TOP OPEN JOB LEADS:")
        lines += [f"- {L.get('title','')[:100]} ({L.get('age') or '?'}) {L.get('url','')}" for L in open_leads]
    notes = _load("notes.json", {}).get("pinned", [])
    if notes:
        lines.append("PINNED NOTES FROM THE SWEEPS:")
        lines += [f"- {n.get('date','')}: {re.sub(r'[*`]', '', n.get('text',''))[:220]}" for n in notes[:8]]
    st = _load("stats.json", {})
    lines.append(f"STATS: {st.get('applied_count', '?')} applications logged; latest sweep {st.get('latest_brief', '?')}.")
    return "\n".join(lines)[:14000]


def cfg():
    # config.json is yours and gitignored; config.example.json is the shipped default.
    for name in ("config.json", "config.example.json"):
        try:
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    def log_message(self, fmt, *args):
        pass  # quiet

    # ---------- helpers ----------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        if not os.path.exists(path):
            return self._json({"error": "not found", "path": os.path.basename(path)}, 404)
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET ----------
    def do_GET(self):
        p = urlparse(self.path).path
        if p.startswith("/api/"):
            name = p[len("/api/"):].strip("/")
            if name in ("leads", "briefs", "briefs_raw", "stats", "study",
                        "notes", "platforms", "tasks", "events"):
                return self._file(os.path.join(DATA, f"{name}.json"))
            if name == "points":
                fb = set()
                tp = os.path.join(DATA, "tasks.json")
                if os.path.exists(tp):
                    try:
                        fb = {t["key"] for t in json.load(open(tp, encoding="utf-8")).get("freebies", [])}
                    except Exception:
                        fb = set()
                return self._json(points_mod.summary(LOG.all_events(), fb))
            if name == "leadkills":
                return self._json({"leadkills": LOG.leadkills(),
                                   "presets": (cfg().get("kill_reasons") or {})})
            if name == "buildreqs":
                return self._json({"buildreqs": LOG.buildreqs(), "status": builder.all_status(),
                                   "instant": bool(builder.cli_path(cfg()))})
            if name == "checks":
                return self._json({"checks": LOG.checks()})
            if name == "pins":
                return self._json({"pins": pins()})
            if name == "history":
                return self._json(history())
            if name == "engine":
                return self._json({"engine": ai_mod.engine_name(cfg())})
            if name == "queue":
                pend = LOG.pending()
                return self._json({"pending": len(pend), "events": pend[-50:]})
            if name == "rebuild":
                return self._json({"ok": True, "out": rebuild()})
            return self._json({"error": "unknown endpoint"}, 404)
        if p == "/":
            p = "/index.html"
        self.path = p
        return super().do_GET()

    # ---------- POST ----------
    def do_POST(self):
        p = urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)

        if p == "/api/check":
            key = (body.get("key") or "").strip()
            if not key:
                return self._json({"error": "key required"}, 400)
            ev = LOG.append("check", {
                "key": key,
                "checked": bool(body.get("checked")),
                "label": body.get("label") or "",
                "kind": body.get("kind") or "task",
                "url": body.get("url") or "",
                "note": body.get("note") or "",
            })
            # The browser gets confirmation only after the line is on disk and
            # fsync'd, so a tick the user saw land is a tick that survives a
            # hard shutdown one second later.
            return self._json({"ok": True, "id": ev["id"],
                               "checks": LOG.checks(),
                               "pending": len(LOG.pending())})

        if p == "/api/kill":
            key  = (body.get("key") or "").strip()
            tier = (body.get("tier") or "").strip().lower()
            reason = (body.get("reason") or "").strip()
            if not key:
                return self._json({"error": "key required"}, 400)
            if tier not in ("red", "yellow", "dead"):
                return self._json({"error": "tier must be red, yellow or dead"}, 400)
            # RED is permanent in ghost.md and never comes off, and YELLOW parks a
            # company for three months. Neither may be recorded without a stated
            # reason -- a tier with no reason is unauditable six weeks later.
            # "dead" is the exception: the reason IS the tier.
            if tier in ("red", "yellow") and not reason:
                return self._json({"error": f"{tier} requires a reason"}, 400)
            ev = LOG.append("kill", {
                "key": key,
                "tier": tier,
                "reason": reason,
                "employer": body.get("employer") or "",
                "title": body.get("title") or "",
                "url": body.get("url") or "",
            })
            return self._json({"ok": True, "id": ev["id"],
                               "leadkills": LOG.leadkills(),
                               "pending": len(LOG.pending())})

        if p == "/api/build":
            key = (body.get("key") or "").strip()
            if not key:
                return self._json({"error": "key required"}, 400)
            # A request, not a build: the next 1am/6am sweep drains it into
            # dashboard-inbox.md and builds the folder. Same contract as kills.
            req = {"key": key,
                   "employer": body.get("employer") or "",
                   "title": body.get("title") or "",
                   "url": body.get("url") or "",
                   "note": (body.get("note") or "").strip()[:1000]}
            LOG.append("build", req)
            # Logged first, so a failed or missing CLI still leaves the request
            # for the next sweep. Then try to build it right now.
            try:
                builder.start(key, req, ROOT, cfg())
            except Exception as e:      # a builder bug must never lose the request
                print("instant build could not start:", e)
            return self._json({"ok": True, "buildreqs": LOG.buildreqs(),
                               "status": builder.all_status(),
                               "pending": len(LOG.pending())})

        if p == "/api/unbuild":
            key = (body.get("key") or "").strip()
            if not key:
                return self._json({"error": "key required"}, 400)
            LOG.append("unbuild", {"key": key})
            return self._json({"ok": True, "buildreqs": LOG.buildreqs(),
                               "pending": len(LOG.pending())})

        if p == "/api/unkill":
            key = (body.get("key") or "").strip()
            if not key:
                return self._json({"error": "key required"}, 400)
            # Undo is an append, never a delete. Valid any time before the next
            # sweep drains the queue; after that the ghost.md line is the record.
            LOG.append("unkill", {"key": key})
            return self._json({"ok": True, "leadkills": LOG.leadkills(),
                               "pending": len(LOG.pending())})

        if p == "/api/note":
            text = (body.get("text") or "").strip()
            if not text:
                return self._json({"error": "text required"}, 400)
            ev = LOG.append("note", {"key": f"note-{body.get('tab','general')}",
                                     "text": text, "tab": body.get("tab", "general")})
            return self._json({"ok": True, "id": ev["id"],
                               "pending": len(LOG.pending())})
        if p == "/api/pin":
            d = (body.get("date") or "").strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or not (body.get("title") or "").strip():
                return self._json({"error": "date (YYYY-MM-DD) and title required"}, 400)
            ev = add_pin(body)
            return self._json({"ok": True, "pin": ev, "pins": pins(), "pending": len(LOG.pending())})

        if p == "/api/unpin":
            key = (body.get("id") or "").strip()
            if not key:
                return self._json({"error": "id required"}, 400)
            LOG.append("unpin", {"key": key})
            return self._json({"ok": True, "pins": pins()})

        if p == "/api/win":
            text = (body.get("text") or "").strip()
            if not text:
                return self._json({"error": "text required"}, 400)
            add_win(body.get("date") or date.today().isoformat(), text)
            return self._json({"ok": True, "history": history(), "pending": len(LOG.pending())})

        if p == "/api/ask":
            q = (body.get("q") or "").strip()
            if not q:
                return self._json({"error": "q required"}, 400)
            res = ai_mod.ask(q, ai_context(), cfg())
            made_pins, made_wins = [], []
            for pn in (res.get("pins") or [])[:6]:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", str(pn.get("date", ""))) and pn.get("title"):
                    made_pins.append(add_pin(pn, source="ask"))
            for w in (res.get("wins") or [])[:6]:
                if w.get("text"):
                    add_win(w.get("date") or date.today().isoformat(), w["text"], source="ask")
                    made_wins.append(w)
            LOG.append("ask", {"key": "ask-log", "q": q[:600], "reply": (res.get("reply") or "")[:1200],
                               "engine": res.get("engine")})
            return self._json({"reply": res.get("reply", ""), "engine": res.get("engine"),
                               "pins": made_pins, "wins": made_wins})
        return self._json({"error": "unknown endpoint"}, 404)


def _match_event(b):
    """'pin agent fair dec 15 6pm' should attach to the real Agent Fair, so the
    pin carries its venue, leave-by and catch instead of being a bare string."""
    if b.get("event_id"):
        return b
    words = {w for w in re.findall(r"[a-z0-9]+", (b.get("title") or "").lower()) if len(w) > 2}
    best, score = None, 0
    for e in _load("events.json", {}).get("events", []):
        if e.get("date") != b.get("date"):
            continue
        ew = set(re.findall(r"[a-z0-9]+", e["title"].lower()))
        sc = len(words & ew)
        if sc > score:
            best, score = e, sc
    if best and score >= 1:
        b = dict(b, event_id=best["id"])
        if len(b.get("title", "")) < len(best["title"]):
            b["title"] = best["title"]
        if not b.get("time") and best.get("start24"):
            b["time"] = best["start24"]
        if not b.get("note"):
            b["note"] = " · ".join(x for x in [
                f"Leave by {best['leave_by']}" if best.get("leave_by") else "",
                best.get("venue", ""), best.get("url", "")] if x)
    return b


def add_pin(b, source="dashboard"):
    import uuid
    b = _match_event(b)
    payload = {"key": "pin-" + uuid.uuid4().hex[:12], "date": b.get("date"),
               "time": (b.get("time") or "")[:5], "title": (b.get("title") or "")[:160],
               "note": (b.get("note") or "")[:500], "event_id": b.get("event_id") or "",
               "source": source}
    LOG.append("pin", payload)
    return dict(payload, id=payload["key"])


def add_win(d, text, source="dashboard"):
    import uuid
    return LOG.append("win", {"key": "win-" + uuid.uuid4().hex[:12], "date": d,
                              "text": text[:400], "source": source})


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--root", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--no-build", action="store_true",
                    help="serve the existing data/*.json without re-parsing the workspace")
    a = ap.parse_args()
    ROOT = find_root(a.root)
    os.makedirs(DATA, exist_ok=True)
    print("workspace:", ROOT)
    print("(--no-build: serving cached data)" if a.no_build else rebuild())
    pend = len(LOG.pending())
    if pend:
        print(f"queue: {pend} event(s) waiting for the next sweep to drain")
    url = f"http://127.0.0.1:{a.port}/"
    # On Windows SO_REUSEADDR lets a second server bind the same port silently,
    # which is how a stale copy keeps answering. Refuse instead.
    if os.name == "nt":
        ThreadingHTTPServer.allow_reuse_address = False
    srv = None
    for _ in range(6):          # a self-restart may need a moment for the port to free
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
            break
        except OSError:
            time.sleep(1)
    if srv is None:
        print(f"already running at {url} -- opening it instead of starting a second copy")
        if not a.no_open:
            webbrowser.open(url)
        return
    print(f"dashboard: {url}   (ctrl-c to stop)")
    if not a.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    threading.Thread(target=_watch_code, args=(srv,), daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped. your ticks are saved in state/events.jsonl")
        return
    if _RESTART["now"]:
        srv.server_close()
        args = [x for x in sys.argv if x != "--no-open"] + ["--no-open"]
        print("server code changed -- restarting with the new version")
        subprocess.Popen([sys.executable] + args, cwd=HERE)
        sys.exit(0)


# ---------------------------------------------------------------- self-restart
# The page's own files (static/, data/) are re-read on every request, so a
# browser refresh picks those up. The server's PYTHON code is loaded once, so an
# update to it used to need a manual restart -- and a stale server answers new
# buttons with 404 ("could not save"). This watcher restarts the server when its
# code changes, but only if the new code compiles; a broken edit keeps the old
# server running rather than taking the dashboard down.
_RESTART = {"now": False}
_WATCH = ("serve.py", "eventlog.py", "points.py", "ai.py", "builder.py")


def _code_mtimes():
    out = {}
    for f in _WATCH:
        fp = os.path.join(HERE, f)
        if os.path.exists(fp):
            out[f] = os.path.getmtime(fp)
    return out


def _watch_code(srv):
    import py_compile
    base = _code_mtimes()
    while True:
        time.sleep(3)
        cur = _code_mtimes()
        if cur == base:
            continue
        time.sleep(1.5)                      # let a multi-file update finish writing
        cur = _code_mtimes()
        try:
            for f in cur:
                py_compile.compile(os.path.join(HERE, f), doraise=True)
        except Exception as e:
            print(f"code changed but does not compile, keeping the running version: {e}")
            base = cur
            continue
        _RESTART["now"] = True
        srv.shutdown()
        return


if __name__ == "__main__":
    main()
