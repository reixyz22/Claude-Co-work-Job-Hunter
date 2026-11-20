# Brief Site — the job hunter's dashboard

A local web dashboard for the daily-job-hunter plugin. Finished briefs, expandable
leads with apply links, a study plan, a notes inbox, and an AI-training-work lane —
with checkboxes that feed back into the pipeline.

**Python standard library only.** No pip install, no node, no build step, no CDN.
If `python3` runs, this runs.

## Start it

```bash
python3 serve.py                       # http://127.0.0.1:8787, opens a browser
python3 serve.py --port 9000           # different port
python3 serve.py --root /path/to/ws    # a workspace other than ~/mnt/Claude
python3 serve.py --no-build            # serve cached data, skip re-parsing
```

Binds to `127.0.0.1` only. Nothing is exposed off the machine.

## How the feedback loop works, and why it survives you closing the laptop

This is the part worth understanding, because it is the part that is easy to get
wrong and silently lose someone's work.

```
  browser tick  ──►  POST /api/check  ──►  state/events.jsonl   (append + fsync)
                                                   │
                                                   ▼
                                      python3 drain_queue.py     (a SWEEP runs this)
                                                   │
                                   ┌───────────────┴───────────────┐
                                   ▼                               ▼
                             applied.md                   dashboard-inbox.md
                        (applications only,              (tasks, study, notes)
                         canonical format)
```

1. **`state/events.jsonl` is append-only and is the source of truth.** Nothing
   rewrites or truncates it. The browser only gets its confirmation after the line
   is on disk and `fsync`'d, so a tick you *saw* land is a tick that survives a
   hard shutdown one second later. A torn final line from an abrupt power-off is
   skipped on read rather than poisoning the file.
2. **A skipped sweep costs nothing but latency.** Ticks queue. Whatever run
   happens next — tomorrow, next week, after a billing lapse — drains the whole
   backlog in order. There is no window in which a tick is lost because a run
   didn't happen.
3. **Draining is idempotent.** Every event has a uuid; consumed ids go in
   `state/ingested.json` as a union, never a replacement. Re-running a sweep,
   running two, or restoring an old `ingested.json` can never double-apply.
4. **The web server never writes to a markdown file.** Only `drain_queue.py` does,
   and only a sweep runs that. A browser cannot corrupt `applied.md` — which
   matters, because `applied.md` is the kill-list every sweep reads before ranking.
5. **`state/checks.json` is a derived projection and is disposable.** Delete it;
   it rebuilds exactly from the event log. Never treat it as truth.

## Wiring it into the sweeps

At the **top** of the 1am and 6am runs, before any searching:

```bash
python3 tools/brief_site/drain_queue.py --root "$WORKSPACE"
```

At the **end**, after the brief is written:

```bash
python3 tools/brief_site/build_site.py          # re-parse briefs into data/*.json
```

Use `--dry-run` on the drain to see what's queued without applying it.

## Calendar, events, log and the ask bar (added 2026-11-19)

- **Events** — every event the IRL event finder logged in `events.md`, parsed by
  `build_events.py` (deduped across runs, kills applied, STATUS lines honoured).
  Pin one and it lands on the calendar; past ones get an "I went" button.
- **Calendar** — month grid of events, your pins, and a count of what you got done
  each day. Click a day for the full schedule (start / leave-by / catch) and that
  day's log; pin something or log a win from there.
- **Log** — running history: applications (from `applied.md` and ticks), study,
  events attended, wins you typed, by day.
- **Ask bar** (press `/`) — `pin <thing> <day> <time>`, `remind me fri 9am …` and
  `log <what you did>` work offline and instantly. Anything else goes to Claude:
  the Claude Code CLI if `claude` is on PATH, else `ANTHROPIC_API_KEY`. The model
  sees upcoming events, pins, recent wins, top leads and pinned notes, and can pin
  or log for you. Optional `config.json` keys: `ai_model`, `ai_cli_model`,
  `ai_timeout`, `claude_cli`.

Pins, unpins, wins and asks are events in the same fsync'd `state/events.jsonl`;
`drain_queue.py` writes PINNED / WIN lines into `dashboard-inbox.md` for the sweeps.

## Files

| Path | What it is |
|---|---|
| `serve.py` | The local server. stdlib `http.server`. |
| `eventlog.py` | Append-only event log. The durability contract lives here. |
| `build_site.py` | Parses `brief-*.md` + `email-check-*.md` (1pm checks; KILLED rows never become cards), `applied.md`, `ghost.md` → `data/*.json`. Read-only on the workspace. |
| `drain_queue.py` | Sweep-side consumer. The only thing that writes markdown. |
| `build_events.py` | Parses `events.md` + `applied.md` → `data/events.json`, `data/history_static.json`. Read-only. |
| `ai.py` | Ask bar: offline pin/log parser, then Claude CLI / API. |
| `static/` | `index.html`, `app.js`, `styles.css`. No framework. |
| `data/` | Generated. Safe to delete; rebuilt by `build_site.py`. |
| `state/` | **Not generated.** Your ticks live here. Do not delete. |

`build_site.py` refuses to write when it finds no briefs under `--root`, so a wrong
path reports an error instead of silently blanking good data.

## Design notes

- **Today's load is a dial, not a guess**: Easy (3) · Normal (6) · Catch-up (12) ·
  Everything. Default is Easy, because a dashboard that opens on sixteen tasks is a
  dashboard you stop opening. The setting persists, so a catch-up stretch stays set
  until it's dialled back. Picks are deduped by company and drawn from the last 14 days.
- **The 14-day rule is a kill, not a preference.** Non-internship leads older than 14
  days (by an employer-sourced date) are marked `expired`, struck through, excluded
  from Today at *every* load setting, and hidden from the default Leads filter. The
  dial can make the day busier; it cannot resurrect a dead req. Internships and co-ops
  are exempt — they post on cohort cycles, so posting age doesn't measure pool burn.
- **An unparseable age is not a kill.** Older briefs used different table columns, so
  `age_days: null` means this parser couldn't read it, not that the posting is undated.
  Those stay visible and are simply never promoted to Today.
- **The "screened out" counter in the header** shows how many leads the pipeline
  killed so you never saw them, with no detail. Deliberately ad-blocker shaped:
  the number is the point.
- Light and dark both ship; it follows the OS and the toggle is remembered.

## Killing a lead from the dashboard (added 2026-11-19)

Every lead card carries three quiet buttons under it: **Red**, **Yellow**, **Dead link**.
They are dimmed until you hover the card, so they stay out of the way.

| Button | What it means | Reason required |
|---|---|---|
| **Red** | Permanent. Ethics or scam tier. The whole company is skipped from now on and it never comes off. | **Yes** |
| **Yellow** | This req is no good. Parks the company for three months. | **Yes** |
| **Dead link** | The posting is gone or the URL is broken. Recorded as YELLOW with a dead-link reason, explicitly noting it is not a judgment on the employer. | No, one tap |

Red and Yellow open a row of preset reason chips plus a free-text box. The presets live in
`config.json` under `kill_reasons` and are hand-editable; no code change needed.

**Nothing is written to a markdown file by the web server.** A kill appends one event to
`state/events.jsonl` exactly like a checkbox tick, and the next sweep's `drain_queue.py` writes it
into `ghost.md`:

- RED lines are **inserted into the `## RED — Permanent Kills` section**, because the sweeps read
  that section top-down. Appending them at the end of the file would leave them outside the section
  and a later sweep would never see them.
- YELLOW and dead links go into a dated `## <date> — kills sent from the dashboard` block at the end,
  which is how every sweep already logs its own kills.

Killed leads disappear from Live, Today and every other view and reappear only under the
**Killed** filter, which carries a count. **Undo is available right up until a sweep drains the
queue** — "Put back" on the card, or the Undo link in the toast. The undo is an append (`unkill`),
never a delete, and the drain reconciles the two so a kill you took back never reaches `ghost.md`.

Because the drain already runs at STEP 0.5 of both sweeps, no sweep or skill change was needed.
