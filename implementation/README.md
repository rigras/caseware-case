# Part 2 — The pending-updates rule

## What this slice is

The core rule of the design: given the row we keep for an engagement (`engagement_versions`) and the versions published for its template, what the list shows, what the review offers, and how a decision or a backfill reading changes the row. Everything else in the design (the API, the engagement hook, the backfill job) calls into this rule; it is where a mistake would show the wrong updates to every firm.

| Function | Answers | Design reference |
|---|---|---|
| `list_status` | *Up to date*, *N updates pending*, *Verifying…*, *error* or *archived* for one engagement | design §1 "At a glance", "What counts as pending" |
| `review` | Which versions the user can apply up to (latest first, then walking back) and which summaries to show, marking *previously declined, would be included* | design §1 "Accumulated versions", D4 |
| `decide` | The new row and the `decision_log` entry after apply / decline. Takes the latest version the review showed (`reviewed_up_to`) and the engagement's own revision after the save; rejects anything that was not on offer | design §1 "History", D4, D1 |
| `record_observation` | Stores the version read by loading an engagement (backfill or a user opening it), ignoring readings older than what the row holds | design §2 step 3, D1 |
| `check_citations` | Whether a generated summary cites every change in the diff and invents none (the *ID check*) | design §1 "Summary generation", D5 |

## Why it is built this way

- **Pure functions over plain values, no database.** The rule can be read, tested and reasoned about on its own; the brief asks Part 2 to "focus on interfaces, contracts, and correctness". The callers own the I/O and the transaction.
- **Two numbers per engagement instead of a list of declined versions.** Versions are cumulative (assumption 5), so `current` and `declined_up_to` are enough: pending = published versions above both. Nothing grows with the number of publications.
- **The engagement's own revision decides which write wins.** A backfill load takes ~1 minute; a user may apply an update in that minute. Every write carries the engagement's revision and an older one is ignored (D1). The revision must come from the engagement itself: plain saves never reach our table, so a counter kept by us falls behind and a late reading could win.
- **`reviewed_up_to` comes from the review screen, not from the database at click time.** A version published while the user has the review open stays pending instead of being declined unseen.

## How we know it works

```
cd implementation
python -m pytest -v        # Python 3.10+, pytest: 32 passed
```

- **Example tests**: the worked example of design §1 end to end, walk-back offers, re-offers after a decline, unverified rows never shown as *Up to date*, versions that are not on offer rejected, stale and archived readings ignored, the ID check.
- **Random histories**: one test replays 500 random interleavings of publications (also while a review is open), plain saves, decisions, and backfill readings arriving late with an old revision. After every step it checks that an engagement never moves back a version, that exactly the versions nobody has reviewed are pending, and that no version is ever skipped without the user having seen it.
- **The tests catch real mistakes**: reintroducing either of the two defects found in the code review (see D7 in `docs/decisions.html`) makes the suite fail, including the random-history test on its own.
