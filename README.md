# Caseware Take-Home — Pending Template Updates

A design for showing which engagement files have pending product-template updates, with a human-readable summary of the inbound changes, without ever loading an engagement while the user waits.

## Where everything is

| What | Where | Notes |
|---|---|---|
| **Design document** (Part 1: the brief's 5 sections, 3 pages) | [`docs/design.pdf`](docs/design.pdf) | Source: [`docs/design.md`](docs/design.md) |
| **Architecture diagram** | [`docs/architecture.svg`](docs/architecture.svg) | Also embedded in the design document |
| **Flow diagrams**: user journey, worked example, sequence diagrams (publish, open the list, apply/decline), backfill, row lifecycle, summary generation, observability | [`docs/flows.pdf`](docs/flows.pdf) | Source: [`docs/flows.md`](docs/flows.md) (Mermaid; also renders on GitHub) |
| **Code** (Part 2: the pending-updates rule, with tests) | [`implementation/`](implementation/) | What it does, why it is built that way and how it is verified: [`implementation/README.md`](implementation/README.md) |
| **Decision log**: context, options, decision, consequences and assumptions, each tied to a quote from the brief | [`docs/decisions.html`](docs/decisions.html) | Open in a browser |
| **AI usage**: how AI was used, where it helped, where it was corrected (each correction points to its decision), how to guide others, where not to trust it | [`docs/ai-usage.md`](docs/ai-usage.md) | Review checklist used: [`docs/review-checklist.md`](docs/review-checklist.md) |
| Brief | [`Take-Home_Refactoring_Team_Design_Exercise.pdf`](Take-Home_Refactoring_Team_Design_Exercise.pdf) | |

## Suggested reading order

1. `docs/design.pdf`: the design.
2. `docs/flows.pdf`: the same design, step by step.
3. `implementation/`: the core rule in code, with its tests.
4. `docs/decisions.html` and `docs/ai-usage.md`: why each choice was made, and how AI was used and checked.

## Running the tests

```
cd implementation
python -m pytest -v        # Python 3.10+ and pytest; 32 tests
```
