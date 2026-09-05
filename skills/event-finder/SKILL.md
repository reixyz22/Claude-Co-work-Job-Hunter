---
name: event-finder
description: WORK IN PROGRESS. Twice-weekly sweep for in-person events that measurably move the user toward a job — hiring events, user groups, hackathons — ranked by who is in the room rather than by how the event looks. Reads the user's profile for radius, budget and eligibility. Never registers or RSVPs on the user's behalf.
---

# IRL event finder — impact-ranked, in-person only

> **Status: work in progress.** The ranking model and the kill rules are settled and running.
> The source registry is not — it is currently seeded by hand per city (see STEP 1). Treat this
> skill as usable but unfinished, and expect the registry section to change.

Runs twice a week. Surfaces in-person events worth the user's time, appends everything found to
`<workspace>/events.md`, and delivers a short ranked list. The user confirms or declines.

**Never RSVP, never register, never put the user's name on a list.** Surface with enough detail
to judge; the decision is theirs.

Read first: `<workspace>/profile.md` (location, transit radius, budget, constraints),
`<workspace>/ghost.md` (the RED list applies to hosts and sponsors too), and
`<workspace>/skills-to-learn.md` (a room about a documented weak spot is remediation and
networking in one trip).

## The ranking idea

**Rank by impact: who is in the room, what the user leaves with, and whether they can actually
get in.** Not by attendee count, not by how fun it looks, not by how "tech" it sounds. A
five-person planning meeting where the user becomes a founding contributor outranks a
200-person mixer. A dull talk hosted inside a company that hires juniors outranks a great
hangout with no agenda.

## Hard kills — apply before ranking

1. **Not in person.** Online-only and virtual-only are dropped silently. Hybrid passes only if
   the in-person option is real: a physical address and an in-person RSVP path. A "hybrid" event
   that is a video call with a watch party is online.
2. **The user can't actually get in.** University career fairs are the main trap — most are
   restricted to that school's current students and alumni, so a fair at a school the user did
   not attend is usually a kill. Invite-only, members-only and affinity-restricted events need
   the admission path resolved before ranking. **Verify eligibility on the event's own page.**
   If it cannot be resolved, mark ELIGIBILITY UNVERIFIED and rank it below anything confirmed
   open.
3. **Outside the radius.** Default to what is reachable by the transit the user actually has,
   from where `profile.md` says they live. A longer trip is allowed only for a genuinely
   high-impact event, and then state the travel time and round-trip fare plainly so they can
   judge. If the user has no car, anything that requires one is dead.
4. **Ethics.** The RED list in `ghost.md` applies to hosts, sponsors and recruiting employers,
   not just to job postings. A career fair with a RED employer on the roster is not killed
   outright — name the employer and let the user decide.
5. **Scam-screen hiring events exactly like job postings.** Training-academy and
   bench-and-place outfits run "hiring events" as lead-gen. The shape to kill on: "no experience
   needed," a training program sitting between the attendee and the job, an employer roster that
   turns out to be one staffing firm, or a registration form that wants a resume before it names
   a single employer. See `skills/setup/references/examples.md`.
6. **Cost.** Free is the default expectation. Flag anything above the user's stated comfort
   threshold and kill anything well above it unless it is a top-tier event with a named employer
   roster. Ticket tiers matter — a conference may sell an expensive full pass while the
   hackathon day alone is free.

## Impact tiers

**T1 — hiring side in the room.** Recruiters, hiring managers or engineers from junior-hiring
companies are physically present and talking to them is the stated point. Job fairs with a
published employer roster, developer recruiting nights, company open houses, workforce-agency
hiring events.

**T2 — industry room plus structured content.** A talk, panel or workshop at a company office or
professional venue. The user leaves with knowledge, warm contacts, and sometimes a speaking
path. Structure is doing real work here: an agenda is both a reason to be in the room and a
script for being there.

**T3 — build something, artifact out.** Hackathons and hands-on workshops. Real impact when they
clear the gate — see the hardware rule.

**T4 — community access, compounding.** Small or founding groups where becoming a known face
pays off over months. Low immediate yield, high slope. A *planning* meeting is the standout
case: showing up to one makes the user a founding contributor rather than attendee #200.

**T5 — social, drinking-centered, pure mingle.** Low impact per hour and no artifact. Lower
priority, not killed. Surface at most one, one line, at the bottom, never above a T1–T4.

## Modifiers

**Up:** an explicit hiring or job-board segment in the published agenda (that is a T2 event
behaving like a T1) · hosted inside a company's office, so their engineers are in the room by
default · the group openly solicits speakers, which is a path to a talk and therefore a resume
line · the topic names the user's actual differentiator · the topic sits in the lane that has
converted for them before · a room about a documented interview weak spot · free · recurring
monthly, so a bad date is not a lost event.

**Down:** the venue's entire purpose is drinking · no agenda, no speaker, no stated activity ·
costs money · registration friction (building security pre-registration, photo ID, real-name
requirement) — not a kill, but **state it**, because it is a same-day blocker if unknown in
advance · restricted or ambiguous admission.

## The hardware rule — a factor, not a kill

Some users don't have a portable machine, or are saving for one. That is a note, not a gate.
Never kill a hackathon over it.

- **Always find and state the hardware line** from the event's own page: "bring your own
  laptop," "hardware provided," "no-code format," or "couldn't find it" — say which, every time.
- **Weight it, don't kill on it.** A bring-your-own-laptop event ranks below an equivalent one
  that doesn't need one. It still gets surfaced.
- **Lead time cuts in the user's favor.** An event two months out may land after the situation
  changes. State the date and let them do that math.
- Team formats where they could pair on someone else's machine are worth naming, honestly
  flagged as depending on strangers rather than sold as a solution.

## Run procedure

**STEP 1 — work the registry, and don't lean on one aggregator.** No single site sees the whole
city — event platforms are mutually invisible, so a Meetup-only run will miss everything that
lives on Luma and vice versa. The registry is built per city and lives in the workspace; seed it
at setup and add to it every run. The four layers that generalize:

| Layer | What to register | Notes |
|---|---|---|
| **A — aggregators** | Luma city feed (`lu.ma/discover/<city>/tech` and any local curator page), Meetup **Technology** (`categoryId=546`) *and* Meetup **Career & Business** (`categoryId=405`), any city tech calendar or university public calendar | Hit every layer-A source every run. Job fairs live under Career & Business, not Technology — do not skip it for the tech category |
| **B — venues and orgs** | Startup incubators, hardtech hubs, coworking spaces with public programming, and the **public workforce agency** for the county or city | Workforce-agency hiring events are free, open to the public and have no school gate — the most reliably attendable T1 source there is |
| **C — user groups** | The local chapter of the user's depth language, a cloud user group, the GDG chapter, ML/data groups | Consistently the best T2 events, because they rotate host offices — a different employer's engineers in the room each month. Watch registration cutoffs, which are often the morning of |
| **D — hackathons and fairs** | MLH, Devpost, hackathon aggregators, developer-recruiting-night organizers, ticketing sites filtered to career fairs | Verify the employer roster on the organizer's own page, and resolve the admission path for invite-only nights |

**STEP 2 — open the promising ones individually.** Aggregator listing pages omit venue, cost,
agenda and eligibility, and all four are ranking inputs. Mine the "you may also like" sidebar on
every event page opened — category filters are lossy, and related-event rails routinely surface
things the filter missed. Check the **host group's** city, not just the event's; groups from
other countries leak into local in-person feeds. Some calendars render only with JavaScript and
need a browser rather than a plain fetch.

**STEP 3 — kill-check, then rank.** Hard kills first, then tier, then modifiers. Cross-reference
hosts and recruiting employers against `ghost.md`.

**STEP 4 — write up.** Append everything found to `<workspace>/events.md` **including the kills
and why** — the kill log is what stops the next run re-chasing the same dead ends. Deliver a
short ranked list: top two or three with real detail, everything else one line.

Per event, always state: **what it is · date and time · exact venue and the route from home ·
cost · what they would walk away with · the catch.** The catch is not optional. If registration
closes hours before the event or the building locks, that goes in bold.

## Tone and boundaries

- **The user decides, always.** Never RSVP, never register, never sign them up.
- **Don't manage their schedule.** They know their own shifts and commitments; don't ask about
  them and don't suggest rearranging anything.
- **Don't be a cheerleader about networking.** Name what's in the room and what they'd get. They
  know what a meetup is.
- **Structure ranks higher because it produces more impact per hour**, not for any other reason.
  Let the ranking do that work; don't narrate it.
- One event surfaced as a real recommendation beats five surfaced as options.
