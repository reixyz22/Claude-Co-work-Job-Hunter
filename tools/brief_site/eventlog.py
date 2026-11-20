"""
Append-only event log for the job-hunter dashboard.

DESIGN CONTRACT (this is the part that matters, read before changing anything):

  The user ticks checkboxes in a browser. A sweep (the 1am/6am scheduled task)
  reads those ticks later -- possibly MUCH later, because the computer gets shut
  off and runs get skipped. So:

  1. events.jsonl is APPEND-ONLY and is the source of truth. Nothing ever
     rewrites or truncates it. A crash mid-write loses at most the last line,
     and a half-written last line is skipped on read rather than poisoning the
     file.
  2. Every event carries a uuid. Draining is IDEMPOTENT: the sweep records which
     ids it has consumed in ingested.json. Re-running a sweep, running two
     sweeps, or restoring an old ingested.json can never double-apply an event.
  3. A skipped run is a no-op, not a loss. Events just queue. The next sweep to
     run -- tomorrow, or next week -- drains the whole backlog in order.
  4. checks.json is DERIVED and disposable. It is a fast-read projection of the
     event log for rendering. Delete it and it rebuilds exactly. Never treat it
     as truth.
  5. Writes are fsync'd. The user closing the laptop lid right after clicking is
     the expected case, not an edge case.
"""
import json, os, uuid, threading, tempfile
from datetime import datetime, timezone

_LOCK = threading.Lock()


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EventLog:
    def __init__(self, state_dir):
        self.dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.events_path = os.path.join(state_dir, "events.jsonl")
        self.ingested_path = os.path.join(state_dir, "ingested.json")
        self.checks_path = os.path.join(state_dir, "checks.json")

    # ---------- append ----------
    def append(self, kind, payload):
        ev = {
            "id": uuid.uuid4().hex,
            "ts": _utc(),
            "kind": kind,
            "payload": payload,
        }
        line = json.dumps(ev, ensure_ascii=False) + "\n"
        with _LOCK:
            # append + fsync: survives an immediate shutdown
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            self._rebuild_checks_locked()
        return ev

    # ---------- read ----------
    def all_events(self):
        out = []
        if not os.path.exists(self.events_path):
            return out
        with open(self.events_path, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    out.append(json.loads(raw))
                except json.JSONDecodeError:
                    # torn final line from an abrupt shutdown -- skip, never raise
                    continue
        return out

    def ingested_ids(self):
        if not os.path.exists(self.ingested_path):
            return set()
        try:
            with open(self.ingested_path, encoding="utf-8") as f:
                return set(json.load(f).get("ids", []))
        except Exception:
            return set()

    def pending(self):
        done = self.ingested_ids()
        return [e for e in self.all_events() if e["id"] not in done]

    def mark_ingested(self, ids):
        """Idempotent. Union, never replace -- so an older ingested.json
        restored from backup cannot resurrect already-applied events."""
        with _LOCK:
            cur = self.ingested_ids()
            cur.update(ids)
            self._atomic_write(self.ingested_path,
                               {"ids": sorted(cur), "updated": _utc()})

    # ---------- derived projection ----------
    def _rebuild_checks_locked(self):
        state = {}
        for e in self.all_events():
            p = e.get("payload") or {}
            key = p.get("key")
            if not key:
                continue
            if e["kind"] == "check":
                state[key] = {
                    "checked": bool(p.get("checked")),
                    "ts": e["ts"],
                    "note": p.get("note") or "",
                }
            elif e["kind"] == "uncheck":
                state[key] = {"checked": False, "ts": e["ts"], "note": ""}
        self._atomic_write(self.checks_path, {"checks": state, "rebuilt": _utc()})
        return state  # the checks dict itself, NOT the file envelope

    def leadkills(self):
        """Fold kill/unkill events into {lead_key: {...}}. Derived and
        disposable exactly like checks(): the event log stays the truth, and an
        unkill is a new append rather than an edit, so nothing is ever rewritten.
        Last event per key wins, so kill -> unkill -> kill behaves as expected."""
        state = {}
        for e in self.all_events():
            p = e.get("payload") or {}
            key = p.get("key")
            if not key:
                continue
            if e["kind"] == "kill":
                state[key] = {
                    "tier": p.get("tier") or "yellow",
                    "reason": p.get("reason") or "",
                    "employer": p.get("employer") or "",
                    "title": p.get("title") or "",
                    "url": p.get("url") or "",
                    "ts": e["ts"],
                    "id": e["id"],
                }
            elif e["kind"] == "unkill":
                state.pop(key, None)
        return state

    def buildreqs(self):
        """Fold build/unbuild events into {key: {...}}: leads the user asked the
        next sweep to build materials for. Derived like leadkills(); the log is
        the truth and a cancel is an append, never an edit."""
        state = {}
        for e in self.all_events():
            p = e.get("payload") or {}
            key = p.get("key")
            if not key:
                continue
            if e["kind"] == "build":
                state[key] = {"employer": p.get("employer") or "", "title": p.get("title") or "",
                              "url": p.get("url") or "", "note": p.get("note") or "",
                              "ts": e["ts"], "id": e["id"]}
            elif e["kind"] == "unbuild":
                state.pop(key, None)
        return state

    def checks(self):
        if not os.path.exists(self.checks_path):
            with _LOCK:
                return self._rebuild_checks_locked()
        try:
            with open(self.checks_path, encoding="utf-8") as f:
                return json.load(f).get("checks", {})
        except Exception:
            with _LOCK:
                return self._rebuild_checks_locked()

    def _atomic_write(self, path, obj):
        d = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
