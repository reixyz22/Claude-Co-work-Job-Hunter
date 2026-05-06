# Examples — case studies from production runs

Each entry is a real failure mode (or a real success pattern) and the rule it produced. These are the anti-patterns and corrections that save users weeks of trial-and-error.

## Aggregator listings show dead postings as fresh

A "Reposted 2 Days Ago" label on a popular aggregator stayed up for weeks after the role had been filled. Multiple aggregators were caught doing this — the apprenticeship had expired in November, the careers page on the company's own site confirmed it dead, and the aggregator kept marketing it as fresh.

**Rule:** Aggregator "reposted" labels are decoration, not evidence. Verify on the company's own ATS (Workday, Greenhouse, Lever, Ashby) before treating any lead as live. If a board does this repeatedly, add its domain to `boards.md` denylist.

## The redirect-aggregator scam

A LinkedIn listing branded as a major AI lab routed through an unrelated aggregator domain to a premium-signup paywall. The "real" listing on the company's own site had been stale for 30+ days. The aggregator scraped the brand and inserted a paywall in the click-through.

**Rule:** Scrutinize the URL chain on every aggregator-sourced lead. If the apply button takes you off the company domain to a third-party signup form before you reach the actual application, it's a scam. Mark RED in `ghost.md` and add the redirect domain to denylist.

## Cold email beat cold apply (the most important success pattern)

A user cold-applied to a target studio via the standard apply form and got nothing. They then identified a recruiter on LinkedIn, cold-emailed them with a short specific message — the role plus one concrete portfolio project that matched the JD — and got a reply within a day. Within a week they were shortlisted into the pipeline.

**Rule:** The application form is the baseline. Finding a human is the force multiplier. For every Tier-1 lead, the `nightly` skill produces both: an `apply-notes.md` AND an `outreach-draft.md` targeting a real named recruiter or hiring engineer (not a generic "Recruiting Team"). The outreach is short, specific, and references one concrete portfolio match. Never invent recipients — if no human is identifiable, say so in the outreach-draft and skip it.

## The hallucinated metric

A resume bullet originated as an AI overclaim — "1,000+ concurrent users" — that turned out to be impossible. Ground truth was 1,000+ cumulative unique users across the tool's lifetime, with about 200 average concurrent. The user had to walk it back across multiple already-submitted applications.

**Rule:** AI inflates numbers by default. Baseline truth lives in `profile-resume.md` and `profile-projects.md`, captured during setup from things the user actually said. Resume tailoring is allowed to surface different bullets, never to invent metrics. If the user can't immediately verify a number you wrote, you made it up.

## The JD-inflation cover letter

A cover letter was built on the premise that a JD asked for Python, when the JD actually said "C# or Java." The whole pitch was wrong because the apply-notes inflated the JD with a language the company hadn't asked for.

**Rule:** When writing the "what they want" section of `apply-notes.md`, quote or closely paraphrase the actual JD. Never add languages, frameworks, or skills that aren't there. If you're using a flex-skill strategy, mark FLEX explicitly and limit to two per resume.

## The flex-skill strategy (intentional, with disclosure)

Hiring filters are keyword-based. A resume that doesn't hit a JD's required keywords often drops before a human ever sees it. The flex-skill strategy: for skills the user could credibly study to working knowledge in 6-12 hours between a screen and the actual interview, list them on the resume to clear the keyword filter, AND document them as FLEX in apply-notes so the user knows what to study before any callback.

**Rule:** Two flex skills max per application. More than that crosses into fiction. Flex must be backable in ~6-12 hours of focused study — not "I'll cram a new language." Apply-notes for any flex'd application MUST include a "STUDY BEFORE THE SCREEN" section listing the FLEX skills and specific resources pulled from `skills-to-learn.md`.

## Don't kill leads for partial fit

A JD listing "5+ years of experience" on a junior posting often means "we'll consider strong 1-3 year candidates." A JD listing "Java, Go, or Python" with the user only knowing Python means apply with confidence. Killing leads for missing 1-2 keywords is leaving applications on the table.

**Rule:** Surface the lead, mark the gap. Use FLEX where the gap is bridgeable. Only kill leads for partial fit when the missing piece is fundamental — a senior staff role for someone with no work experience, a specialty stack that takes months to learn.

## The clipped resume header

A pdflatex render cut "github.com/yourname" to "github.com/yourn" because the right margin overflowed by one character. The resume shipped to a recruiter with the truncation unnoticed.

**Rule:** Every PDF render gets visually verified before delivery. Page count exactly 1. No clipping at any margin (header right edge especially). No paragraph orphaned to a second page. If any check fails, edit and re-render. Never deliver a clipped resume — it is the single most professionally damaging output the plugin can produce.

## Don't pull in context the user didn't invite

An earlier session referenced unrelated personal history mid-task. The user pushed back: *"feel like you're feeding me things that aren't for me."*

**Rule:** Cover letters and resume tailorings use ONLY `profile.md`, `profile-resume.md`, `profile-projects.md`, `skills-inventory.md`, and the JD. Nothing else. No biographical color the user didn't put in their profile. No emotional framing. The user is the editor of their own narrative.

## Don't claim aspirational experience

A user listed a framework they wanted to learn but had not actually demonstrated. It sat on the resume as a fully-claimed skill. In a phone screen, it would have surfaced as a hole.

**Rule:** `skills-inventory.md` is the source of truth for what the user can credibly claim. The resume can't outpace it. Aspirational skills go to `skills-to-learn.md` with a study path, not the resume. Flex strategy is the controlled exception (and only with the FLEX disclosure pattern).

## Hackathon framing accuracy

A user described a hackathon win as "rapid prototyping" — the standard framing — when the event was actually a timed coding competition (HackerRank-style: specific inputs, specific outputs, scored on correctness under time pressure). Not the same thing. Different signal entirely.

**Rule:** Ask about past achievements during setup. Don't assume the standard framing. Set the truth in `profile-projects.md` and never deviate from it.

## TRAP / training academy decline

Companies offering "free" training programs with $20-30k clawback if you leave within 1-3 years. Flag at scam-screen, never after applying. The economics are bad and the legal exposure is real.

**Rule:** TRAP outfits get RED in `ghost.md` permanently. The plugin's pre-seeded ethics filter examples should include "training-repayment-agreement (TRAP) employers" so users encountering them have language ready to flag the pattern.

## Trading firms (and other low-yield-direct-apply targets) deprioritized

Trading firms are interesting work but historically take a masters + return-offer path. For non-target-school juniors applying directly with no prior intern conversion, yield is near-zero. Keep them on the targeting list (they're aspirational signals about what the user values), but don't let them eat top-3 brief slots.

**Rule:** Target list ≠ apply weight. Junior-friendly generalist roles get priority in the brief. Aspirational-target leads appear when they appear, but always alongside a concrete project suggestion that would make the application credible (logged to `skills-to-learn.md` study ideas).

## Empty brief is a valid output

If the boards are quiet, the brief says so. Padding briefs with low-confidence junk trains the user to ignore the system. Honest empty briefs train them to trust it.

**Rule:** Producing zero leads is a valid sweep outcome. State it plainly with a one-line reason ("boards quiet today, kill list hit hard, low-confidence-only results").

## Caveman-speak never reaches a human

Internal scratch notes, todo items, and tool-call prompts can be telegraphic to save tokens. Anything the user pastes into a form, sends to a recruiter, or reads as a brief stays in clean, full-sentence prose.

**Rule:** Cover letters, resumes, outreach drafts, the morning brief — all in the user's voice, full prose. Token discipline applies to internal artifacts only.
