---
name: setup
description: First-time onboarding wizard for the daily-job-hunter plugin. Use when the user installs the plugin, says "set up daily job hunter," "onboard me to the job hunter," "configure the job hunter," "start the job search system," or runs this for the first time. Walks the user through disclaimers, profile capture, resume import, code-folder skill inventory, project narratives, learning interest, ethics filter seed, board discovery, scheduling, CLAUDE.md installation, and the participation contract.
---

# Setup — first-time onboarding

This is a one-time wizard. Run it when the user first installs the plugin or asks to reconfigure.

The user has just installed an autonomous system that will write drafts on their behalf and run unattended overnight. They need to understand what it does and what it does not do before they trust any output. This skill exists to make that handoff careful.

Total time: about ten minutes if the user has their resume handy.

## STEP 0 — Disclaimers FIRST (do not skip)

Read `references/disclaimers.md` and present its full contents to the user as the very first thing they see. Do not summarize. Do not rephrase. Do not collapse it into bullets. Wait for the user to acknowledge they've read it before continuing. If they want to skip ahead, gently tell them you will not skip this — it is the most important page they will see.

## STEP 1 — Workspace folder

Ask the user where they want the plugin's workspace to live. Default suggestion: a folder named `job-hunter/` somewhere convenient (Documents, home directory, Desktop). The plugin will write all state files there.

Confirm the path. If the folder doesn't exist, create it. If it already has files, ask before writing on top of them.

## STEP 2 — Personal info (mandatory, no placeholders ever)

Use AskUserQuestion (or the elicitation form widget if available) to collect ALL of the following in one pass. Do not skip fields — they prevent `[user]` placeholders from showing up in cover letters later.

- Full legal name (as it should appear on a resume)
- Preferred name (if different — used in cover letter signatures)
- Email
- Phone (with country code)
- Mailing address (street, city, state/province, country, postal code)
- Work authorization (US citizen / permanent resident / requires visa / other — ask the user to specify)
- Sponsorship needed (yes / no)
- LinkedIn URL
- GitHub URL (or other portfolio repo host)
- Personal website / portfolio URL (optional)

Save the answers to `<workspace>/profile.md` in a clean markdown structure. Every other skill in this plugin reads `profile.md` before generating materials. If a field is empty when a cover letter is being written, the writing skill is required to ask the user before emitting a placeholder — never invent values, never leave bracketed `[name]` tokens.

**Privacy option.** If the user prefers to keep some of these fields out of the workspace, that is fine — they can leave any field blank or skip the question entirely. Do not pressure or nag. Warn them: leaving a field blank means cover letters and resume tailorings will have a literal placeholder where that field would have gone (e.g., `<your name>` in the signature), and they will need to fill those in by hand before sending. Do not let them ship a resume that has `<name>` or `<email>` written on it — that makes a worse impression than not applying at all.

## STEP 3 — Experience level + role focus

Ask, in one elicitation form:

- Career stage: student / new grad / 1-3 yrs / 3-7 yrs / 7+ yrs / staff+
- Primary role types they're targeting (free text — encourage specificity, e.g. "junior backend Python," "ML platform mid-level," "C++ games engineer")
- Geography: city/region or remote-only
- Remote tolerance: remote-only / hybrid / onsite OK / open to anything

Append to `profile.md`.

## STEP 4 — Resume import

Ask the user to point at their best current resume. Accept either a PDF or a LaTeX source file (`.tex`). Read it. Extract:

- Education (school, degree, GPA if listed, graduation year)
- Work experience (title, company, dates, bullets)
- Projects (name, tech stack, brief description, link if any)
- Skills inventory (languages, frameworks, tools)
- Certifications, awards, publications

Save the parsed structure to `<workspace>/profile-resume.md`. This becomes the source of truth for tailored resumes — when the `nightly` skill builds a per-role resume, it pulls from here, not from the original PDF.

If the user does not have a current resume, offer to walk them through building one from scratch using the LaTeX template at `assets/resume-template/`. This is a longer flow and worth its own session.

## STEP 5 — Code folder scan (read-only)

Ask the user to point at one or more local code folders — git repos, side projects, school work, modding folders, anything. Walk them read-only. For each folder identify:

- Primary language(s) by file count and recency
- Frameworks/libraries actually imported (not just installed)
- Project shape (web app, CLI, ML model, game, mod, library, infra)
- Approximate size and last-commit recency

Write `<workspace>/skills-inventory.md` summarizing what the user has actually built versus what is on the resume. This catches two important gaps:

1. Skills claimed on resume but not visible in code (potential weak points the user should know about before interviews).
2. Skills demonstrated in code but undersold or absent on the resume (real strengths worth surfacing).

DO NOT modify any files in the user's code folders. Read-only scan only.

## STEP 6 — Project narratives (the 2-4 you'd want to interview about)

Cover letters and resume tailorings only feel personal when they reference real project details — what was hard, what was actually built, what the metrics were. The system needs that ground truth from the user, in their words, so it can surface it without inventing.

Ask the user to name 2-4 projects they would most want to talk about in interviews. For each project, walk through:

- What does it actually do? (their words, not aspirational framing)
- What's the tech stack?
- One or two concrete metrics they can defend (real users, real downloads, real performance numbers, real revenue, real test coverage). If they don't have hard numbers, that's fine — the project still goes in, just without a metric.
- What was the hardest part? What did they learn?
- One-line framing they would use in a cover letter.

If the user has granted view-only access to the code folders for these projects in STEP 5, briefly walk the relevant repo to confirm the user's framing matches what's in the code. Flag any mismatch back to the user for clarification — the user's truth wins, but mismatches between memory and code are useful data.

Save to `<workspace>/profile-projects.md` using the template in `references/starter-files.md`. Do not invent any project detail. Do not inflate metrics. If a number doesn't come from the user, it doesn't go in.

## STEP 7 — Learning interest (shapes skill-gap study suggestions)

Ask the user, in their own words, what they're most interested in learning right now. Examples to give them: a new language they've been curious about, a specific framework, system design, LeetCode-style algorithms, a structured curriculum like CodePath, Advent of Code, Linux internals, a project idea they've been kicking around.

This shapes two things in their morning brief:

1. Which skill-gap entries surface as study suggestions even before they cross the frequency threshold. An explicit interest from the user is a force-override.
2. The resource recommendations the system makes when a study suggestion does surface — if the user said "I want to do LeetCode," study paths lean toward LeetCode resources rather than CodePath.

Encourage the user to keep their actual learning sessions in a separate context — a different Claude chat, an external service like CodePath that has its own engagement cadence, or just heads-down focused study time. The daily-job-hunter loop is for executing applications; learning lives in its own context.

Append the user's learning interest to `<workspace>/profile.md` under a "Learning interest" section.

## STEP 8 — Ethics filter seed (one question with examples)

Ask once, with concrete examples so the user knows what is on the menu:

> "Are there any company types or industries you want pre-filtered out of your job hunt? For example: gambling, AI weapons or military contracting, payday lending, companies with publicly known seven-day work week culture, anti-union employers. You can name specific companies, whole categories, or skip this if you don't want any filter."

Save the response as the initial RED tier of `ghost.md`. Always include "training-repayment-agreement (TRAP) employers" as a pre-seeded RED entry regardless of user input — that's a default ethical filter, not a user preference.

## STEP 9 — Discover and seed boards

Before writing `boards.md`, do an initial board-discovery search based on the user's geography + role focus from `profile.md`. The goal: seed the karma table with relevant universal AND niche boards, so the first `nightly` run has real candidates to work with instead of guessing.

**Universal small-but-high-quality boards** (always seed at karma 0):

- Y Combinator (`workatastartup.com`)
- Wellfound (formerly AngelList)
- Ashby direct (`jobs.ashbyhq.com`)
- Greenhouse direct (`boards.greenhouse.io`)
- Lever direct (`jobs.lever.co`)
- Workable direct
- Handshake (if the user is a student or new grad)

**Geography-specific discovery search.** Run a web search like: "best tech job boards in <user's city/region>" or "<region> startup job boards." Look for boards that serve listings from multiple companies (not single-company portals). Common patterns:

- "BuiltIn <City>" sites in many US metros (note: these can be noisy — verify on company ATS, but seed at karma 0 and let karma decide)
- Regional tech meetup job boards
- Government and civic-tech boards if relevant
- University career networks if the user is recent-grad

**Role-specific discovery search.** Run a web search based on the user's primary role types from `profile.md`. Examples:

- Game industry → `hitmarker.net`, `gamejobs.co`, `gameindustryjobs.com`
- ML / AI → `aijobs.net`, `aijobslist.com`
- Govtech → `govtechjobs.com`
- Remote-only → `remoteok.com`, `weworkremotely.com`, `remote.co`

For every candidate board found, validate it serves listings from 3+ distinct companies. Add validated boards to the `boards.md` karma table at karma 0. Note the discovery source as the seeding reason in the event log: `SEEDED at setup +0 to <board>`.

**Standard denylist seed** (always include — these have a poor track record across most users; karma can override later if needed):

- `builtin.com`
- `indeed.com`
- `dice.com`
- `ziprecruiter.com`
- `glassdoor.com`
- `linkedin.com/jobs` (flagged as discovery-only — use to find role names + companies, then verify on company ATS)

Show the user the seeded list before writing the file. They can remove or add any board on the spot. Their choices ARE the initial calibration tone.

## STEP 10 — Write the rest of the starter state files

Using the templates in `references/starter-files.md`:

- `boards.md` — write the karma table with all boards seeded in STEP 9, plus the denylist and "what counts as a board" definition.
- `ghost.md` — RED/YELLOW/GREEN tier headers with the user's ethics-filter seeds from STEP 8 in RED.
- `applied.md` — empty numbered list with the format header and status legend.
- `pattern-signals.md` — empty file with section headers.
- `posting-freshness.md` — empty log with header.
- `skills-to-learn.md` — empty tally log with category headers (hard requirements, nice-to-haves, below-threshold, study session ideas).
- `profile-projects.md` — populated from STEP 6.

## STEP 11 — Write CLAUDE.md from template

Copy `references/claude-md-template.md` to `<workspace>/CLAUDE.md`. This file captures the standing rules for how the plugin writes materials (resume tightness, JD-quote-verbatim, flex-skill strategy, recruiter-direct outreach play, scam patterns) plus a "project memory" section that grows over time.

Substitute the user's name, role focus, and learning interest into the placeholders marked `<from profile>`. Do not modify the standing rules — those are the keepers.

The `nightly` and `morning-brief` skills both read `CLAUDE.md` at the start of every run.

Tell the user the file exists, what it contains in plain language, and how to add their own notes (they can edit it directly, or say "remember that <X>" in chat and the system will append to the project memory section).

## STEP 12 — Schedule the two daily runs

Use the scheduled-tasks MCP to create:

- A task named `nightly` that runs at 1am user-local-time, weekdays only, invokes the `nightly` skill from this plugin.
- A task named `morning-brief` that runs at 6am user-local-time, weekdays only, invokes the `morning-brief` skill from this plugin.

Confirm the times with the user. Mention they can shift them later — the defaults are based on catching fresh postings before the morning recruiter triage stack at most companies.

Then explicitly tell the user, in plain language:

1. Their computer must stay on (or be configured to wake) at the scheduled times. If the computer is asleep, the runs are skipped silently.
2. The Claude Pro plan ($20/month as of May 2026) is enough to run the full system comfortably. The free tier's daily token limits will hit before the morning brief completes; once on Pro, there is plenty of headroom.

## STEP 13 — Optional dry run

Offer to run one immediate `nightly` pass right now against the seeded boards, so the user can see what the output looks like before tomorrow morning. Mark the result clearly as a preview run. This is optional — if the user wants to wait for the real overnight run, that is fine.

## STEP 14 — User participation contract (mandatory — do not skip)

The system breaks if the user is passive. They need to flag APPLIED and GHOST events back to Claude in chat — otherwise applied.md never grows, karma never updates, and the same dead leads keep resurfacing. Read this contract to the user explicitly and confirm they understand:

> "Heads up — this system runs on your feedback. Two things to tell me, in your own words, whenever they happen:
>
> **1. When you apply to a role**, just tell me. 'I applied to Acme,' 'just applied to that Beta posting in today's brief,' anything that names the company. If you applied to a different role than the one in the brief, mention which. I'll number the entry, log it, and stop suggesting that role.
>
> **2. When you spot a scam, ghost-post, or dead listing**, also just tell me. 'Acme turned out to be a scam,' 'skip Beta for a few months,' 'Gamma keeps reposting ghosts.' I'll figure out whether you mean permanent or temporary. There is no special command — talk like a person.
>
> **Status updates after applying** are useful but not required:
> - 'Acme rejected me' → I update the status, nothing else.
> - 'Acme went silent on me' or 'Acme ghosted me' → status update only. (Getting ghosted by a recruiter is different from a posting being a ghost-post — the first is a status, the second is a kill.)
> - 'Got a screen with Acme' or 'Got an offer from Beta' → status update.
>
> If you don't tell me when you apply or when you kill a lead, I have no way to know. Five minutes a week is enough."

Have the user say "got it" or otherwise confirm before continuing.

## STEP 15 — Confirm completion

Summarize what was set up, in plain language:

- Workspace folder location
- Profile, resume, code inventory, and project narratives captured
- Learning interest noted
- Ethics filter seeded with N entries
- Boards seeded: N universal + N geography-specific + N role-specific (all karma 0, calibrating)
- CLAUDE.md installed with standing rules
- Two scheduled tasks created at HH:MM and HH:MM local time
- All starter state files written

Tell the user what to expect tomorrow morning: a `morning-brief-YYYY-MM-DD.md` file in their workspace, with ranked leads, materials for the top one, an applied tally, and (if applicable) a study-session nudge. Remind them once more that the system needs to hear from them when they apply or when they spot a scam — five minutes a week of casual feedback in their own words is enough.

Tell them where past briefs live: every daily brief is saved as `morning-brief-YYYY-MM-DD.md` in the workspace folder. They can open the workspace in any file browser to revisit prior days, look up a lead they meant to apply to, or skim what they missed.

Other things they can ask Claude in chat (no special syntax — these are examples, not commands):

- "Move the nightly run to 5am" — reschedules the task
- "Reconfigure the job hunter" — reruns this setup
- "Show me my karma table" — Claude reads boards.md back to you
- "Why was BuiltIn down-karma'd?" — Claude reads the relevant event-log entries
- "Remember that I prefer remote-only roles" — appends to CLAUDE.md project memory

Do not run any sweeps automatically as a result of setup. Setup ends here.
