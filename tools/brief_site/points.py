"""
Points, streaks and rollups, computed from the event log.

DESIGN NOTES, because the psychology here is the feature:

* Points are awarded on the FIRST time a key is checked, and are NEVER revoked.
  Unchecking something is not punished. If you tick "applied" and then realise you
  didn't finish, un-ticking it should not take the day's score away -- that turns the
  checkbox into a thing you avoid touching, which is the opposite of the point.

* The daily target is deliberately LOW (25). One application, or one study module,
  or three freebies, clears it. A target you hit on a bad day is a target you keep
  coming back to; a target you miss four days running is one you stop looking at.

* The streak counts a day as "kept" at 1 point, not at target. And it looks back from
  yesterday if today is still empty, so the number never reads as broken at 9am before
  you've done anything.

* Freebies score real points (5) rather than token ones. They exist for days when the
  alternative is zero.
"""
import os
from datetime import date, datetime, timedelta, timezone

DEFAULT_VALUES = {
    "applied":  25,   # the thing that actually moves the job hunt
    "study":    15,   # a module from a lane
    "research":10,    # signed up / investigated a platform or employer
    "task":     10,   # a real checklist item
    "freebie":   5,   # low-activation, still real
    "note":      2,   # wrote something down for the next sweep
    "win":      10,   # logged something you did (ask bar / calendar) -- counts on its own day
    "event":    20,   # went to an IRL event
}
DAILY_TARGET = 25
WEEKLY_TARGET = 120
MONTHLY_TARGET = 450


def _d(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    except Exception:
        return None


def score_events(events, freebie_keys=(), values=None):
    """-> (per_day {date: pts}, awarded [{key,kind,pts,day,label}])"""
    vals = dict(DEFAULT_VALUES)
    if values:
        vals.update(values)
    first_true, meta = {}, {}
    for e in events:
        p = e.get("payload") or {}
        key = p.get("key")
        if not key:
            continue
        if e.get("kind") == "win":
            # a win is dated by what the user says, not by when it was typed
            try:
                d = date.fromisoformat(str(p.get("date"))[:10])
            except Exception:
                d = _d(e.get("ts"))
            if d:
                first_true.setdefault(("win", e["id"]), d)
                meta[("win", e["id"])] = ("win", p.get("text", "")[:60])
            continue
        if e.get("kind") == "note":
            # notes score each time; they are cheap and additive
            d = _d(e.get("ts"))
            if d:
                first_true.setdefault(("note", e["id"]), d)
                meta[("note", e["id"])] = ("note", p.get("text", "")[:60])
            continue
        if e.get("kind") == "check" and p.get("checked"):
            if key not in first_true:          # first tick only -- no farming
                d = _d(e.get("ts"))
                if d:
                    first_true[key] = d
                    kind = "freebie" if key in freebie_keys else (p.get("kind") or "task")
                    meta[key] = (kind, p.get("label", ""))

    per_day, awarded = {}, []
    for key, day in first_true.items():
        kind, label = meta.get(key, ("task", ""))
        pts = vals.get(kind, vals["task"])
        per_day[day] = per_day.get(day, 0) + pts
        awarded.append({"key": key if isinstance(key, str) else key[1],
                        "kind": kind, "pts": pts, "day": day.isoformat(),
                        "label": label})
    return per_day, awarded


def streak(per_day):
    """Consecutive days with at least 1 point. Starts from yesterday when today is
    still empty, so an untouched morning never shows a broken streak."""
    if not per_day:
        return 0
    today = date.today()
    cur = today if per_day.get(today) else today - timedelta(days=1)
    n = 0
    while per_day.get(cur):
        n += 1
        cur -= timedelta(days=1)
    return n


def summary(events, freebie_keys=(), values=None):
    per_day, awarded = score_events(events, freebie_keys, values)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())          # Monday
    month_start = today.replace(day=1)

    s = lambda since: sum(p for d, p in per_day.items() if d >= since)
    today_pts = per_day.get(today, 0)
    week_pts, month_pts = s(week_start), s(month_start)

    # last 14 days, oldest first, for a sparkline
    hist = [{"day": (today - timedelta(days=i)).isoformat(),
             "pts": per_day.get(today - timedelta(days=i), 0)}
            for i in range(13, -1, -1)]

    by_kind = {}
    for a in awarded:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + a["pts"]

    return {
        "today": today_pts, "week": week_pts, "month": month_pts,
        "total": sum(per_day.values()),
        "daily_target": DAILY_TARGET,
        "weekly_target": WEEKLY_TARGET,
        "monthly_target": MONTHLY_TARGET,
        "day_done": today_pts >= DAILY_TARGET,
        "streak": streak(per_day),
        "active_days": len(per_day),
        "history": hist,
        "by_kind": by_kind,
        "values": dict(DEFAULT_VALUES, **(values or {})),
        "recent": sorted(awarded, key=lambda a: a["day"], reverse=True)[:12],
    }
