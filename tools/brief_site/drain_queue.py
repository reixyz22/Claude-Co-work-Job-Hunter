#!/usr/bin/env python3
"""
Drain the dashboard's event queue into the workspace. A SWEEP runs this --
never the web server, so nothing a browser does can corrupt applied.md.

Called at the top of every 1am / 6am sweep:

    python3 drain_queue.py --root /path/to/workspace          # show + apply
    python3 drain_queue.py --root ... --dry-run               # show only

WHY THIS SHAPE: the user ticks "applied" at 11pm and shuts the laptop. The 1am
run may not happen -- skipped, offline, billing lapse, whatever. The tick is
already durable on disk, so the backlog simply drains on whatever run happens
next, in order, exactly once. Missing a run costs nothing but latency.
"""
import argparse, json, os, re, sys
from datetime import datetime, date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eventlog import EventLog  # noqa: E402


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




def split_lead(p):
    """A dashboard lead title is usually "Employer - Role". ghost.md wants them
    in separate columns, so split on the first dash-ish separator and fall back
    to the employer field rather than guessing."""
    t = (p.get("title") or "").strip()
    for sep in (" - ", " \u2014 ", " \u2013 ", " | "):
        if sep in t:
            co, role = t.split(sep, 1)
            return co.strip(), role.strip()
    co = (p.get("employer") or t or "unknown").strip()
    return (co.title() if co == co.lower() else co), (t if t and t != co else "role not captured")


def apply_kills(ghost_path, kills):
    """Write queued kills into ghost.md.

    RED lines are INSERTED into the RED section, because that section is a flat
    list the sweeps read top-down; appending them at the end of the file would
    leave them outside the section and a later sweep would not see them.
    YELLOW and dead links go in a dated block at the end, which is how every
    sweep already logs its own kills. Nothing is ever rewritten or deleted.
    """
    if not os.path.exists(ghost_path):
        return 0, 0
    with open(ghost_path, encoding="utf-8") as f:
        text = f.read()

    today = date.today().isoformat()
    reds, others = [], []
    for e, p in kills:
        co, role = split_lead(p)
        tier, reason = p.get("tier"), (p.get("reason") or "").strip()
        url = p.get("url") or ""
        when = (e["ts"] or "")[:10] or today
        if tier == "red":
            reds.append(f"RED | {co} | all roles | permanent | {reason} "
                        f"[marked RED on the dashboard {when}, drained {today}"
                        f"{'; req seen at ' + url if url else ''}]\n")
        elif tier == "dead":
            others.append(f"YELLOW | {co} | {role} | KILLED {when} | Dead link reported from the "
                          f"dashboard: the posting is gone or the URL is broken. Not a judgment on "
                          f"the employer -- re-check their own ATS before treating the company as "
                          f"closed.{' Link was ' + url if url else ''}\n")
        else:
            others.append(f"YELLOW | {co} | {role} | KILLED {when} | {reason} "
                          f"[marked YELLOW on the dashboard, drained {today}]"
                          f"{' ' + url if url else ''}\n")

    if reds:
        # insert after the last existing top-level RED line
        lines = text.split("\n")
        last = max((i for i, l in enumerate(lines) if l.startswith("RED | ")), default=None)
        if last is None:
            text += "\n" + "".join(reds)
        else:
            head = "\n".join(lines[:last + 1])
            tail = "\n".join(lines[last + 1:])
            text = head + "\n" + "".join(reds).rstrip("\n") + "\n" + tail
    if others:
        text = text.rstrip("\n") + (
            f"\n\n## {today} — kills sent from the dashboard\n\n" + "".join(others))

    with open(ghost_path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(reds), len(others)


def next_applied_number(applied_path):
    n = 0
    if os.path.exists(applied_path):
        with open(applied_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^(\d+)\.\s+.*\|", line.strip())
                if m:
                    n = max(n, int(m.group(1)))
    return n + 1


def builder_status(key):
    try:
        import builder
        return builder.status(key)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    a.root = find_root(a.root)
    log = EventLog(os.path.join(HERE, "state"))
    pending = log.pending()
    if not pending:
        print("queue empty -- nothing to drain")
        return

    applied_path = os.path.join(a.root, "applied.md")
    applies, tasks, notes, cal = [], [], [], []
    kills, unkilled = [], set()
    builds, unbuilt = [], set()
    # Walk backwards first so a kill the user undid before the sweep ran is
    # never written to ghost.md. The undo is an append, not a delete, so this
    # is the only place the two have to be reconciled.
    for e in pending:
        if e["kind"] == "unkill":
            unkilled.add((e.get("payload") or {}).get("key"))
        if e["kind"] == "unbuild":
            unbuilt.add((e.get("payload") or {}).get("key"))
    for e in pending:
        p = e.get("payload") or {}
        if e["kind"] == "kill" and p.get("key") not in unkilled:
            kills.append((e, p))
        if e["kind"] == "build" and p.get("key") not in unbuilt:
            # already built instantly on the PC by builder.py -> nothing for the sweep to do
            if (builder_status(p.get("key")) or {}).get("state") != "done":
                builds.append((e, p))
        if e["kind"] == "note":
            notes.append((e, p))
        elif e["kind"] in ("pin", "unpin", "win"):
            cal.append((e, p))
        elif e["kind"] == "check" and p.get("checked"):
            (applies if p.get("kind") == "applied" else tasks).append((e, p))

    print(f"=== {len(pending)} pending event(s) ===")
    for _, p in applies:
        print(f"  APPLIED  {p.get('label')}  {p.get('url','')}")
    for _, p in tasks:
        print(f"  TASK     {p.get('kind')}: {p.get('label')}")
    for _, p in notes:
        print(f"  NOTE     [{p.get('tab')}] {p.get('text')[:90]}")
    for _, p in kills:
        print(f"  KILL     {(p.get('tier') or '').upper():<6} {p.get('title')}"
              f"{'  -- ' + p['reason'] if p.get('reason') else ''}")

    for _, p in builds:
        print(f"  BUILD    {p.get('title')}  {p.get('url','')}")

    if a.dry_run:
        print("\n--dry-run: nothing written, queue left intact")
        return

    # applied.md is appended to ONLY here, with the canonical format, and only
    # for events the user explicitly ticked as an application.
    if applies:
        n = next_applied_number(applied_path)
        lines = []
        for e, p in applies:
            when = (e["ts"] or "")[:10] or date.today().isoformat()
            lines.append(
                f"{n}. {p.get('label','(unnamed)')} | Applied {when} "
                f"(ticked on the dashboard; drained {date.today().isoformat()}) "
                f"| Salary: not logged | Status: PENDING "
                f"| SOURCE: dashboard checkbox | {p.get('url','')}\n")
            n += 1
        with open(applied_path, "a", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"\nappended {len(lines)} entr(ies) to applied.md")

    # ghost.md is appended to ONLY here, never by the web server.
    if kills:
        nr, no = apply_kills(os.path.join(a.root, "ghost.md"), kills)
        print(f"wrote {nr} RED and {no} YELLOW/dead-link entr(ies) to ghost.md")
        if nr:
            print("  NOTE: RED is permanent and never comes off. "
                  "Check those lines if any was a misclick.")

    inbox = os.path.join(a.root, "dashboard-inbox.md")
    for _, p in cal:
        print(f"  CAL      {p.get('date','')} {p.get('time','')} {p.get('title') or p.get('text') or p.get('key')}")

    if builds:
        # The sweep reads dashboard-inbox.md at STEP 0.5; a BUILD MATERIALS line is
        # an instruction from the user to build that lead's folder this run.
        with open(inbox, "a", encoding="utf-8") as f:
            f.write(f"\n## Materials requested {datetime.now().isoformat(timespec='seconds')}\n")
            for e, p in builds:
                f.write(f"- BUILD MATERIALS: {p.get('title') or p.get('employer')} | {p.get('url','')} "
                        f"(requested {e['ts'][:16]} on the dashboard)"
                        f"{' -- USER SAYS: ' + p['note'] if p.get('note') else ''}\n")
        print(f"appended {len(builds)} materials request(s) to dashboard-inbox.md")

    if tasks or notes or cal:
        with open(inbox, "a", encoding="utf-8") as f:
            f.write(f"\n## Drained {datetime.now().isoformat(timespec='seconds')}\n")
            for e, p in tasks:
                f.write(f"- [x] {p.get('kind')}: {p.get('label')} "
                        f"(ticked {e['ts'][:16]})\n")
            for e, p in notes:
                f.write(f"- NOTE [{p.get('tab')}] {e['ts'][:16]}: {p.get('text')}\n")
            for e, p in cal:
                if e["kind"] == "win":
                    f.write(f"- WIN {p.get('date')}: {p.get('text')} (logged {e['ts'][:16]})\n")
                elif e["kind"] == "pin":
                    f.write(f"- PINNED {p.get('date')} {p.get('time') or ''}: {p.get('title')}"
                            f"{' — ' + p['note'] if p.get('note') else ''} (calendar, {p.get('source','dashboard')})\n")
                else:
                    f.write(f"- UNPINNED {p.get('key')}\n")
        print(f"appended {len(tasks)} task(s) + {len(notes)} note(s) + {len(cal)} calendar item(s) to dashboard-inbox.md")

    log.mark_ingested([e["id"] for e in pending])
    print(f"marked {len(pending)} event(s) ingested -- safe to re-run, this is idempotent")


if __name__ == "__main__":
    main()
