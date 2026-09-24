# Caseware — Take-Home: pending template updates

Design exercise (2–3 h, "do not over-optimize"): a system that shows which engagement files have
pending product-template updates and a human-readable summary of the inbound changes.
Brief: `Take-Home_Refactoring_Team_Design_Exercise.pdf`.

## Repo map

- `Take-Home_Refactoring_Team_Design_Exercise.pdf` — the brief; source of truth for scope
- `docs/decisions.html` — decision log (D-N, lightweight ADRs) agreed during design sessions
- `docs/design.md` — the deliverable: 1–3 pages covering the brief's 5 sections
- `docs/ai-usage.md` — where AI helped and where it was corrected

## Rules

1. No decision lives only in chat: every agreed decision is recorded in `docs/decisions.html`
   (context → options → decision → consequences, including the negative ones).
2. Every decision quotes the sentence of the brief that forces it. No quote = invented scope.
   Anything the brief does not state is recorded as an explicit **assumption**.
3. Recorded decisions are not silently reopened: a change is logged, with its reason, in the
   same record.
4. Proportional ceremony: the deliverable is a 1–3 page document, not a full technical spec.
   Use an LLM only where reasoning adds value; keep everything else deterministic.
5. Never invent template content: every human-readable summary must trace back to the real
   JSON diff.
6. Code (Part 2, optional): TDD; evidence that it works is test output, not claims.
7. The assistant does not run `git add`/`commit`/`push` unless explicitly asked at that moment.
8. Everything committed to this repo is in English.
