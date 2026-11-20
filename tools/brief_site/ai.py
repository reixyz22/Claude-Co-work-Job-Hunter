"""
The dashboard's ask bar.  Two layers, so it always does *something*:

  1. A local command parser that needs nothing installed:
       pin agent fair dec 15 6pm        -> calendar pin
       remind me fri 9am follow up w/ the recruiter
       log got 2 referrals at the meetup   -> accomplishment for today
       log yesterday: finished the testing module
  2. A real model for everything else, tried in this order:
       a. the Claude Code CLI (`claude -p`) if it is on PATH -- uses your plan
       b. ANTHROPIC_API_KEY in the environment -- direct HTTPS, stdlib only
     The model can answer AND propose pins/wins; the server writes them through
     the same fsync'd event log as a checkbox.

Nothing here writes markdown. Pins and wins are events; a sweep drains them.
"""
import json, os, re, shutil, subprocess, tempfile, urllib.request
from datetime import date, datetime, timedelta

WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

PIN_RE = re.compile(r"^\s*/?(pin|add|remind(?:\s+me)?|schedule|put|cal(?:endar)?)\b[:\s]*", re.I)
WIN_RE = re.compile(r"^\s*/?(log|win|won|done|did)\b[:\s]*", re.I)


# ---------------------------------------------------------------- date / time
def parse_when(text, today=None):
    """-> (date|None, 'HH:MM'|'', text_with_date_and_time_removed)"""
    today = today or date.today()
    t = " " + text + " "
    d = None

    def cut(m):
        nonlocal t
        t = t[:m.start()] + " " + t[m.end():]

    m = re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", t)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3))); cut(m)
    if not d:
        m = re.search(r"\b(?:on\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", t, re.I)
        if m:
            mo, dy = MONTHS[m.group(1)[:3].lower()], int(m.group(2))
            y = today.year + (1 if mo < today.month - 6 else 0)
            try:
                d = date(y, mo, dy); cut(m)
            except ValueError:
                pass
    if not d:
        m = re.search(r"\b(?:on\s+)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
        if m:
            y = int(m.group(3)) if m.group(3) else today.year
            if y < 100: y += 2000
            try:
                d = date(y, int(m.group(1)), int(m.group(2))); cut(m)
            except ValueError:
                pass
    if not d:
        m = re.search(r"\b(today|tonight|this evening|tomorrow|tmrw|yesterday)\b", t, re.I)
        if m:
            w = m.group(1).lower()
            d = today + timedelta(days={"tomorrow": 1, "tmrw": 1, "yesterday": -1}.get(w, 0)); cut(m)
    if not d:
        m = re.search(r"\b(?:on\s+)?(next\s+|this\s+|last\s+)?(mon|tue|wed|thu|fri|sat|sun)(?:day|sday|nesday|rsday|urday)?\.?\b", t, re.I)
        if m:
            target = WD.index(m.group(2).lower()[:3])
            if (m.group(1) or "").strip().lower() == "last":
                delta = (today.weekday() - target) % 7 or 7
                d = today - timedelta(days=delta)
            else:
                delta = (target - today.weekday()) % 7
                if (m.group(1) or "").strip().lower() == "next" and delta == 0:
                    delta = 7
                d = today + timedelta(days=delta)
            cut(m)

    hhmm = ""
    m = re.search(r"\b(?:at\s+|@\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)\b", t, re.I)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3).lower().startswith("p") else 0)
        hhmm = f"{h:02d}:{m.group(2) or '00'}"; cut(m)
    else:
        m = re.search(r"\b(?:at\s+|@\s*)([01]?\d|2[0-3]):([0-5]\d)\b", t)
        if m:
            hhmm = f"{int(m.group(1)):02d}:{m.group(2)}"; cut(m)
        else:
            m = re.search(r"\b(?:at\s+)?(noon|midnight)\b", t, re.I)
            if m:
                hhmm = "12:00" if m.group(1).lower() == "noon" else "00:00"; cut(m)
    rest = re.sub(r"\s+", " ", t).strip(" ,.:-")
    rest = re.sub(r"^(to|that|about|for)\s+", "", rest, flags=re.I)
    return d, hhmm, rest


def local_command(q, today=None):
    """Explicit commands handled without a model. -> dict or None"""
    today = today or date.today()
    m = PIN_RE.match(q)
    if m:
        d, hhmm, rest = parse_when(q[m.end():], today)
        if not d:
            return {"reply": "I need a day for that pin — try “pin agent fair dec 15 6pm” or “remind me fri 9am …”.",
                    "pins": [], "wins": []}
        return {"reply": f"Pinned to {d.strftime('%a %b')} {d.day}" + (f" at {fmt12(hhmm)}" if hhmm else "") + ".",
                "pins": [{"date": d.isoformat(), "time": hhmm, "title": rest[:140] or "Pinned", "note": ""}],
                "wins": []}
    m = WIN_RE.match(q)
    if m:
        body = q[m.end():]
        d, _, rest = parse_when(body, today)
        if not re.search(r"\b(today|yesterday|tonight|(?:mon|tue|wed|thu|fri|sat|sun)(?:day|sday|nesday|rsday|urday)?\b|(?:jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d|\d+/\d+|20\d\d-)", body, re.I):
            d, rest = today, body.strip()
        d = d or today
        while d > today:          # "log monday" means the one that already happened
            d -= timedelta(days=7)
        return {"reply": f"Logged for {d.strftime('%a %b')} {d.day}.",
                "pins": [], "wins": [{"date": d.isoformat(), "text": rest[:300] or body.strip()[:300]}]}
    return None


def fmt12(hhmm):
    if not hhmm:
        return ""
    h, mi = map(int, hhmm.split(":"))
    return f"{(h % 12) or 12}:{mi:02d} {'PM' if h >= 12 else 'AM'}"


# ---------------------------------------------------------------- model
SYSTEM = """You are the assistant built into the user's job-hunt dashboard. {user_context}
Answer in 1-4 short sentences, plain text, no markdown headers. Be direct; they decide, you don't manage their schedule.
Times: always lead with the START time, e.g. "STARTS 6:00 PM Wed Dec 2". Never RSVP or register for anything.
If they ask you to put something on the calendar, remind them, or peg an event, add it to "pins".
If they tell you something they did, add it to "wins" (dated; default today).
Reply with ONE JSON object and nothing else:
{"reply": "...", "pins": [{"date":"YYYY-MM-DD","time":"HH:MM or empty","title":"...","note":"...","event_id":"ev-... or empty"}], "wins": [{"date":"YYYY-MM-DD","text":"..."}]}"""


def build_prompt(q, ctx, cfg=None):
    # user_context lives in config.json (e.g. "Based in Chicago, transit only, no car.")
    system = SYSTEM.replace("{user_context}", ((cfg or {}).get("user_context") or "").strip())
    who = ((cfg or {}).get("user_name") or "User").strip()
    return f"{system}\n\n--- DASHBOARD CONTEXT (today is {date.today().isoformat()}, {date.today():%A}) ---\n{ctx}\n--- END CONTEXT ---\n\n{who}: {q}"


def _extract_json(text):
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and "reply" in obj:
                obj.setdefault("pins", []); obj.setdefault("wins", [])
                return obj
        except Exception:
            pass
    return {"reply": text[:1500] or "(empty answer)", "pins": [], "wins": []}


def _via_cli(prompt, cfg):
    exe = shutil.which(cfg.get("claude_cli") or "claude")
    if not exe:
        return None
    base = [exe, "-p"]
    if cfg.get("ai_cli_model"):
        base += ["--model", cfg["ai_cli_model"]]
    kw = dict(capture_output=True, text=True, encoding="utf-8", errors="replace",
              timeout=int(cfg.get("ai_timeout", 120)),
              # run outside the workspace so the CLI doesn't auto-load a 140 KB CLAUDE.md
              cwd=tempfile.gettempdir())
    # Prompt on stdin first: it survives Windows .cmd shims, which mangle long
    # quoted arguments. Fall back to the argument form for CLIs that want it.
    r = subprocess.run(base, input=prompt, **kw)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout
    if len(prompt) < 24000:
        r2 = subprocess.run(base + [prompt], **kw)
        if r2.returncode == 0 and r2.stdout.strip():
            return r2.stdout
        r = r2
    raise RuntimeError(((r.stderr or r.stdout or "claude CLI failed").strip())[:300])


def _via_api(prompt, cfg):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": cfg.get("ai_model", "claude-sonnet-4-5"), "max_tokens": 900,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=int(cfg.get("ai_timeout", 120))) as resp:
        data = json.load(resp)
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def engine_name(cfg):
    if shutil.which(cfg.get("claude_cli") or "claude"):
        return "claude-cli"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api"
    return "offline"


def ask(q, ctx, cfg=None):
    cfg = cfg or {}
    local = local_command(q)
    if local:
        local["engine"] = "local"
        return local
    prompt = build_prompt(q, ctx, cfg)
    errors = []
    for name, fn in (("claude-cli", _via_cli), ("api", _via_api)):
        try:
            out = fn(prompt, cfg)
        except Exception as e:  # noqa: BLE001 -- surface, then try the next engine
            errors.append(f"{name}: {e}")
            continue
        if out is not None:
            res = _extract_json(out)
            res["engine"] = name
            return res
    msg = ("No model is reachable from here, so only the offline commands work: "
           "“pin <thing> <day> <time>” and “log <what you did>”. "
           "To turn on real answers, install Claude Code (so `claude` is on PATH) "
           "or set ANTHROPIC_API_KEY before starting the dashboard.")
    if errors:
        msg += "  (" + "; ".join(errors)[:300] + ")"
    return {"reply": msg, "pins": [], "wins": [], "engine": "offline"}
