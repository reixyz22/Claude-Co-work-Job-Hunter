---
name: morning-brief
description: Morning verification + delivery sweep. Verifies the apply links from last night's research, fills gaps, and produces the ranked brief the user reads with coffee. Runs unattended via scheduled task at 6am local time on weekdays. Not normally invoked manually.
---

# Morning brief — verification + delivery

Light second-pass sweep. Read `<workspace>/profile.md` for context.

## THE DASHBOARD IS THE DELIVERY SURFACE (read first)

The brief is delivered through the local dashboard (`tools/brief_site`, served at
http://127.0.0.1:8787 by `start-dashboard.bat` / `start-dashboard.sh`), not as a loose
markdown file the user has to go find. Every run, without exception:

1. **STEP 0.5** drains the dashboard's event queue before any searching.
2. **STEP 6** writes the brief as `<workspace>/brief-YYYY-MM-DD-6am.md` with a
   dashboard-parseable lead table (header spec in STEP 6 item 7).
3. **STEP 99** rebuilds the site and confirms today's brief and leads actually landed.
4. Every pointer to the user (brief footer, chat summary, push notification) sends them
   to the dashboard's Today tab first; the markdown file is the archive behind it.

A run that writes a brief but skips STEP 99, or writes it under a name the site does not
ingest, has not delivered anything. If the build fails, say so in the notification.

## STEP 0 — Read before anything

1. `<workspace>/applied.md`
2. `<workspace>/ghost.md`
3. `<workspace>/pattern-signals.md` — read it back to yourself before any output.
4. `<workspace>/boards.md` — note current karma + tiers (CORE/ROTATION/DORMANT/BLOCKED) + blocked domains.


## STEP 0.4 — Drift check

```bash
python3 tools/drift_check.py --live
```

Optional: `drift_check.py` is a workspace-specific scanner for claims you have
retired (old metrics, banned phrasings). If your workspace has no such file, skip
this step.

Exits non-zero when a live file still carries a claim an earlier ruling killed.
Fix those before building anything, because the next resume will copy them forward.
`applications/*` and the brief archive are history and are never rewritten.
Unresolved conflicts live in `conflicts.md`; surface anything marked OPEN in the brief
ONCE, then leave it alone until the user rules.

## STEP 0.5 — Drain the dashboard queue (RUN THIS BEFORE SEARCHING)

The user ticks checkboxes on the local dashboard (`tools/brief_site`). Those ticks
are queued on disk, not applied live. Drain them first, because an "applied" tick
changes the kill-check for this very run:

```bash
python3 tools/brief_site/drain_queue.py --root "$WORKSPACE"
```

- **Expect a backlog.** The computer gets shut off and runs get skipped. Events
  queue until a sweep runs, so a drain covering several days is normal, not a bug.
- It is **idempotent** -- safe to run twice, safe to re-run after a crash.
- It appends applications to `applied.md` in the canonical format, and tasks and
  notes to `dashboard-inbox.md`. **Read `dashboard-inbox.md` after draining** --
  notes the user wrote are addressed to this run.
- **`BUILD MATERIALS:` lines are the user asking for a folder.** The dashboard's
  "Build materials please" button drains into `dashboard-inbox.md` as
  `- BUILD MATERIALS: <lead> | <url> (requested ...)`. Treat every one not yet
  handled as a top-priority build THIS run, whatever its rank: verify the link on
  the employer's own surface, run the applied/ghost/scam check, then build
  `applications/<slug>-YYYY-MM-DD/` (resume PDF, jd.md, apply-notes.md, plus any
  free-text answer the form requires). Mark it `READY` in this run's brief table so
  the button disappears. If the lead fails a check, do not build; say why in the
  brief in one line. Freshness does not block a requested build: he chose it.
- **Save every surfaced lead's JD (2026-11-19).** The dashboard's expanded
  card shows the job description FIRST and the sweep's analysis under it. So for
  every lead that lands in a brief table, save the posting body verbatim (pulled
  from the employer API you already hit for liveness) to
  `jds/<employer>-<role>-<YYYY-MM-DD>.md` with a short header (capture date, source
  URL, employer posting date), and put that path in the row's Materials cell:
  `NOT BUILT · JD saved: \`jds/<file>.md\``. A built folder's own `jd.md` is found
  automatically from the `applications/<folder>/` path. A `BUILD MATERIALS` line may
  carry `USER SAYS: ...`: follow that note when building.
- If it reports `queue empty`, say nothing about it in the brief. Silence is the
  normal case.

## STEP 1 — Pick up where nightly left off

Read `<workspace>/brief-YYYY-MM-DD-1am.md` (older installs: `nightly-leads-YYYY-MM-DD.md`) and the day's `<workspace>/applications/` folders. Note the board-of-origin recorded in each `apply-notes.md`.

## STEP 2 — Link verification (this skill's primary job)

For each lead from the nightly sweep, open the apply link in a browser (navigate only — no clicks, no form fills). Read the page. Three outcomes:

- **(a) Page loads to the right role with an active Apply button** → mark `VERIFIED` in `apply-notes.md`.
- **(b) Page is 404, "no longer accepting applications," or wrong role** → search alternate ATSs (Ashby ↔ Lever ↔ Greenhouse ↔ Workday), check `{company}.com/careers`. If a working link is found, update `apply-notes.md`. If nothing works, leave the lead in the brief with the note: `Apply link broken — try Google '{company} {role title}' or {company}.com/careers`. Never silently delete a lead. Append to `boards.md` event log: `GHOST BURN -5 to <board-of-origin>` — a board that produced a dead lead pays the price.
- **(c) JS-rendered portal that won't load cleanly via headless browse** → mark `UNVERIFIED`, hand the user the company careers URL. No karma penalty (not the board's fault that the portal is JS-heavy).

Cap: ~5 browser actions per link. If verification drags beyond that, hand the URL to the user with a note and move on.

## STEP 2.5 — Email tracking (only if an email connector is available)

If the environment has a connected email tool (e.g. Gmail), use it to catch application confirmations and rejections the user hasn't manually reported yet:

1. Search recent mail (last 24-48h covers a daily cadence) with a rotating keyword set — don't rely on a single term. Working starting set: `appl` (catches application/applying/applied), `reject`, `regret`, `unfortunately`, `interview`, `next steps`, `screener`, `take-home`, `moving forward with other candidates`. Widen this over time if the user reports a status update that the current keywords would have missed — log the miss and the fix in `pattern-signals.md` so the keyword set actually improves.
2. Cross-reference hits against `applied.md`. A confirmation email for a company/role not already logged is a new entry — backfill it with the real applied date from the email, not today's date. A rejection or interview-invite email for an existing PENDING entry updates that entry's status directly (REJECTED / SCREENER) rather than waiting on any time-based auto-ghost rule.
3. This step is READ-ONLY. Never reply, send, forward, or take any action on the inbox beyond searching and reading. If an email is ambiguous (might be a rejection, reads oddly, could be a scam), surface it in the brief instead of guessing at the status.
4. If no email connector is available, skip this step silently — it is not a failure, just an unavailable capability.

## STEP 3 — Gap fill if nightly was thin

If the nightly sweep produced fewer than 3 leads, run targeted supplemental searches to fill the gap. Different angles than nightly used — try Handshake-style entry-level boards, role-specific job boards (e.g. `gameindustryjobs.com` for a games-focused user), apprenticeship aggregators if the user is early-career.

Per-lead `applied.md` + `ghost.md` check before writing anything up.

## STEP 4 — Output (read carefully — past sweeps have failed here)

Surface the nightly sweep's lead descriptions VERBATIM. Do not rewrite them. Do not strip signal-rich paragraphs into bare tables. The nightly sweep's analysis IS the value — preserve it.

Format:

- A summary table at the top is fine as a header (company, role, comp, location, apply link, verified status).
- Each lead's full paragraph from nightly must follow it, unchanged or only lightly edited.

Per-lead `applied.md` check: if a company appears in `applied.md`, remove it from the brief entirely.

## STEP 5 — Append to logs

- New entries to `posting-freshness.md` and `skills-to-learn.md`.
- New permanent kills to `ghost.md`.
- GHOST BURN events from STEP 2 (full -5 only for curated boards; INFRASTRUCTURE boards like Lever/Greenhouse/Ashby/Workday are capped at -2 for fast-closes and floored at 0) to the `boards.md` event log. This is the only event `morning-brief` logs to boards.md — `nightly` handles USABLE LEAD / TOP RANKING / DRY SEARCH / NEW BOARD INDEXED, and the chat handler logs APPLIED / USER GHOST when the user reports them. See the karma taxonomy table in `nightly/SKILL.md` STEP 8 for the complete picture.

## STEP 6 — Deliver the brief

Write the final brief to `<workspace>/brief-YYYY-MM-DD-6am.md`. That exact pattern (`brief-` or `email-check-`, the date, then the run tag) is what `build_site.py` ingests; a file named `morning-brief-*.md` never reaches the dashboard. Structure:

**1. Date header.**

**2. Standings.** Read `<workspace>/applied.md`. Count total entries and pending entries (status `pending`, `screen scheduled`, or `interviewing` — anything not `rejected` / `ghosted` / `offer`). Lead with a one-line tally:

- "First brief — let's start with something to apply to today" (when applied count is 0)
- "Applied to N roles, M still pending — keep going" (when M < 6)
- "Applied to N roles, M pending. M+ pending without a callback yet — see the study nudge below" (when M >= 6 with no recent screen-scheduled / interviewing status)

Tone: encouraging without being saccharine. One sentence, not a paragraph.

**3. Dry-streak study nudge (only if pending count >= 6 with no recent forward motion).** Read the top entries from `<workspace>/skills-to-learn.md` — only skills at count >= 3 OR with explicit user interest from `profile.md`'s "Learning interest" section. Surface ONE specific study path with a SPECIFIC resource matching the user's stated learning interest:

- LeetCode interest → name a topic (e.g., "Dynamic Programming Easy + Medium, 5 problems") and a target rate
- CodePath interest → mention the next cohort start date if known, link to enroll
- New language interest → Advent of Code in that language for the past year (link the year)
- Linux / systems interest → OverTheWire Bandit (link), or "set up a Linux VM and live in it for a week"
- Project-based interest → propose a concrete project from the gaps in `skills-to-learn.md` "Study session / project ideas" section, with a 3-step expansion path (each step ~3-6 hours)

One short paragraph, not a lecture. End with: "Take this in a separate Claude chat or external service so this brief stays focused on applications."

**4. Counts.** Verified leads / unverified leads / killed-since-nightly leads.

**5. Top-lead pointer.** Path to `<workspace>/applications/<slug>-YYYY-MM-DD/` where `apply-notes.md`, `apply-notes.md`, `outreach-draft.md`, and the resume PDF are waiting (no cover letter is generated; apply-notes carries an outline if the role needs one). If an email outreach draft was staged in the user's email account (per `nightly` STEP 7), say so explicitly and point to it — "a draft is sitting in your email drafts folder, ready to review and send." Note any FLEX skills the user should brush up on if a callback lands.

**5.5. Email tracking summary (if STEP 2.5 ran).** One or two lines: any new applied.md entries backfilled from confirmation emails, any statuses updated from rejection/interview emails, and any ambiguous emails that need the user's own read.

**6. TODOs from nightly.** Missing profile fields, broken renders, anything that needs the user's attention before they can ship.

**7. Lead summary table.** One row per lead — company, role, comp, location, apply link, verified status. Use this header exactly, because the dashboard binds columns by header name:

`| # | Lead | Comp | Location | Apply link | Age | Verified | Materials |`

Put employer AND role in the single `Lead` cell ("Acme - Software Engineer, Platform"). Do not split them into `Employer` and `Role` columns (the parser drops `Role`), and do not use `Item` without a leading `#` column. Every row carries a full `https://` apply link (employer ATS first, careers URL if none). Put this table under a heading that reads exactly `## Links and materials status`, with the table starting on the very next non-blank line: any prose line between the heading and the table ends the parser's table mode and every lead is silently dropped (this happened on the first 6am run that followed this rule). Prose goes after the table. A row containing the word KILLED is screened out of the dashboard by design, so killed items belong in the kill list below, not in this table.

**8. Lead writeups.** Each lead's full paragraph from `nightly` (verbatim per STEP 4 above). Do not condense. The paragraph IS the value.

**9. Footer.** Closing line pointing the user to the dashboard: "Today's leads are on the dashboard's Today tab (http://127.0.0.1:8787, or double-click `start-dashboard.bat`). Tick what you apply to there; past briefs live under the Briefs tab." The push notification ends with the same pointer.

The brief is what the user wakes up to. It is the user-facing artifact for the day. Clean prose, signal-rich paragraphs, honest about confidence, occasionally encouraging but never saccharine.
---
## Direction update (2026-08)

- **Cover letters: DROPPED as an auto-generated deliverable.** Most roles do not require one. When a role requires a cover letter, provide ONLY a short structural outline plus one or two lines of angle/inspiration; the user writes it in their own voice. Do not generate full cover letters.
- **Discovery runs every channel; ranked queries are where discretion goes.** Native job alerts (Greenhouse/MyGreenhouse, EarnBetter, Handshake, LinkedIn) ingested via the daily email-check task are a proven breadth extender for employers no registry covers. Direct ATS polling of registered target companies (Greenhouse boards-api, Lever v0 postings, Ashby) is reliable, real-time and zero-token — treat it as a liveness and verification instrument. **Web search is NOT a supplement:** it is the only layer that reaches companies not yet in any registry or digest, which is every new employer by definition, and the "poller-primary, search-supplement" framing is retired. Run all three; spend ranking effort on the query ledger, not on the boards. See tools/board_poller and the subagent batch protocol in `nightly/SKILL.md` STEP 1.
- **Karma: keep the guardrails, retire board-ranking-by-search.** Keep applied/ghost kill-checks, the stale-mirror denylist, and the ethics/experience/location/freshness filters. Stop gating discovery on noisy per-sweep board karma; weight sources by whether they actually produce applied-to leads.
- **Learning as SMART goals in the brief.** Instead of a separate skills-to-learn file the user ignores, surface ONE SMART learning goal per brief driven by AGGREGATE skill demand across recent postings (the skills that recur most, plus high-value ones like Unreal/C++/C#/Kubernetes) rather than pinned to a single lead. Time-box it (~6h) and make it Specific/Measurable/Achievable/Relevant/Time-bound.
---
## 6am discovery — verify nightly's leads, then run this run's query block (load split with 1am)
The nightly sweep is discovery-heavy; the morning sweep is verification-heavy. Both runs carry real query load — see **THE SUBAGENT BATCH PROTOCOL** in `nightly/SKILL.md` STEP 1, which governs both. Target 20-25 queries here, 40-50 across the pair, and report the real number.

1. `poll_boards.py --run` (real-time diff since 1am). If dry (0/0), `poll_boards.py --standing` → `standing-postings.md` (all open registered-board leads minus applied/ghost). The poller is layer A — registered boards only.
2. Run this run's share of the query ledger **in subagent batches** (5-8 queries per subagent, `numResults: 5`), led by LOCATION-FIRST queries for anything posted in the last ~12-24h ("junior/entry SWE {metro} posted today", plus the user's other target role-types). This is the layer that catches fresh roles at unregistered companies (a same-day Capgemini-type junior role) — do NOT skip it just because the poller ran. `--add` any good new company.
   - Subagents return survivors only, with verbatim experience requirements, employer ATS links, dated provenance, and **which query found each lead**. They do not rank and do not write files.
   - Their returns have not been checked against `applied.md` / `ghost.md` — run the kill check yourself before anything reaches the brief.
   - If query volume falls short, name the resource that actually ran out (context window, rate limit, or token budget — they are different problems) rather than reporting a generic capacity limit.
3. Merge with nightly's leads, dedupe, freshness-sort (hours-old first), then per-lead applied/ghost kill-check + scam-screen + ethics + rank.


## STEP 99 — Publish to the dashboard (MANDATORY, LAST STEP, AFTER THE BRIEF IS WRITTEN)

```bash
python3 tools/brief_site/build_site.py
python3 tools/brief_site/build_events.py
```

`build_site.py` feeds Today/Leads/Briefs; `build_events.py` feeds the calendar from `events.md`. Run both. Any dated item the brief tells the user about (an info session, a deadline, a booked screen) must also be appended to `events.md` under a `## YYYY-MM-DD` heading and a `### One-liners` subheading, as `- Title | Thu Nov 19, 3-4 PM | where | cost | NEW - description`, or it will be in the brief text but missing from the calendar.

Re-parses `brief-*.md`, `applied.md` and `ghost.md` into the JSON the dashboard
serves, so tonight's leads appear on the user's Today tab with working apply links
and checkboxes. The brief file must already be written -- this step reads it.

Read-only against the workspace; it cannot damage a markdown file. It refuses to
write when it finds no briefs, so a wrong `--root` errors instead of blanking data.

If the user keeps the dashboard open, it picks the new data up on refresh.

**Verify the publish, do not assume it.** After the build, confirm that today's
`brief-YYYY-MM-DD-6am.md` was parsed and that its leads appear in the generated data
(grep the built JSON for one of today's apply URLs). If the build errors, refuses to
write, or today's leads are missing, fix the brief's table header and rebuild once; if it
still fails, the push notification says "brief written, dashboard NOT updated" with the
reason, so the user does not open a stale Today tab.

