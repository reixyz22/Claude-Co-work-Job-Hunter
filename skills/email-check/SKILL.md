---
name: email-check
description: Midday inbox pass. Mines job-alert email as a primary lead source, reconciles applied.md against real confirmations and rejections, and reports what actually changed. Runs unattended via scheduled task at 1pm local time on weekdays. Not normally invoked manually.
---

# Midday email check

Third scheduled pass of the day, between `nightly` (1am) and the next `morning-brief` (6am).
Requires an email connector (e.g. Gmail via Cowork). Without one, this skill does not run —
the pipeline still works on two passes.

**Read-only on the inbox. Search and summarize. Never send, never reply, never archive.**

Read before scanning: `<workspace>/CLAUDE.md`, `<workspace>/applied.md`, `<workspace>/ghost.md`,
`<workspace>/alert-channels.md` (the sender list, if present).

## Why this pass exists

The user's own job-alert email is a discovery channel the board rotation cannot reach. Alerts from
Greenhouse/MyGreenhouse, Handshake, LinkedIn and similar surface companies that are not in any board
registry and never come up in a source-biased search. Treat every job title in an alert as worth
considering unless `ghost.md` kills it.

It is also the only channel that reports back on applications already sent. `applied.md` drifts out
of date within days without it.

**Expectation setting: this is a sift-through-sand pass, not a high-yield sweep.** On a slow day
"nothing changed" is the correct output and should be stated plainly. Do not manufacture leads to
justify the run, and do not spend the karma/board bookkeeping ceremony of `nightly` on every digest
hit — reserve a formal `ghost.md` kill for something worth remembering (a real eligibility gate, a
scam pattern, a company that earns a RED card).

## STEP 1 — Scan the window, in TWO passes

The window runs from the last completed check through today, including any lapsed days (a Monday run
covers the weekend).

**Pass 1 — date range over Primary/Updates/Forums:**
`after:YYYY/MM/DD before:YYYY/MM/DD -category:promotions -category:social`

**Pass 2 — explicit senders, Promotions deliberately INCLUDED:**
`from:<alert-sender-1> OR from:<alert-sender-2> OR ...` over the same window.

Pass 2 is not optional and its filter is the whole point. Mail providers routinely classify job-alert
digests as Promotions, which makes them invisible to pass 1 *by construction*. A channel that "stopped
arriving" is a categorization question before it is ever a market signal. Keep the sender list in sync
with `alert-channels.md`.

**Never assert a negative from a truncated scan.** Search APIs cap at `pageSize`. If a query returns
exactly `pageSize` results, the set is truncated by definition and cannot support "nothing arrived
from X." Paginate, narrow the window, or run a targeted sender query first. State in the writeup
whether each pass was truncated, so the negatives in it are real negatives.

## STEP 2 — Classify every message

**Application signals** (these change `applied.md`):

| Signal | Action |
| --- | --- |
| "Thank you for applying to `<role>`" | New entry with the real applied date, or backfill an existing one |
| Rejection | Mark REJECTED |
| Interview / screener / take-home invite | Mark SCREENER, surface as time-sensitive |

**Not application signals** — account plumbing. Account activations, "verify your candidate account,"
login codes, forwarding confirmations. Users create portal accounts and handle codes routinely. Never
log an `applied.md` entry from one, and never surface one as an outstanding action item.

**An email sitting in the inbox says nothing about whether the user acted on it.** Read state, unread
state, a verification link still visible — none of it is evidence about a link clicked or a form
filled. Assume handled. The only thing worth raising is an *observable* downstream failure: mail that
should be arriving has stopped, or a submitted application that never produced a confirmation. Report
the observable symptom, not a guess about which click was missed. If read state matters, check the
message's own unread flag rather than asserting it.

## STEP 3 — Mine alerts for leads

Cross-reference every candidate against `applied.md` and `ghost.md` first; kill matches before
spending anything on them.

**Label every claim with its provenance tier. Do not merge tiers into one confident voice.**

- **ALERT** — from the alert email itself; usually title, company, rough location, nothing more.
- **REPORTED** — from a third party; name which one (Dice, BuiltIn, ZipRecruiter, jobgether…).
- **CONFIRMED** — read on the employer's own ATS.

A lead arriving unverified is the expected state at discovery, not a defect. Discovery and
verification are separate steps and must not be collapsed in either direction: do not present an
ALERT-tier lead as confirmed, and do not discard a real lead because it is only ALERT-tier. Conflicting
numbers between two aggregators are a finding worth surfacing, not noise to average away.

**Login-walled sources: the digest is a ping, not the job list.** Some feeds send a handful of cards
by email while the full list sits behind a login, and the two are not the same set. Never characterize
what such a source surfaced from its email. Open the real feed in the browser and read it, or say plainly that this pass
did not. The same applies to a single posting from those sources: it cannot be verified, located on an
ATS, or ranked from the email text alone.

**A completed employer-ATS check is an answer — commit to it.** If the employer's own board has been
read directly and the req is not there, that is a CONFIRMED-tier kill; log it and move on. Hedging
after doing the work discards the verification and hands the labor back to the user. Genuine
ambiguity — a JS shell that never rendered, a portal that would not load — is different and gets
flagged UNVERIFIED rather than concluded either way.

**Cohort and eligibility gates live in the JD body, not the title.** A year in a title proves nothing
in either direction, and platform "you match all qualifications" badges and "entry level" seniority
tags are confirmed unreliable. Pull the eligibility sentence before killing *or* ranking a
cohort-labeled req.

## STEP 4 — Write the check

Save to `<workspace>/email-check-YYYY-MM-DD-1pm.md`:

1. **Window scanned + truncation status of both passes.** One line. This is what licenses every
   negative below it.
2. **Short version.** Two sentences: what is worth acting on today, and what did not move.
3. **Leads**, each with its provenance tier, why it clears the gates (quoting the JD's eligibility
   language verbatim), and the direct apply link.
4. **Unresolved** — what could not be verified and the specific check that would resolve it. Be
   honest that it is unresolved; do not round it up or down.
5. **Pipeline** — every `applied.md` change made, and anything that should have arrived and has not.
6. **Killed today** — with the one-line reason each.
7. **Channel notes** — which senders produced signal, which produced junk, any channel that went
   quiet and whether that is categorization or reality.

Then apply the `applied.md` / `ghost.md` / `posting-freshness.md` updates the writeup describes.
The writeup and the state files must not disagree.
