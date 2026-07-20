---
name: nightly
description: Overnight job-research sweep. Searches the user's top-karma boards, scam-screens results, ranks leads, and builds tailored materials for the best one. Runs unattended via scheduled task at 1am local time on weekdays. Not normally invoked manually.
---

# Nightly research sweep

Heavy research pass. Read in this order before any search:

1. `<workspace>/CLAUDE.md` — standing rules (materials standards, flex strategy, outreach play, scam patterns) and the user's project memory
2. `<workspace>/profile.md` — identity, contact, work authorization, targeting, learning interest
3. `<workspace>/profile-resume.md` — what's on the user's resume
4. `<workspace>/profile-projects.md` — interview-worthy projects in the user's own words (primary input for cover letters)
5. `<workspace>/skills-inventory.md` — what the user's code actually shows they can do
6. `<workspace>/applied.md` — kill list. Companies here do not get re-suggested. EXCEPTION: entries older than 12 months from their applied date are no longer hard kills — job postings turn over annually, and a role applied to last cycle may be worth re-applying for this cycle. Surface these leads in the brief with a note: "applied <date> last cycle — may be worth re-applying."
7. `<workspace>/ghost.md` — RED = permanent skip; YELLOW within 3 months = skip; GREEN = ATS verify before resurfacing. At the start of the sweep, prune YELLOW entries older than 3 months → GREEN.
8. `<workspace>/pattern-signals.md` — the user's engagement signals shape what counts as a good fit.
9. `<workspace>/boards.md` — recompute the karma table from the event log if needed. Identify the TOP 5 boards by karma. Note the domain denylist and the "what counts as a board" rule.

## Operating principles (apply throughout this skill)

- **Search broad, brief focused.** Search across the user's stated role types AND credible adjacencies. The brief highlights leads matching expressed direction but does not limit to them. This is about searching, exploring, and growing — not narrowing into a single track. Senior users with forced specialization or users with explicit "only show me X" preference are the exceptions.
- **Don't kill leads for partial fit.** A JD listing "5+ years" on a junior posting often means "we'll consider strong 1-3 year candidates." Note the gap, mark FLEX skills where bridgeable, surface the lead. Only kill when the missing piece is fundamental (senior staff role for someone with no work experience, specialty stack that takes months).
- **Flex skill strategy (controlled exception to the no-fabricated-experience rule).** For skills the user could credibly study to working knowledge in 6-12 hours, list 1-2 max on the tailored resume to clear keyword filters. Mark FLEX in `apply-notes.md` with a "STUDY BEFORE THE SCREEN" section listing specific resources pulled from `skills-to-learn.md`. Two FLEX max per app — more is fiction.
- **Skills-to-learn is a tally.** Each skill gets a frequency count incremented per occurrence in any JD. Surface as a study suggestion only when count >= 3 OR when the user has explicitly expressed interest in `profile.md`'s "Learning interest" section. One-off skill mentions stay logged but don't bubble up — they're noise until they recur.
- **Salary ≠ winnability. Calibrate both before ranking.** High comp often signals high selectivity — ATS keyword filters, school pedigree screens, larger applicant pools. Use this working model when ranking leads:
  - **$80-120K at a small startup (≤30 people, new-grad-ok, founder-accessible)** → realistic. Target band for most early-career users.
  - **$120-160K at a named Series B+ company (portal-based hiring)** → context-dependent. Surface in top-3 only if there's a concrete angle: a specific portfolio match in the JD, a named person to cold-reach, or a relevant open-source contribution.
  - **$140K+ at an established brand with an ATS portal** → assume brutal filtering. Top-3 only with an ATS bypass (referral, direct recruiter contact, or a JD line the user's shipped work directly answers). Otherwise, log as "stretch" rather than padding the brief with low-probability applies.
  A high-comp lead without a concrete winnability angle is NOT a top-ranked lead. Honest odds read is more valuable to the user than an impressive-looking salary figure in the summary table.

## STEP 0 — Confirm read

You should have already read all 9 files listed above. If any are missing (e.g., `CLAUDE.md` doesn't exist yet), the user has not completed setup — abort the sweep and tell them to run `setup` first.

## STEP 1 — Search

Run EXACTLY 5 parallel web searches (Exa or equivalent), one per top-5 board. Each query natural-language and source-biased. Examples (substitute the actual top-5 boards in `boards.md`):

- YC: "junior or new grad software engineer postings on Y Combinator companies job board"
- Ashby: "new grad software engineer roles on jobs.ashbyhq.com"
- Wellfound: "junior software engineer startup roles on wellfound.com"
- Greenhouse direct: "junior software engineer entry level openings on boards.greenhouse.io"
- Lever direct: "entry level software engineer roles on jobs.lever.co"

`numResults`: 10 per query.

If the karma table is fresh (less than 7 days of sweep history) and most boards sit at karma 0, treat the top-5 as a starting heuristic only — early sweeps are calibration runs, not high-confidence runs. Surface that in the brief if results are thin.

## STEP 2 — Post-filter

Drop any URL whose domain matches the denylist in `boards.md` before scoring.

## STEP 3 — Per-lead kill check

Before writing up any lead, check the company name against `applied.md` AND `ghost.md`. Per-lead, not just at sweep start. A company appearing in either is killed unless the lead is clearly a different role at a different team and enough time has passed to make re-engagement appropriate (note the reasoning in `apply-notes.md` if so).

## STEP 4 — Verify lead validity (not link validity yet)

For each surviving candidate:

- Confirm the company + role exist via search results, careers-page references, or ATS metadata.
- Score on JD fit (against `profile.md` targeting + `skills-inventory.md`), posting freshness, comp signals, company stage signals.
- Lock the lead based on the lead itself, not the link. Link verification is the `morning-brief` skill's job.

## STEP 5 — Best-guess link with confidence flag

For each lead, ship a best-guess apply link with a confidence flag:

- **HIGH** — link came directly from the company's own careers page or a recent ATS posting (Greenhouse, Lever, Ashby, Workday).
- **MEDIUM** — link came from an aggregator or older ATS posting.
- **LOW** — no clean link found, only a JD reference. Note this clearly so the user knows to expect to hunt for the apply page themselves.

## STEP 6 — Write up each surviving lead

Each lead writeup is a signal-rich paragraph (not a bare table row). Include:

- Posting age + which board surfaced it (track board-of-origin for karma backtrace)
- Company shape: funding stage / team headcount / new-grad-explicit flag if visible
- Named co-founders, hiring managers, or relevant engineers from LinkedIn (only if visible — never invent names)
- JD signals matching the user's profile and skills inventory (which projects, languages, hackathon wins, etc. line up)
- Comp range (or "not listed")
- Location + remote policy
- Honest odds read for the user's stage
- Apply link + confidence flag

If zero leads survive: that is a valid output. Write a brief that says so and explains why (boards quiet, kill list hit hard, low-confidence-only results). Do not pad.

## STEP 7 — Materials for the best lead

Build full materials for the top-ranked lead. Save to `<workspace>/applications/<slug>-YYYY-MM-DD/`:

- `apply-notes.md` — DIRECT APPLY LINK at top, what they want (quoting JD verbatim), why this fits the user, scam verdict, manual steps if any, FLEX skill flags.
- `cover-letter.md` — user's voice, ~250 words, no AI-isms, reads `profile.md` for name and contact info.
- `outreach-draft.md` — short LinkedIn DM or cold email targeting a real named person at the company (only if a real person was identified — do not invent recipients).
- `resume.tex` (or `resume.md`) — tailored from `<workspace>/profile-resume.md` and the template at `assets/resume-template/`. Render to PDF.

**Resume rendering — adaptive renderer.** Detect what is installed locally:

1. If `pdflatex` is on the path, render via the LaTeX template.
2. Else if `typst` is on the path, render via the Typst template.
3. Else: emit a clean markdown resume and tell the user in `apply-notes.md` that PDF rendering needs `pdflatex` (recommended) or `typst` installed locally. Do not block the brief on a missing renderer.

**Resume verification (mandatory after any PDF render):**

1. Page count is exactly 1.
2. No text clipped at any margin (header right edge especially — `github.com/<handle>` must not truncate).
3. No paragraph orphaned to a second page.

If any check fails, edit and re-render. Never deliver a clipped resume.

**Personal info:** every cover letter and resume MUST read `profile.md` and use the user's actual name, email, phone, etc. Never emit `[user]`, `[your name]`, `[email]` placeholders. If a needed profile field is missing, leave a clearly-marked TODO in the document and flag it in the morning brief.

## STEP 8 — Karma updates

Append events to the `boards.md` event log. The full event taxonomy:

| Event | Weight | Trigger |
|---|---|---|
| `USABLE LEAD` | +1 | Any lead that survived all kill checks and made it into the brief |
| `TOP RANKING` | +1 (additive) | Lead also landed in top 3 of the brief |
| `NEW BOARD INDEXED` | +1 | A new board candidate was validated and added (must serve listings from 3+ distinct companies — a single company's portal does NOT count) |
| `DRY SEARCH` | -1 | A scheduled board search returned zero usable results |
| `GHOST BURN` | -5 | Logged by `morning-brief` when an apply link from a board is 404 / dead / wrong role — do NOT log here |
| `APPLIED` | +10 | Logged by chat handler when the user confirms they applied — do NOT log here |
| `USER GHOST` | -5 | Logged by chat handler when the user manually flags a lead as junk — do NOT log here |

What `nightly` logs this run:

- For each lead in tonight's brief: `USABLE LEAD +1 to <board>`
- For each top-3 lead (additive on top of USABLE LEAD): `TOP RANKING +1 to <board>`
- For each of the 5 board searches that returned zero usable results: `DRY SEARCH -1 to <board>`
- If a NEW board candidate emerged during search and validates (3+ companies): `NEW BOARD INDEXED +1 to <new board>` and add it to the karma table at karma 1.

Do NOT log `APPLIED`, `USER GHOST`, or `GHOST BURN` here — those events belong to other code paths (chat handler and `morning-brief` respectively). Logging them twice corrupts the karma signal.

Top-3 leads earn +2 (USABLE LEAD + TOP RANKING). Applied is the heaviest positive (+10) by design — it means the user looked at the lead and chose to act on it, which is the strongest possible signal that the board is producing real value. The asymmetry between APPLIED (+10) and GHOST BURN (-5) means a single applied counterbalances two ghosts, which is the right shape for a noisy data source.

## STEP 9 — Append to running logs

- `posting-freshness.md` — log each lead's posted-X-ago timestamp at sweep time.
- `skills-to-learn.md` — for any JD requirement the user does not have, log it under HARD or NICE-TO-HAVE.
- `ghost.md` — append any new permanent kills surfaced (TRAP outfits, confirmed scams, ethics-filter matches).

Do NOT append to `applied.md` — that is the user's call.

## STEP 10 — Study-idea notes

The frequency tally in `skills-to-learn.md` does the threshold work — surface as a study suggestion only when count >= 3 cumulatively across all sweeps (or when the user has expressed interest in `profile.md`). Do NOT use a per-night threshold; that creates noise and surfaces obscure one-off skills as if they were trends.

For any skill that has crossed the cumulative threshold and does not yet have a study-session entry in `skills-to-learn.md`'s "Study session / project ideas" section, append one now. Be specific: "Build a small REST API with X to back up the framework claim" rather than "learn X." Match the resource recommendation to the user's stated learning interest from `profile.md` (LeetCode user → suggest LeetCode topic; CodePath user → suggest CodePath cohort; Advent of Code user → suggest AoC year-and-language; project-based user → suggest a build-and-extend project with a 3-step expansion path).

## STEP 11 — Hand-off

Save the night's lead writeups to `<workspace>/nightly-leads-YYYY-MM-DD.md`. The `morning-brief` skill reads this file in a few hours, verifies the links, and produces the brief the user actually wakes up to.
