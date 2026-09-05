# Daily-Job-Hunter

Most cold applications get ghosted, and the rest come with no feedback. You spend hours on aggregator sites that reshuffle dead listings, write the same materials from scratch over and over, and don't really know which boards are worth checking next time.

This plugin handles the slog inside Claude Cowork: it finds live postings on the boards that actually work for your situation, drafts tailored resumes and outreach, identifies recruiters worth a direct email, and learns over time which sources produce real leads versus noise. You wake up to a ranked brief with apply links and materials ready. You read, send what you want, and tell the system what stuck and what was a scam.

It writes drafts. You ship them.

## How it avoids confidently wrong output

Early versions produced briefs that read perfectly and were wrong — inflated project metrics, requirements attributed to postings that never listed them, and "no alert arrived from X" lines written off a search that had silently truncated. Four rules fixed it, and they live in the plugin's standing-rules template rather than in anyone's memory:

- **Metrics are read, not recalled.** `skills-inventory.md` is the source of truth for what you can claim, and the resume can't claim what it can't back. See [*no fabricated experience*](https://github.com/reixyz22/Claude-Co-work-Job-Hunter/blob/main/skills/setup/references/claude-md-template.md).
- **Requirement text is quoted verbatim** from the posting. If the JD says "C# or Java," the agent may not add Python.
- **Every claim carries a provenance tier** — ALERT (from a job-alert email), REPORTED (from a named third party), CONFIRMED (read on the employer's own ATS) — and the tiers never merge into one confident voice. A lead that is only ALERT-tier is a normal discovery, not a defect, and it gets labeled as such instead of being dressed up or thrown away.
- **Scam and mirror-mill screening runs before anything else** — redirect aggregators, republished dead listings under fabricated dates, and training-repayment (TRAP) outfits. Patterns documented in [`examples.md`](https://github.com/reixyz22/Claude-Co-work-Job-Hunter/blob/main/skills/setup/references/examples.md).

The same instinct shows up in the tooling: `tools/board_poller/README.md` labels its own ATS endpoint table *unverified — written from recall, not vendor documentation*, and the `--add` command probes each board live before registering it. That is where the guess gets tested.

## Read before installing

This plugin generates AI-written drafts. AI hallucinates. Resume tailorings and outreach are templates, not finished documents — read every one before sending, especially the first ten or twenty while you learn how the model drifts on your background. The full disclaimer is in [`skills/setup/references/disclaimers.md`](https://github.com/reixyz22/Claude-Co-work-Job-Hunter/blob/main/skills/setup/references/disclaimers.md) and is the first thing setup reads to you.

## Quick start

1. Install the plugin in Cowork. daily-job-hunter.plugin file is in the sidebar under releases-- alternatively make the .plugin file yourself by creating a new .zip pasting in repo contents and renaming to 
daily-job-hunter.plugin (.plugin is the file type)
<img width="1322" height="1268" alt="image" src="https://github.com/user-attachments/assets/8cf5a89b-8b1e-472c-aa12-aeeaeaecb787" />

2. Run the `setup` skill in a new chat with / . Claude will ask you for, in order:
   - A workspace folder (state files live there, on your computer, locally — nothing leaves)
   - Name, email, phone, city/state, work authorization, LinkedIn, GitHub (any of these can be skipped if you'd rather fill them in by hand later — note: no street address is collected, city/state is all resumes and geo-matching need)
   - Career stage, role focus, geography, remote tolerance
   - Your best current resume (PDF or LaTeX)
   - One or more code folders for a read-only skills inventory
   - Two to four projects you'd want to talk about in interviews
   - What you most want to learn next (shapes the skill-gap study suggestions)
   - Companies or industries to filter out (ethics seed)
3. Confirm the scheduled tasks (default 1am + 6am local time, plus a 1pm inbox pass if you connect an email account).
4. Optionally do a dry-run preview.
5. Tomorrow morning, read `morning-brief-YYYY-MM-DD.md` in your workspace.
6. Tell Claude when you apply to a role and when you spot a scam — in your own words, no special syntax. The system depends on this; see "You're a participant" below.

Setup takes about ten minutes.

## How it works

Up to three scheduled passes a day.

**Overnight (1am)** runs discovery across three parallel layers — direct ATS polling of your registered target companies, broad source-biased search, and location-first freshness search — then scam-screens, ranks, and builds tailored materials for the best lead.

**Morning (6am)** verifies every apply link, runs a short freshness pass to catch anything posted overnight, computes your applied-tally, and writes the brief you read with coffee.

**Midday (1pm, optional)** scans your inbox. Job-alert email reaches companies no board rotation queries, so it is a discovery channel in its own right — and it is the only channel that reports back on applications you already sent, which is what keeps `applied.md` from drifting out of date.

Every pass reads your `applied.md` and `ghost.md` first to skip anything you've already touched. Each source carries a karma score that climbs when leads work out and decays back toward neutral when they don't, and tiers (CORE / ROTATION / DORMANT / BLOCKED) keep a quiet week from burying a good board permanently.

## board_poller — direct ATS polling, zero tokens

`tools/board_poller/` is a stdlib-only Python tool (no `pip install`) that polls company ATS boards directly — Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, plus an HTML fallback — and reports only what is **new** since the last run.

```
python3 poll_boards.py --add "<your filtered ATS careers URL>"   # register a company
python3 poll_boards.py --run                                     # diff since last run
python3 poll_boards.py --standing                                # everything currently open
python3 -m unittest test_poll_boards                             # 18 offline unit tests
```

The keyword filter is the small half of it. The **diff** is the point: `seen.json` remembers every posting ID ever fetched, so each run surfaces only what appeared since last time — which is how a posting a few hours old gets caught, the strongest ranking signal the pipeline has.

Your `registry.json` (target companies) and `seen.json` are gitignored; `registry.example.json` documents the shape. `REGISTRY-RECOVERY-2026-08-13.md` is the postmortem from the day a cleanup one-liner assumed `boards` was a list when it is a dict and wiped 61 board configs — kept in the repo because the prevention notes are the useful part.

## You're a participant, not a passenger

The system needs to hear from you when:

1. You apply to a role. "I applied to Acme" — anything like that. Without this, the same lead gets recycled tomorrow.
2. You spot a scam or a dead listing. "Acme turned out to be a scam," "skip Beta for a few months" — your own words. Without this, the dead lead keeps coming back.

Five minutes of feedback per week is enough.

## What you get

- Numbered applied tracking with a daily pending count and study-nudge prompts after dry streaks
- Boards with karma and tiers — the system learns which sources actually work for you, and parks the quiet ones instead of killing them
- Ghost-burn tracking with three tiers (RED permanent / YELLOW 90 days / GREEN cooled-off)
- Tailored resume and outreach drafts (with named recruiters when identifiable, never invented). Cover letters are **not** auto-generated — when a role requires one you get a structural outline and an angle, and you write it in your own voice
- Direct ATS polling of your target companies via `board_poller`, no tokens spent
- Salary-band calibration — a lead's comp gets read against winnability, not just ranked by number. High comp at a portal-hiring company without a concrete angle (referral, named contact, a JD line your shipped work directly answers) gets logged as a stretch instead of eating a top-3 slot
- Optional email tracking (if you connect an email account like Gmail) — the midday pass reads your inbox for application confirmations and rejections and keeps `applied.md` current automatically, read-only, never touches anything else in your inbox
- Optional email outreach drafts (same connector) — when a real named contact is found, a ready-to-send email is staged directly in your drafts folder alongside the markdown version. Draft only, always — the plugin never sends on your behalf, and if someone replies, that conversation is handed straight back to you
- Frequency-tallied skill-gap log with concrete study paths (CodePath, Advent of Code, LeetCode, project ideas with expansion routes, language and Linux resources)
- A `CLAUDE.md` template seeded with battle-tested job-hunt rules (resume tightness, JD-quote-verbatim, provenance tiers, flex-skill strategy, recruiter-direct outreach play, scam patterns)
- Autonomous mornings — fresh leads ready when you wake up

## Scheduled runs

Overnight (default 1am local) does the research. Morning (default 6am local) does the verification + delivery. Midday (default 1pm local, weekdays) does the inbox pass and only exists if you connect an email account. Your computer needs to be on or set to wake at the scheduled times.

## Token cost

The Claude Pro plan ($20/month as of May 2026) is enough to run the full system comfortably. The free tier's daily token limit will hit before the morning brief completes.

## Files the plugin writes to your workspace

```
<your-workspace>/
├── CLAUDE.md                      # standing rules + your project memory
├── profile.md                     # name, contact, work auth, targeting, learning interest
├── profile-resume.md              # parsed structure of your resume
├── profile-projects.md            # 2-4 interview-worthy project narratives
├── skills-inventory.md            # what your code shows you can do
├── boards.md                      # karma table + tiers + denylist + event log
├── ghost.md                       # RED/YELLOW/GREEN dead listings
├── applied.md                     # numbered application log
├── alert-channels.md              # which email senders are real channels
├── pattern-signals.md             # what you engage with vs. ignore
├── posting-freshness.md           # timestamp log
├── skills-to-learn.md             # tallied gaps + study paths
├── nightly-leads-YYYY-MM-DD.md    # overnight research handoff
├── morning-brief-YYYY-MM-DD.md    # daily output
├── email-check-YYYY-MM-DD-1pm.md  # midday inbox pass (if email connected)
└── applications/<slug>-YYYY-MM-DD/
    ├── apply-notes.md
    ├── outreach-draft.md
    └── resume.pdf (+ source)
```

## Skills shipped

| Skill           | When                 | Purpose                                                       |
| --------------- | -------------------- | ------------------------------------------------------------- |
| `setup`         | Once, on install     | Onboarding wizard — disclaimers, profile, resume, code scan, schedule |
| `nightly`       | Auto, weekday 1am    | Overnight research + materials for top lead                   |
| `morning-brief` | Auto, weekday 6am    | Verify links, fill gaps, deliver the daily brief              |
| `email-check`   | Auto, weekday 1pm    | Inbox pass — mine job alerts, reconcile `applied.md` (needs an email connector) |

## Changelog

**0.3.0** — Added the `email-check` skill: the midday inbox pass, previously run as an ad-hoc scheduled task, now ships as a documented skill. It mines job-alert email as a discovery channel and reconciles `applied.md` against real confirmations, rejections and interview invites. Two mandatory search passes (the second one deliberately includes Promotions, where alert digests are routinely classified and where a single-pass scan cannot see them), and a hard rule against asserting a negative from a result set that hit its page cap. Added `tools/board_poller`, a stdlib-only Python ATS poller with 18 offline unit tests. Discovery in `nightly` now runs three layers in parallel rather than treating any one as primary — the 2026-08 "poller-primary, web-search-supplement" framing starved the pipeline for two weeks and is retired. Cover letters dropped as an auto-generated deliverable. Board karma is now clamped and decays, with CORE/ROTATION/DORMANT/BLOCKED tiers so a dry week parks a source instead of burying it.

**0.2.0** — Added optional email-connector integration (e.g. Gmail via Cowork). When connected: the pipeline can search your inbox for application confirmations and rejections and keep `applied.md` current without manual copy-paste, and the nightly pass can stage a real outreach email as a draft in your account when a good named contact is found. Both capabilities are strictly read/draft-only — no send capability is ever used, and replies are never auto-answered. Entirely optional; the plugin works the same without it.

**0.1.1** — Setup no longer asks for a street address, just city/state (or city/country) — resumes and geo-matching never needed more than that, and asking for it was a privacy overreach. Added salary-band calibration to the nightly research pass so high-comp leads get ranked by winnability, not just by the number.

**0.1.0** — Initial release.

## Author

Built by William Reixyz Pitts ([github.com/reixyz22](https://github.com/reixyz22)).

## License

MIT. See `LICENSE`.
