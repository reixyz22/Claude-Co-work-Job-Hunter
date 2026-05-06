# CLAUDE.md template

The `setup` skill copies this file to `<workspace>/CLAUDE.md` during STEP 11, substituting the placeholders marked `<from profile>` with the user's actual values from `profile.md`.

The `nightly` and `morning-brief` skills read this file at the start of every run.

The standing rules below are battle-tested in production and should not be modified casually. The "Project memory" section at the end is intentionally empty and grows over time as patterns become clear from the user's `applied.md` / `ghost.md` activity, or as the user explicitly says "remember that <X>" in chat.

---

```markdown
# CLAUDE.md — daily-job-hunter standing rules + project memory

This file is read at the start of every nightly and morning-brief sweep. It captures:

1. The standing rules for how this system writes materials (the keepers — don't change without strong reason)
2. The user's project memory (grows over time as patterns become clear)

## User context (from setup)

- User: <from profile — preferred name>
- Role focus: <from profile — primary role types>
- Career stage: <from profile>
- Geography + remote tolerance: <from profile>
- Learning interest: <from profile>

## 1. Materials standards (do not violate)

- **Resume is one page, hard.** Past failures: 1.1-page renders shipped to recruiters look amateur. Cut ruthlessly. Stretch claims stay only when role genuinely demands them.
- **JD quote verbatim.** When writing the "what they want" section of `apply-notes.md`, quote the JD's actual language. Do not add languages, frameworks, or skills the JD doesn't list. If JD says "C# or Java," do not add Python.
- **No AI-vibe prose.** Cover letter bullets are punchy and concrete. Avoid: "I am a passionate software engineer with a strong interest in...", "Leveraging my expertise to drive impactful solutions," any sentence the user wouldn't say out loud. Voice should be direct, slightly informal, factual.
- **No fabricated experience.** `skills-inventory.md` is the source of truth. The resume can't claim skills the user can't credibly back. Aspirational skills go to `skills-to-learn.md`, not the resume. Flex strategy is the controlled exception.
- **Inference rules for unstated skills.** Don't make the user spell out everything. Reasonable inferences:
  - University CS programs usually involve Java (CS101 typically) — count as real Java exposure
  - Game modding / scripting often involves C# — count as real C# exposure
  - Web projects almost always involve some HTML/CSS/JS — count
  - Any agile-feeling team project is real Agile experience
  - But: do NOT infer skills not implied. If the user has no Rust code and didn't mention Rust, the resume does not claim Rust.
- **Resume compile safety check (mandatory after every render):**
  1. Page count is exactly 1
  2. No clipping at any margin (especially the right edge of the header — `github.com/<handle>` must not truncate)
  3. No paragraph orphaned to a second page
  If any check fails, edit and re-render. A clipped resume is the single most professionally damaging output the plugin can produce.

## 2. Resume layout convention

The recruiter F-shape reading pattern: strong stuff top-left, weak stuff bottom-right. The plugin's default resume order:

1. Skills (top — must hit JD keywords)
2. Projects (top-3 most relevant, rotated based on JD)
3. Professional experience
4. Teaching / mentorship / leadership
5. Education (bottom — non-target schools should be present but not headlined)

Sidebar LaTeX style is the default — `\mysidestyle` in the included resume.cls is the single hook for layout customization.

## 3. The flex-skill strategy (intentional, with disclosure)

Hiring filters are keyword-based. A resume that doesn't hit the JD's required keywords often drops before any human reads it. The flex-skill strategy: for skills the user could credibly study to working knowledge in 6-12 hours between a screen and the actual interview, list them on the resume to clear the keyword filter.

Rules:

- Two flex skills max per application. More than that is fiction.
- Flex must be backable in ~6-12 hours of focused study. Not "I'll cram a new language."
- `apply-notes.md` MUST include a "STUDY THIS BEFORE THE SCREEN" section listing the FLEX skills + specific resources from `skills-to-learn.md`.
- The morning brief tells the user which skills are FLEX so they know what to brush up on if a callback lands.

## 4. Outreach play — finding a human is the force multiplier

The application form is the baseline. For Tier-1 leads (high karma + good fit + named team), the system additionally:

1. Identifies a real recruiter or hiring engineer at the company via LinkedIn search
2. Drafts a short cold email or LinkedIn DM (~80-150 words) referencing the role + one concrete portfolio match from `profile-projects.md`
3. Saves to `outreach-draft.md` alongside the cover letter

Pattern that works in production: cold-applied via standard channel, no response. Cold-emailed a recruiter found on LinkedIn with one specific portfolio detail. Got a reply within a day. Got into the pipeline.

Rules:

- Never invent recipient names. If no real person is identifiable on LinkedIn, say so in `outreach-draft.md` and skip.
- Never claim a referral the user doesn't have.
- Outreach is always a draft. The user reviews and sends.

## 5. Scam screening and aggregator skepticism

Patterns that have surfaced in production:

- TRAP / training-academy companies offering "free training" with $20-30k clawback if the user leaves within 1-3 years → permanent RED
- Brand-named job listings that route through unrelated aggregator domains to premium-signup paywalls → permanent RED
- Aggregator boards with "Reposted X days ago" labels showing dead listings → add domain to denylist
- Cold "recruiter" DMs from accounts with no employment history → ignore, do not surface as outreach contacts

Rule: if a company's brand appears to be an aggregator scrape rather than the company's own posting, verify on the company's own ATS before treating as live.

## 6. Source verification

Every lead in the morning brief must have a direct link to the company's own ATS (Workday, Greenhouse, Lever, Ashby) — not an aggregator. Aggregator links go in the notes as discovery sources only.

If the company's ATS portal is JS-rendered and can't be scraped cleanly, hand the user the portal URL to verify themselves rather than block the brief.

## 7. Generalist framing — search broad, don't pigeonhole

Search broadly across the user's stated role types AND credible adjacencies. If the user said "junior backend Python," surface backend Python AND junior generalist AND data engineering with Python AND DevOps with Python — anything where the user's profile is a credible read.

The brief HIGHLIGHTS leads matching expressed direction but does not LIMIT to them. This is about searching, exploring, and growing — not narrowing into a single track.

Two exceptions:

1. Senior users may have legitimate forced specialization. A 10-year systems engineer with no ML background should not get ML platform leads.
2. The user may explicitly say "only show me X" — directional preference overrides generalist sweep.

## 8. Don't pull in context the user didn't invite

Cover letters and resume tailorings use ONLY: `profile.md`, `profile-resume.md`, `profile-projects.md`, `skills-inventory.md`, this file (`CLAUDE.md`), and the JD. Nothing else.

No biographical color the user did not put in their profile. No emotional framing. The user is the editor of their own narrative.

## 9. Anti-patterns surfaced in production

(See `skills/setup/references/examples.md` in the plugin for the full case-study list. Most important rules to internalize:)

- AI hallucinates metrics — baseline truth comes from setup, not from the model.
- Aggregator "reposted" labels are decoration, not evidence.
- The application is the baseline; finding a human is the force multiplier.
- Empty brief is a valid output. Padding briefs trains the user to ignore the system.
- Caveman-speak never reaches a human — internal scratch can be telegraphic, anything user-facing stays full prose.
- Don't kill leads for partial fit — note the gap, FLEX where bridgeable, surface the lead.

## 10. Token discipline

- Caveman-style trimming is fine in internal artifacts (TodoList items, scheduled-task prompts, scratch summaries). Full prose in everything the user reads (briefs, materials, outreach, this file's edits).
- Don't re-Read after Write — Edit/Write errors on failure.
- Don't spawn a subagent for a trivial single-file lookup.
- Don't echo full tool output back into chat when the user already saw it.
- Use diffs not full-file pastes when reporting changes.

## 11. Project memory (grows over time — append-only unless user explicitly edits)

Patterns get added by the user (via chat: "remember that I don't apply to X") OR by the morning-brief skill when patterns become obvious from `applied.md` / `ghost.md` activity. Examples of what lives here:

- "User prefers small teams (under 100 people) — engagement signal from applied.md after first 20 applications"
- "User does not engage with consulting roles regardless of company strength"
- "User's strongest portfolio piece is `<project name>` — lead with it in cover letters for relevant roles"
- "User has a real recruiter relationship at `<company>`; that channel beats the apply form"
- "User got burned by aggregator `<X>` — denylist hardened"

(no entries yet — this section grows organically as the system learns the user)
```
