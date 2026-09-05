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

There is a 1.5s delay between requests and a descriptive User-Agent. These are public
endpoints that the companies' own career pages call, but do not hammer them — a few runs
a day is plenty, and more would not surface anything sooner.
