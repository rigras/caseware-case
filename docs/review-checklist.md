# Design Review Checklist

Used to review `design.md` sections 2–5. The AI assistant built it from established practice (sources below); each finding it produced was accepted or rejected by me, and accepted changes are logged in `decisions.html` (D6).

## 2. Implementation Plan
- [x] Online-migration order: create tables → capture new changes → copy existing state (backfill) → verify → switch users over.
- [x] Each phase ships on its own and has a "done when".
- [x] Cheap, explicit rollback (per-firm flag; additive changes only).
- [x] Gradual rollout: pilot, then waves.
- [x] Size and time of the expensive step (backfill) estimated.
- [x] What can run in parallel is stated.

## 3. Testing Strategy
- [x] Every component is covered at strategy level, with a pass criterion from the brief or the design.
- [x] The brief's explicit scenario (accumulated updates) is a named test.
- [x] Backfill tested under failure (retries, resume).
- [x] Negative security tests (firm isolation).
- [x] Performance criterion taken from the brief (no engagement loaded; time does not grow with firm size), not an invented number.
- [x] LLM: golden set, rubric, and a gate on prompt/model changes.

## 4. Evaluation & Observability
- [x] Answers the brief's three observability questions literally.
- [x] Alerts map to a user-visible effect; thresholds are set in the pilot, not invented.
- [x] AI output evaluated in three layers: offline (golden set), per output (automatic check), production (sampling, user flags, alarm on regression).

## 5. Failure Modes & Tradeoffs
- [x] Per failure: effect, detection, mitigation (lightweight FMEA).
- [x] No absolutes ("impossible"); state the assumption it depends on.
- [x] Covers AI and migration failures, not only infrastructure.
- [x] Tradeoffs state what is given up, including LLM vs. rule-based.

## Cross-cutting
- [x] ≤ 3 pages; each term defined once and used consistently.

## Sources
- Expand/contract and online backfills: https://thebackenddevelopers.substack.com/p/zero-downtime-database-migrations
- Stripe's online data migrations (dual writes, verification, cutover): https://arpitbhayani.me/videos/how-stripe-achieves-zero-downtime-consistent-data-migrations-at-scale
- Shadow tables for migrations: https://www.infoq.com/articles/shadow-table-strategy-data-migration/
- Observability in design docs: https://adhdecode.com/observability/sre-practices-and-observability/observability-review-design-docs-requirements/
- FMEA (severity, occurrence, detection): https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis
- LLM evaluation in production (offline, reference-free, monitoring): https://dev.to/nazar-boyko/evaluating-llm-output-quality-in-production-39an
- Golden datasets: https://langfuse.com/resources/engineering/golden-dataset-evaluation
