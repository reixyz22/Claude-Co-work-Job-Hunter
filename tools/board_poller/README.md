# board_poller

Poll company ATS boards directly and report only what is **new** since the last run.

Zero LLM tokens. Stdlib-only Python, no `pip install`.

## Why

Job-alert emails are a weak signal for mid-size employers — most of them either have
no alert feature or send a digest that is days stale. Their ATS board is the ground
truth, and nearly every ATS ships a JSON API behind the JavaScript shell that a plain
`WebFetch` sees as an empty page.

The keyword filter is the small half of this. The **diff** is the point. The poller
remembers every posting ID it has already seen, so each run surfaces only what appeared
since last time. That is what catches a posting a few hours old, which is the strongest
ranking signal this pipeline has.

## Supported without a browser

> **These endpoint shapes are unverified.** They were written from recall, not from
> vendor documentation, and no live call has been made against any of them. Treat the
> table as a starting hypothesis. `--add` probes for real before registering anything,
> which is why that step is not optional — it is where the guess gets tested.

| ATS | Endpoint | Confidence |
| --- | --- | --- |
| Workday | `POST /wday/cxs/<tenant>/<board>/jobs` | unverified; board name auto-probed |
| Greenhouse | `GET boards-api.greenhouse.io/v1/boards/<token>/jobs` | unverified |
| Lever | `GET api.lever.co/v0/postings/<company>?mode=json` | unverified |
| Ashby | `GET api.ashbyhq.com/posting-api/job-board/<org>` | unverified |
| UKG / UltiPro | `POST /<tenant>/JobBoardView/LoadSearchResults` | unverified, most fragile |

**Needs a headless browser, not implemented:** iCIMS, Taleo, SuccessFactors. These get
registered with `"skip": true` so they show up in `--list` as a known gap rather than
silently disappearing.

## Two design choices worth knowing

**Facets are recorded but not applied.** Your filtered URL carries facet IDs like
`jobFamilyGroup=50411073...`. Those keys and IDs differ per tenant, and a wrong one
returns an empty board — indistinguishable from a company with nothing open. So the
poller pulls the *whole* board and filters titles locally. Your URL is only used to
derive the tenant and board name. Set `"use_facets": true` on an entry to opt back in.

**An empty result counts as a failure, not a pass.** During `--add` and `--verify`, a
board that responds with zero postings is reported as FAIL. A silent zero is the exact
signature of a wrong board name, and treating it as success is how you end up trusting
a board that has been dead for a month.

## Workflow

Filter the company's board in your own browser until the results look right, copy that
URL, and hand it over. Every field is derived from the URL — you never hand-edit the
registry.

```bash
# 0. offline sanity check — parsing and title filtering, no network
python3 test_poll_boards.py

# 1. register a board. This PROBES the endpoint for real and refuses to
#    register if nothing answers. For Workday it walks every plausible board
#    name and keeps whichever one returns postings.
python3 poll_boards.py --add "https://acme.wd1.myworkdayjobs.com/Search?jobFamilyGroup=abc123"

# 2. re-check a board any time
python3 poll_boards.py --verify acme

# 3. first run seeds the baseline — everything currently posted counts as "seen"
python3 poll_boards.py --run

# 4. every run after that reports only what is new
python3 poll_boards.py --run
```

Other commands:

```bash
python3 poll_boards.py --list           # what is registered
python3 poll_boards.py --run --all      # ignore the seen-store, re-report everything
python3 poll_boards.py --add "<url>" --name wintrust-tech    # custom registry key
python3 poll_boards.py --add "<url>" --no-probe              # register blind (not advised)
```

## Tests

`test_poll_boards.py` is stdlib `unittest`, no network, 17 cases covering URL parsing
across all five ATS shapes plus the title filter's edge cases — including the trap where
"Senior Associate Engineer" must lose to the seniority rule despite containing
"associate", and where `\bii\b` must not match inside "Hawaii".

Live endpoint behaviour is deliberately **not** covered and cannot be faked usefully.
`--add` and `--verify` are the live tests.

## Output

Two files, both regenerated every run:

- `new-postings.json` — structured, for a downstream agent to read
- `new-postings.md` — human-readable, for you

Postings land in one of two buckets:

- **junior** — title matched a junior signal (`junior`, `jr`, `entry`, `associate`,
  `new grad`, `graduate`, `early career`, `apprentice`, `Engineer I`, …)
- **watch** — a plain engineering title with no seniority marker either way

Anything matching a seniority term (`senior`, `sr`, `staff`, `principal`, `lead`,
`manager`, `director`, `architect`, `II`, `III`, …) is dropped. **Negative terms beat
positive ones**, so "Senior Associate Engineer" is correctly filtered out rather than
caught by the `associate` rule.

Tune the term lists at the top of `poll_boards.py` — they are plain regex lists.

## Scheduling

Run it on a cron or Task Scheduler a few times a day. Point your agent at
`new-postings.md` instead of having it search job boards. Collection then costs nothing,
and the agent only ever reads the diff.

```
# every weekday at 05:45, 10:00 and 15:00
45 5,10,15 * * 1-5  cd /path/to/board_poller && python3 poll_boards.py --run
```

## Files

| File | Purpose |
| --- | --- |
| `poll_boards.py` | the poller |
| `registry.example.json` | documented example — copy to `registry.json` |
| `registry.json` | your board list (gitignored) |
| `seen.json` | posting IDs already reported (gitignored) |
| `new-postings.json` / `.md` | latest diff (gitignored) |

Paths can be overridden with `BOARD_REGISTRY`, `BOARD_SEEN`, `BOARD_OUT` and
`BOARD_OUT_MD`.

## Being a good citizen

Requests carry a descriptive User-Agent, and each **host** is called serially with a
`HOST_DELAY` gap (default 0.4s) between its requests. Different hosts are polled
concurrently. These are public endpoints that the companies' own career pages call, but
do not hammer them — a few runs a day is plenty, and more would not surface anything
sooner.

### Why it is parallel (reworked 2026-10-23)

The original model slept 1.5s after *every* board, serially. That was fine at 20 boards
and fatal at 79: 1.5s x 77 eligible boards is ~118s of pure sleeping before a single byte
of network time, which put a clean run permanently past the 120s shell timeout the
scheduled sweeps invoke this tool through. The poller had stopped being able to finish at
all — two sweeps (2026-10-14 and 2026-10-23) recorded it as an execution failure, and the
2026-10-23 sweep reported it as the instrument "failing to run as well as failing to
produce."

The registry spans only a handful of vendor API hosts (35 Greenhouse boards share
`boards-api.greenhouse.io`, 23 Ashby boards share `api.ashbyhq.com`), so the correct
politeness unit is the host, not the run. Boards now fetch through a thread pool that
serializes per host and runs hosts in parallel. **Measured: 27s for 77 boards, down from
a run that could not complete.**

| Flag | Env | Default | What it does |
|---|---|---|---|
| `--workers N` | `BOARD_WORKERS` | 8 | Concurrent fetch workers |
| `--budget SEC` | `BOARD_BUDGET` | 90 | Wall-clock ceiling on the fetch phase |
| — | `BOARD_HOST_DELAY` | 0.4 | Seconds between calls to the *same* host |

`--budget` is a guard against the same failure returning as the registry grows. Boards
that have not returned by the deadline are cancelled and reported as timeout errors, and
the run still writes its outputs — **partial results beat being killed and writing
nothing.** If timeout errors start appearing, that is the signal to raise `--workers` or
split the registry, not to raise the budget past the caller's own limit.

## Rippling (added 2026-09-12)

```
https://api.rippling.com/platform/api/ats/v1/board/{tenant}/jobs
```

`{tenant}` is the slug in the careers URL: `ats.rippling.com/<tenant>/jobs`. Public, no auth.
Returns a bare JSON array, one object per open req: `uuid`, `name`, `department`, `url`, `workLocation`.

**No posting date in the payload.** `posted` comes back empty for every Rippling req, so age
can only come from the `seen.json` diff -- a req reads as new on the first run after it appears,
and a board registered today tells you nothing about how long its existing reqs have been open.
Register Rippling boards early; the freshness signal only starts accruing once they are in.

**Tenant slugs are not guessable, so probe before registering.** `loop` and `loop-careers` are two
unrelated companies on this ATS (the first is the US AI/logistics one, the second a Toronto
fintech). Pull the board and read a few titles before adding it.
