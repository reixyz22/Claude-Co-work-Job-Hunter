# Daily-Job-Hunter

Most cold applications get ghosted, and the rest come with no feedback. You spend hours on aggregator sites that reshuffle dead listings, write the same cover letter from scratch over and over, and don't really know which boards are worth checking next time.

This plugin handles the slog inside Claude Cowork: it finds live postings on the boards that actually work for your situation, drafts tailored resumes and cover letters, identifies recruiters worth a direct email, and learns over time which sources produce real leads versus noise. You wake up to a ranked brief with apply links and materials ready. You read, send what you want, and tell the system what stuck and what was a scam.

It writes drafts. You ship them.

## Quick start

1. Install the plugin in Cowork. daily-job-hunter.plugin file is in the sidebar under releases-- alternatively make the .plugin file yourself by creating a new .zip pasting in repo contents and renaming to 
daily-job-hunter.plugin (.plugin is the file type)
<img width="1322" height="1268" alt="image" src="https://github.com/user-attachments/assets/8cf5a89b-8b1e-472c-aa12-aeeaeaecb787" />

2. Run the `setup` skill in a new chat with / . Claude will ask you for, in order:
   - A workspace folder (state files live there, on your computer, locally — nothing leaves)
   - Name, contact info, work authorization, LinkedIn, GitHub (any of these can be skipped if you'd rather fill them in by hand later)
   - Career stage, role focus, geography, remote tolerance
   - Your best current resume (PDF or LaTeX)
   - One or more code folders for a read-only skills inventory
   - Two to four projects you'd want to talk about in interviews (the source of truth for cover letters)
   - What you most want to learn next (shapes the skill-gap study suggestions)
   - Companies or industries to filter out (ethics seed)
3. Confirm the two scheduled tasks (default 1am + 6am local time).
4. Optionally do a dry-run preview.
5. Tomorrow morning, read `morning-brief-YYYY-MM-DD.md` in your workspace.
6. Tell Claude when you apply to a role and when you spot a scam — in your own words, no special syntax. The system depends on this; see "You're a participant" below.

Setup takes about ten minutes.

## How it works

Two scheduled passes a day. The overnight pass searches your top-karma boards, scam-screens results, ranks leads, and builds tailored materials for the best one. The morning pass verifies every apply link, fills any gaps, computes your applied-tally, and writes the brief you read with coffee. Both passes read your `applied.md` and `ghost.md` first to skip anything you've already touched. Each job board has a karma score that climbs when leads work out and drops when they're dead, so search budget follows what actually produces value for your specific city and role type.

## Read before installing

This plugin generates AI-written drafts. AI hallucinates. Cover letters and resume tailorings are templates, not finished documents — read every one before sending, especially the first ten or twenty while you learn how the model drifts on your background. The full disclaimer is in [`skills/setup/references/disclaimers.md`](https://github.com/reixyz22/Claude-Co-work-Job-Hunter/blob/main/skills/setup/references/disclaimers.md) and is the first thing setup reads to you.

## You're a participant, not a passenger

The system needs to hear from you when:

1. You apply to a role. "I applied to Acme" — anything like that. Without this, the same lead gets recycled tomorrow.
2. You spot a scam or a dead listing. "Acme turned out to be a scam," "skip Beta for a few months" — your own words. Without this, the dead lead keeps coming back.

Five minutes of feedback per week is enough.

## What you get

- Numbered applied tracking with a daily pending count and study-nudge prompts after dry streaks
- Boards with karma — the system learns which sources actually work for you
- Ghost-burn tracking with three tiers (RED permanent / YELLOW 90 days / GREEN cooled-off)
- Tailored resume, cover letter, and outreach drafts (with named recruiters when identifiable, never invented)
- Frequency-tallied skill-gap log with concrete study paths (CodePath, Advent of Code, LeetCode, project ideas with expansion routes, language and Linux resources)
- A `CLAUDE.md` template seeded with battle-tested job-hunt rules (resume tightness, JD-quote-verbatim, flex-skill strategy, recruiter-direct outreach play, scam patterns)
- Autonomous mornings — fresh leads ready when you wake up

## Two daily runs

Overnight (default 1am local) does the research. Morning (default 6am local) does the verification + delivery. Your computer needs to be on or set to wake at the scheduled times.

## Token cost

The Claude Pro plan ($20/month as of May 2026) is enough to run the full system comfortably. The free tier's daily token limit will hit before the morning brief completes.

## Files the plugin writes to your workspace

```
<your-workspace>/
├── CLAUDE.md                    # standing rules + your project memory
├── profile.md                   # name, contact, work auth, targeting, learning interest
├── profile-resume.md            # parsed structure of your resume
├── profile-projects.md          # 2-4 interview-worthy project narratives
├── skills-inventory.md          # what your code shows you can do
├── boards.md                    # karma table + denylist + event log
├── ghost.md                     # RED/YELLOW/GREEN dead listings
├── applied.md                   # numbered application log
├── pattern-signals.md           # what you engage with vs. ignore
├── posting-freshness.md         # timestamp log
├── skills-to-learn.md           # tallied gaps + study paths
├── morning-brief-YYYY-MM-DD.md  # daily output
└── applications/<slug>-YYYY-MM-DD/
    ├── apply-notes.md
    ├── cover-letter.md
    ├── outreach-draft.md
    └── resume.pdf (+ source)
```

## Skills shipped

| Skill           | When                | Purpose                                                       |
| --------------- | ------------------- | ------------------------------------------------------------- |
| `setup`         | Once, on install    | Onboarding wizard — disclaimers, profile, resume, code scan, schedule |
| `nightly`       | Auto, weekday 1am   | Overnight research + materials for top lead                   |
| `morning-brief` | Auto, weekday 6am   | Verify links, fill gaps, deliver the daily brief              |

## Author

Built by William Reixyz Pitts ([github.com/reixyz22](https://github.com/reixyz22)).

## License

MIT. See `LICENSE`.
