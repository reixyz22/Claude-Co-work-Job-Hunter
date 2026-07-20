---
name: morning-brief
description: Morning verification + delivery sweep. Verifies the apply links from last night's research, fills gaps, and produces the ranked brief the user reads with coffee. Runs unattended via scheduled task at 6am local time on weekdays. Not normally invoked manually.
---

# Morning brief — verification + delivery

Light second-pass sweep. Read `<workspace>/profile.md` for context.

## STEP 0 — Read before anything

1. `<workspace>/applied.md`
2. `<workspace>/ghost.md`
3. `<workspace>/pattern-signals.md` — read it back to yourself before any output.
4. `<workspace>/boards.md` — note current karma + denylist.

## STEP 1 — Pick up where nightly left off

Read `<workspace>/nightly-leads-YYYY-MM-DD.md` and the day's `<workspace>/applications/` folders. Note the board-of-origin recorded in each `apply-notes.md`.

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
- `GHOST BURN -5 to <board-of-origin>` events from STEP 2 to the `boards.md` event log. This is the only event `morning-brief` logs to boards.md — `nightly` handles USABLE LEAD / TOP RANKING / DRY SEARCH / NEW BOARD INDEXED, and the chat handler logs APPLIED / USER GHOST when the user reports them. See the karma taxonomy table in `nightly/SKILL.md` STEP 8 for the complete picture.

## STEP 6 — Deliver the brief

Write the final brief to `<workspace>/morning-brief-YYYY-MM-DD.md`. Structure:

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

**5. Top-lead pointer.** Path to `<workspace>/applications/<slug>-YYYY-MM-DD/` where `apply-notes.md`, `cover-letter.md`, `outreach-draft.md`, and the resume PDF are waiting. If an email outreach draft was staged in the user's email account (per `nightly` STEP 7), say so explicitly and point to it — "a draft is sitting in your email drafts folder, ready to review and send." Note any FLEX skills the user should brush up on if a callback lands.

**5.5. Email tracking summary (if STEP 2.5 ran).** One or two lines: any new applied.md entries backfilled from confirmation emails, any statuses updated from rejection/interview emails, and any ambiguous emails that need the user's own read.

**6. TODOs from nightly.** Missing profile fields, broken renders, anything that needs the user's attention before they can ship.

**7. Lead summary table.** One row per lead — company, role, comp, location, apply link, verified status.

**8. Lead writeups.** Each lead's full paragraph from `nightly` (verbatim per STEP 4 above). Do not condense. The paragraph IS the value.

**9. Footer.** Closing line pointing the user to past briefs: "Past briefs are saved as `morning-brief-YYYY-MM-DD.md` in your workspace folder — open it in any file browser to revisit prior days." Useful when they miss a day, want to check back on a lead they meant to apply to, or look up something from last week.

The brief is what the user wakes up to. It is the user-facing artifact for the day. Clean prose, signal-rich paragraphs, honest about confidence, occasionally encouraging but never saccharine.
