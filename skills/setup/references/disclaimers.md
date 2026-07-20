# Read this first

You're about to run an autonomous job-hunt system that searches the web, scores postings, and drafts cover letters and resume tailorings on your behalf. Before you trust it for anything you'd send to a human, please understand the following.

## 1. AI hallucinates

The model writing your cover letters and resume bullets does not have ground truth about your career. It will sometimes:

- Invent metrics ("led a team of 10" when you led 4)
- Swap company names or job titles between adjacent bullets
- Misremember which project used which language or framework
- Confidently cite a job posting requirement that isn't actually in the JD
- Phrase your background in ways that sound plausible but are subtly wrong
- Inflate adjectives — a bullet that reads "wrote sustainable, modular, testable code" sometimes appears on projects that have no tests, and "integrated with multiple APIs" sometimes appears on a tool that calls one. The model reaches for impressive-sounding language even when the language does not match what the code actually does.

**You must read every cover letter and resume tailoring before sending.** Especially the first ten or twenty drafts — that is how you learn the specific ways the model tends to drift on your particular background, and how to correct your `profile.md` so future drafts are tighter.

The materials this plugin generates are templates and starting points. They are not finished documents. They are not ready to send out of the box. They get better the more you correct the system, but they will never be safe to send unread.

## 2. Most "scams" are not actually scams — they're noise

The plugin scam-screens results, but the bigger reality is that most of what gets killed is not malicious. It is mostly:

- **Ghost postings.** Companies post jobs for tax credits, optics, or pipeline-padding without actually intending to fill them. Common at large companies and government contractors. Hard to detect from outside; karma calibrates over time as you flag them.
- **Aggregator pollution.** Sites like BuiltIn run ads on listings well after they are filled, and "Reposted X days ago" labels often have nothing to do with the actual posting status. Verify any aggregator-sourced lead on the company's own ATS before treating it as live.
- **Signup baiting.** Apply links that route through a third-party "register to view" page. Not malware, just funneling you into someone else's onboarding for something that should be free. The plugin flags these.

The minority that are actually predatory:

- **Training Repayment Agreements (TRAPs).** "Free" training programs that lock you into a $20–30k clawback if you leave within 1–3 years. Always declined.
- **Cold "recruiter" DMs from accounts with no employment history.** Generic titles, asking you to register on an external site to "see the role."
- **Comp ranges that are impossibly high for the title.** A "junior engineer" role offering staff-level pay is almost always either misfiled, a bait-and-switch, or a scam.

If something feels off, trust the instinct. Tell Claude to dig deeper before applying.

## 3. The karma system needs days to calibrate

The plugin learns which job boards produce live, applicable postings for **your** location and **your** role types. This learning happens through a karma score on each board, updated after every sweep based on which leads turned out real and which turned out dead.

For the first roughly 5–10 days of operation, karma scores are essentially random. Boards that work great in one city are often junk in another. A board that surfaces solid backend Python roles may produce nothing useful for game-engine roles. **You set the initial tone of what is worth filtering** — flag dead listings as you encounter them, mark scams when you spot them, reject leads that aren't actually a fit. The system listens to those signals and improves.

This means: do not fully trust the rankings during the first week. Verify aggressively. After about two weeks of feedback, the rankings get sharp and the brief becomes high-signal.

Even after calibration, brand new scam patterns appear constantly. The system catches what it has seen before. You catch the rest.

## 4. You stay in the loop on every send

The plugin never:

- Submits a job application on your behalf
- Sends an outreach message without your review
- Pays for anything
- Talks to a recruiter while pretending to be you
- Modifies code in your repos
- Posts to your social accounts

It produces drafts. You ship them. If a future version of this plugin offers any kind of auto-send feature, it will be opt-in and clearly flagged.

**If you connect an email account (e.g. Gmail) to Cowork,** the plugin can do two additional things, both bounded by the same rule above:

- Stage a real outreach email as a draft sitting in your email account's drafts folder, ready for you to review and send yourself. It will never use a send capability even if the connector technically has one.
- Read your inbox (search only, never send/reply/delete) to catch application confirmations and rejections you haven't manually reported, so `applied.md` stays current without you having to paste every email in by hand.

Connecting an email account is entirely optional. Nothing in this plugin requires it — it just reduces manual bookkeeping if you choose to enable it. If a recruiter replies to a staged draft after you send it, the plugin will never draft or send a follow-up on your behalf — that conversation is yours from that point forward.

## 5. You're an active participant, not a passenger

The system needs feedback from you to work. Two things:

- **When you apply to a role**, tell Claude in your own words — "I applied to Acme," "just applied to that Beta posting," whatever. Without this, the same lead gets recycled into tomorrow's brief.
- **When you spot a scam, ghost-post, or dead listing**, also tell Claude in your own words — "Acme turned out to be a scam," "skip Beta for a few months," "Gamma reposts ghosts." Claude figures out whether you mean a permanent kill or a temporary skip.

There is no special command syntax. Talk like a person; the system will translate to its internal log.

If you stay silent — apply without telling the system, dismiss scams in your head without flagging them — the same dead leads keep recycling and the boards never learn what is actually working for you. About five minutes a week is enough to keep things calibrated.

## 6. The flex-skill strategy is intentional, and you're responsible for closing the gap

Hiring filters are keyword-based. A resume that doesn't hit a job description's required keywords often drops before any human reads it. To work around this, the plugin sometimes lists skills you could credibly study to working knowledge in 6-12 hours between a screen and the actual interview. These are FLEX skills, capped at two per application, and the apply-notes for that role will include a "STUDY BEFORE THE SCREEN" section telling you exactly what to brush up on.

This strategy is honest about what it is — it's how applications actually clear the filter when the requirements list is wider than what you happen to know today. The risk is real: if a screen calls and you've ignored the FLEX prompt, the technical conversation will surface the gap. Treat the FLEX list in your morning brief as a study cue, not background noise.

The plugin will never flex more than two skills, and never flex something you can't credibly study in a short window (it won't claim "Rust" if you've never written Rust). If a JD's gap is fundamental — no demonstrated work experience for a senior role, a specialty stack that takes months to learn — the lead is killed cleanly rather than flex'd.

## 7. Heads up on a few practical things

- Your computer must be on (or set to wake) at the scheduled run times. If it's asleep, the run is skipped silently.
- The Claude Pro plan ($20/month as of May 2026) is enough to run the full system comfortably. The free tier's daily token limit will hit before the morning brief completes; once you upgrade, you have plenty of headroom for both daily runs.
- The plugin writes to a workspace folder you choose. It does not write anywhere else on your computer.
- Code folders you point it at during setup are scanned read-only. The plugin never modifies your code.

If you understand all of the above, type "got it" or just continue, and we'll move to setup.
