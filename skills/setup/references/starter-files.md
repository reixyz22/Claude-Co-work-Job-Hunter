# Starter file templates

When the `setup` skill writes the workspace state files, use these contents verbatim (substituting user inputs where noted).

The `CLAUDE.md` workspace file is NOT in this document — it gets copied from `references/claude-md-template.md` during STEP 11.

---

## boards.md

```markdown
# Boards — karma table + event log

Every job board this system searches has a karma score. Karma starts at 0 for every newly-seeded board and updates after every event. Sweeps prioritize search budget on the top-karma boards.

## Event taxonomy

| Event | Weight | Triggered by |
|---|---|---|
| `USABLE LEAD` | +1 | Any lead that survived all kill checks and made it into the brief (logged by `nightly`) |
| `TOP RANKING` | +1 (additive on USABLE LEAD) | Lead also landed in top 3 of the brief (logged by `nightly`) |
| `NEW BOARD INDEXED` | +1 | A new board candidate was validated and added (logged by `nightly`) |
| `SEEDED at setup` | +0 | A board was seeded during setup — neutral starting karma (logged by `setup`) |
| `DRY SEARCH` | -1 | A scheduled board search returned zero usable results (logged by `nightly`) |
| `GHOST BURN` | -5 | An apply link from this board turned out to be 404, wrong role, or otherwise dead (logged by `morning-brief` after link verification) |
| `APPLIED` | +10 | The user told Claude in chat that they applied to a lead from this board (logged by chat handler) |
| `USER GHOST` | -5 | The user told Claude in chat to ghost a lead from this board (logged by chat handler) |

Top-3 leads earn +2 (USABLE LEAD + TOP RANKING). APPLIED is the heaviest positive (+10) — the user looked at the lead and chose to act, the strongest signal. The asymmetry between APPLIED (+10) and GHOST BURN / USER GHOST (-5) means a single applied counterbalances two ghosts, which is the right shape for noisy data.

## Karma table

| Board | Karma | Last sweep | Notes |
|---|---|---|---|
| (populated by setup STEP 9 — universal + geography-specific + role-specific boards seeded at karma 0) | | | |

## Domain denylist

These domains are noise across most users — listings here have a poor track record of being live, accurate, or applicable. Skip results from these domains during search ranking.

- builtin.com
- indeed.com
- dice.com
- ziprecruiter.com
- glassdoor.com
- linkedin.com/jobs (use as discovery only — ALWAYS verify the role on the company's own ATS)

If a seeded board appears repeatedly as a source of GHOST BURN events with no offsetting TOP RANKINGs / APPLIEDs after ~10 sweeps, add its domain here.

## What counts as a board

A "board" is a site that serves listings from 3+ distinct companies. A single company's careers portal (e.g. apple.jobs, careers.google.com) is a *portal*, not a board, and does not get karma'd.

## Event log

Append-only. Do not edit history. Format: `YYYY-MM-DD HH:MM | <event> <weight> to <board> | <optional context>`

(no events yet)
```

---

## ghost.md

```markdown
# Ghost — dead, filtered, and disqualified leads

Three tiers:

- **RED** — permanent skip. Scams, ethically blacklisted companies, training-repayment-agreement (TRAP) outfits. Never resurfaces.
- **YELLOW** — dead listing at a legit company. Filled, expired, stale. Skip for 3 months from the KILLED date.
- **GREEN** — was YELLOW, 3+ months passed. Worth re-checking the company's ATS for a fresh req. If verified live with a new req ID, remove from ghost. If still dead, bump back to YELLOW with new date.

At the start of every sweep, prune YELLOW entries older than 3 months → promote to GREEN.

---

## RED — permanent skip

(populated from setup ethics-filter answers — replace examples below with the user's actual seeds)

- Example: gambling industry — KILLED YYYY-MM-DD by user during setup
- Example: AI weapons / military contracting — KILLED YYYY-MM-DD by user during setup
- Example: payday lending — KILLED YYYY-MM-DD by user during setup
- Example: training-repayment-agreement (TRAP) employers — KILLED YYYY-MM-DD by setup default

## YELLOW — recently dead

(no entries yet)

## GREEN — cooled off, worth re-checking

(no entries yet)
```

---

## applied.md

```markdown
# Applied — full history (numbered)

Every role the user has applied to. Sweeps READ this file at the start of every run as a kill list — a company on this list is a strong signal not to re-suggest the same role.

The morning brief reads this file's count to give the user a daily tally ("Applied to 12 roles, 7 still pending — keep going"). After 6+ pending applications without any callbacks, the brief surfaces a study-session nudge using `skills-to-learn.md`.

Numbering is explicit and sequential. Never delete entries — this doubles as the user's personal application tracker.

**12-month aging.** Entries older than 12 months are no longer treated as hard kills. Job postings turn over annually; a role applied to in 2025 may be worth re-applying for in 2026. The nightly sweep flags these as "applied last cycle — may be worth re-applying" rather than skipping them silently.

Format: `N. <Company> | <Role title> | Applied YYYY-MM-DD | <status>`

Status values:
- `pending` — applied, no response yet
- `screen scheduled` — phone screen booked
- `interviewing` — in pipeline
- `offer` — got an offer
- `rejected` — explicit rejection
- `ghosted` — recruiter went silent post-apply (NOT the same as a `ghost.md` entry — this is a status, that is a kill)

(no entries yet)
```

---

## pattern-signals.md

```markdown
# Pattern signals — what the user engages with vs. ignores

Updated by the user (and by the morning-brief skill when patterns become obvious from applied.md / ghost.md activity). Read at the start of every sweep before writing any leads.

## Engages with

(traits of leads the user actually applied to or asked to dig into — e.g. "junior C++ at game studios," "remote-friendly Python at Series B startups")

(no entries yet)

## Ignores / rejects

(traits of leads the user consistently kills or skips — e.g. "consulting firms," "anything requiring 5+ years experience")

(no entries yet)

## Notes

(freeform observations, e.g. "user prefers smaller teams," "user only opens links to Greenhouse / Ashby postings")

(no entries yet)
```

---

## posting-freshness.md

```markdown
# Posting freshness log

Per-lead "posted X hours/days ago" timestamps captured at sweep time. Used to calibrate the scheduled task times — if most fresh postings appear at 4am UTC, the nightly run should land around then.

Format: `YYYY-MM-DD HH:MM | <board> | <company> | <role> | posted <X> ago at sweep time`

(no entries yet)
```

---

## skills-to-learn.md

```markdown
# Skills to learn — tally + study paths

Frequency-tallied gap log. Each skill increments a count every time it appears in a JD the user can't yet hit. The morning brief surfaces only skills appearing 3+ times OR skills the user has explicitly expressed interest in (set during setup STEP 7, stored in profile.md "Learning interest").

Format per skill:

| Skill | Count | First seen | Last seen | Sample postings |
|---|---|---|---|---|
| (populated as JDs are parsed) | | | | |

## Hard requirements gaps (count >= 3 OR explicit interest)

(skills appearing in JDs as required, surfaced because count crossed threshold or user expressed interest)

(no entries yet)

## Nice-to-have gaps (count >= 3 OR explicit interest)

(skills appearing as preferred or "bonus", surfaced under same conditions)

(no entries yet)

## Logged but below threshold (count < 3, no expressed interest)

(everything else — held until it crosses the threshold or the user expresses interest)

(no entries yet)

## Study session / project ideas

For each surfaced skill, the system suggests concrete study paths. Categories of recommendations:

- **Structured curriculum:** CodePath (free, cohort-based — Tech Interview Prep, Web Dev, Cybersecurity tracks), Full Stack Open (free), Coursera tracks specific to the skill
- **Practice:** LeetCode (algorithms), Advent of Code (small puzzles, great for picking up a new language), Exercism, Codewars
- **Project ideas with expansion paths:** specific build-this-then-extend-it projects with each extension scoped to ~3-6 hours
- **Language pickups:** for each language, the standard "1-week-to-working-knowledge" path (book + project + community)
- **Linux / systems:** OverTheWire (Bandit, Narnia), Crafting Interpreters book, set up a Linux VM and live in it for a week

When a study path is suggested in the morning brief, include the SPECIFIC resource (URL or book name) and a one-line "why this for you" note linking back to the JDs that surfaced the gap. Encourage the user to take learning sessions in a separate Claude chat or external service so the daily-job-hunter loop stays focused on applications.

(no entries yet)
```

---

## profile.md (written by setup STEPs 2 + 3 + 7)

```markdown
# Profile

## Identity

- Full legal name: <from setup>
- Preferred name: <from setup>
- Email: <from setup>
- Phone: <from setup>
- Location: <from setup — city + state, or city + country if outside US>
- LinkedIn: <from setup>
- GitHub: <from setup>
- Portfolio: <from setup>

## Work authorization

- Status: <citizen / permanent resident / requires visa>
- Sponsorship needed: <yes / no>

## Targeting

- Career stage: <from setup>
- Primary role types: <from setup>
- Geography: <from setup>
- Remote tolerance: <from setup>

## Learning interest

(what the user said in setup STEP 7 — used to force-surface skills-to-learn entries even when count is below threshold)

- <user's stated interest>
```

Every cover-letter and resume-rendering step in the plugin reads this file before writing. Never emit `[name]`, `[user]`, `[email]` placeholders — if a field is blank, ask the user before generating materials.

---

## profile-projects.md (written by setup STEP 6)

```markdown
# Profile — project narratives

The 2-4 projects the user would most want to talk about in interviews. Set during setup STEP 6 by walking the user through each project.

For each project: name, repo link, what it actually does (in the user's words), tech stack, one or two concrete metrics (verified by the user — do not invent), what was hard / what they learned, and a one-line "framing for cover letters" the user has approved.

This file is a primary input for cover letters and resume tailoring. Do not invent project details. Do not inflate metrics. If a project's framing isn't here, it doesn't go in a cover letter — return to the user to capture it first.

## Project 1: <name>

- Repo: <link or "private">
- What it does: <user's own words>
- Tech stack: <list>
- Metrics: <user-verified — e.g. "200 average concurrent viewers across many streams, $2,000+ in donations">
- What was hard: <user's words>
- Framing for cover letters: <one-line, user-approved>

## Project 2: <name>

(same fields)

(repeat for projects 3 and 4)
```
