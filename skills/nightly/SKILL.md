---
name: nightly
description: Overnight job-research sweep. Polls the user's registered ATS boards directly (board_poller) as the primary source, supplements with web search for new companies, scam-screens, ranks, and builds tailored materials for the best lead. Runs unattended via scheduled task at 1am local time on weekdays. Not normally invoked manually.
---

# Nightly research sweep

Heavy research pass. Read in this order before any search:

1. `<workspace>/CLAUDE.md` — standing rules (materials standards, flex strategy, outreach play, scam patterns) and the user's project memory
2. `<workspace>/profile.md` — identity, contact, work authorization, targeting, learning interest
3. `<workspace>/profile-resume.md` — what's on the user's resume
4. `<workspace>/profile-projects.md` — interview-worthy projects in the user's own words (primary input for materials)
5. `<workspace>/skills-inventory.md` — what the user's code actually shows they can do
6. `<workspace>/applied.md` — kill list. Companies here do not get re-suggested. EXCEPTION: entries older than 12 months from their applied date are no longer hard kills — job postings turn over annually, and a role applied to last cycle may be worth re-applying for this cycle. Surface these leads in the brief with a note: "applied <date> last cycle — may be worth re-applying."
7. `<workspace>/ghost.md` — RED = permanent skip; YELLOW within 3 months = skip; GREEN = ATS verify before resurfacing. At the start of the sweep, prune YELLOW entries older than 3 months → GREEN.
8. `<workspace>/pattern-signals.md` — the user's engagement signals shape what counts as a good fit.
9. `<workspace>/boards.md` — KARMA + TIERS. Karma scores sources (APPLIED +10, INTERVIEW +15, USABLE +2, TOP RANKING +1, GHOST BURN -3 curated / -1 infra, BLOCKED-HIT -5, DRY -1 only if a peer produced that sweep). Karma is CLAMPED to -5..+30 and decays 1/week toward 0, so nothing runs away or stays buried. Tiers are the guardrail: CORE (+8up, every sweep, floor +5 — never demoted by dry nights alone), ROTATION (0..+7, 2-3 round-robin per sweep), DORMANT (<0, parked NOT dead — retry >=1 per sweep, each monthly; one usable lead returns it to ROTATION), BLOCKED (permanent, documented relisters only). A user opinion about a category is a NOTE on the source, never a karma hit.

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
- **Draft, never send.** Any outreach email created through a connected email tool is a DRAFT, full stop — even if the connector exposes a send capability, do not use it. The user reviews and sends every outreach message themselves. If a recruiter or contact replies to a thread the user sent, do not draft or send a follow-up reply autonomously under any circumstance — flag the reply in the next brief and let the user take it from there. This is a hard boundary, not a judgment call.

## STEP 0 — Confirm read

You should have already read all 9 files listed above. If any are missing (e.g., `CLAUDE.md` doesn't exist yet), the user has not completed setup — abort the sweep and tell them to run `setup` first.

## STEP 1 — Search

Run all three layers below IN PARALLEL. They catch different things — breadth is the point, and no single layer is "primary." A dry result from one is normal; the others cover it.

**A — Poller (registered boards, real-time, zero-token).** `poll_boards.py --run`, read new-postings.md. If it's dry (0 junior AND 0 watch — common), `poll_boards.py --standing`, read standing-postings.md (all open registered-board leads minus applied/ghost). This is structured inventory from the boards already in the registry.

**B — Broad web search (Exa, 5-8 parallel, numResults 10).** This is the original engine and it finds roles at companies NOT in the registry. Two flavors, run both:
- *Source-biased* — one per top board in `boards.md`: e.g. "new grad software engineer roles on jobs.ashbyhq.com", "junior software engineer entry level on boards.greenhouse.io", "entry level SWE on jobs.lever.co", "junior/new grad SWE on Y Combinator jobs".
- *Location-first* — the highest-value queries; they catch fresh roles the registry can't see (this is how a 2-hour-old Capgemini junior role surfaces): "junior OR entry-level software engineer jobs {metro/state} posted this week", plus one per target role-type in `profile.md` (IT / QA / analyst / solutions engineer / new grad). Include a "posted this week / past 24 hours" freshness cue.

`query-terms.md` (if present) holds reusable location + NEGATIVE clauses — use them, but a plain location-first query stands on its own. Do NOT gate the search behind that file's machinery.

**C — Feed the registry.** Any good NEW company found in B: `poll_boards.py --add "<ATS careers URL>"` so it self-polls in layer A next time. (SuccessFactors / iCIMS / Taleo boards can't be polled — just apply directly and note it.)

Merge all three, dedupe, freshness-sort (hours-old first). If the karma table is fresh (<7 days history), treat board ranking as a loose heuristic only.

**Load split (1am vs 6am):** 1am runs the full A+B+C (heavy). 6am re-runs the poller + a SHORT location-first freshness pass (2-3 queries) to catch anything posted overnight, then verifies + delivers. Tokens are ample across two runs — favor breadth over cutting searches.

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
- NO cover letter is generated. If the role requires one, put a short structural outline plus 1-2 lines of angle into `apply-notes.md`; the user writes it in their own voice.
- `outreach-draft.md` — short LinkedIn DM or cold email targeting a real named person at the company (only if a real person was identified — do not invent recipients).

**Email outreach draft (if an email tool is connected and a real address was found).** If the environment has an email-sending connector available (e.g. Gmail) and the outreach target is a cold email (not a LinkedIn DM) with a real, verifiable email address, stage the same content as an actual draft in the user's email account using the connector's draft-creation tool — never a send tool, even if one is technically available. This is in addition to `outreach-draft.md`, not a replacement for it. Keep the email brief and respectful: 3-5 sentences, one clear reason it's relevant to this specific person, no attachments unless the connector supports them and the user's profile explicitly authorized it. Note the draft's ID or location in `apply-notes.md` so `morning-brief` can point the user to it. Cap at ONE outreach draft per sweep — this is a precision play, not a volume play.
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

**Personal info:** every resume and outreach draft MUST read `profile.md` and use the user's actual name, email, phone, etc. Never emit `[user]`, `[your name]`, `[email]` placeholders. If a needed profile field is missing, leave a clearly-marked TODO in the document and flag it in the morning brief.

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
---
## Direction update (2026-08)

- **Cover letters: DROPPED as an auto-generated deliverable.** Most roles do not require one. When a role requires a cover letter, provide ONLY a short structural outline plus one or two lines of angle/inspiration; the user writes it in their own voice. Do not generate full cover letters.
- **Discovery uses ALL channels in parallel — breadth wins.** Three complementary layers, none is "primary" (see STEP 1): (1) native job alerts (Greenhouse/MyGreenhouse, EarnBetter, Handshake, LinkedIn) via the email-check task; (2) direct ATS polling of registered target companies (board_poller — reliable, real-time, zero-token); (3) broad + location-first web search (Exa) which is the ONLY layer that finds fresh roles at companies not yet registered (e.g. a same-day Capgemini junior role). A quiet result from one layer does not mean the market is quiet — run the others. Do not demote web search; the 2026-08 "poller-primary, Exa-supplement" framing starved the pipeline for ~2 weeks and is retired.
- **Karma: keep the guardrails, retire board-ranking-by-search.** Keep applied/ghost kill-checks, the stale-mirror denylist, and the ethics/experience/location/freshness filters. Stop gating discovery on noisy per-sweep board karma; weight sources by whether they actually produce applied-to leads.
- **Learning as SMART goals in the brief.** Instead of a separate skills-to-learn file the user ignores, surface ONE SMART learning goal per brief driven by AGGREGATE skill demand across recent postings (the skills that recur most, plus high-value ones like Unreal/C++/C#/Kubernetes) rather than pinned to a single lead. Time-box it (~6h) and make it Specific/Measurable/Achievable/Relevant/Time-bound.
---
## board_poller — how to run layer A (see STEP 1 for how it fits with web search)
The poller is ONE of the three search layers (STEP 1, layer A), not a replacement for web search. It polls registered ATS boards directly (Greenhouse/Lever/Ashby/Workday/SmartRecruiters/Workable, plus JazzHR/custom via HTML fallback), applies seniority + location + role filters in Python, tags YoE (`[needs Nyr]`), and is zero-token.

- `poll_boards.py --run` → `new-postings.md`: postings NEW since the last run (real-time diff).
- If that's dry (0 junior AND 0 watch — common on a slow registry), `poll_boards.py --standing` → `standing-postings.md`: EVERY currently-open registered-board junior/watch lead, minus applied.md/ghost.md (auto-excluded by company name). A dry `--run` is normal; `--standing` is its companion, not a failure signal.
- `poll_boards.py --add "<careers URL>"` registers a new company found via web search so it self-polls next time.

Layer A gives structured, real-time coverage of the boards you already track. It does NOT see companies outside the registry — that's what the broad + location-first web searches in STEP 1 layer B are for. Run both; freshness-sort together.
