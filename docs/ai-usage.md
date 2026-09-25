# AI Usage

The design was produced in a conversation with an AI coding assistant (Claude Code). I owned the questions, the decisions and the corrections; the assistant drafted explanations, options and documents.

## How AI was used: the mechanism

1. **Rules the assistant must follow** (`CLAUDE.md`): every decision quotes the sentence of the brief that forces it; anything the brief does not state is written down as an assumption; recorded decisions are changed only with a logged reason; the assistant never commits.
2. **Decision log as shared memory** (`decisions.html`): each decision is recorded as context → options → decision → consequences, so work continues across sessions without relying on chat history.
3. **Review against external practice** (`review-checklist.md`): the assistant researched established practice (online migrations, FMEA, observability in design docs, LLM evaluation), turned it into a per-section checklist, and reviewed the design against it. I accepted or rejected each finding; accepted changes are logged (D6).
4. **Human gate:** the assistant proposes and explains; I decide. Nothing enters the design without that decision.

## Where AI helped

- Reading the brief and turning each constraint into a candidate decision, with the quote that forces it.
- Laying out options and their costs per decision, and drafting the decision log and the design document.
- Spotting production concerns early: lost updates (writing our tables in the same transaction as the engagement change), stale overwrites during the backfill (revision check), per-firm load control.
- Finding a day-one gap: `template_releases` only learned about versions published after launch, so engagements already behind would have shown "Up to date". Fixed by copying the existing versions once at launch.
- Arguing me out of a bad idea: I wanted to block unverified engagements during the backfill; it pointed out that this would stop users' daily work, and that opening an engagement is what verifies it.

## Where I corrected or ignored it

- **Wrong model of the data.** It first described a firm's engagements as all using one template; the brief says "across many different products", and each engagement can be on a different version.
- **Over-engineering (D1, D3, D5).** It proposed a per-firm copy of the published-versions table (it holds no client data, so one shared table is enough), an outbox plus an event processor on the firm side (removed: our tables share the firm's database and are written in the same transaction), and a summary reference in the decision log (removed: summary revisions are dated, so the dates already tell which one a decision saw).
- **Invented numbers (D6).** It wrote a p95 latency target and alert thresholds (15 min, 24 h, 7 days, 99%) that the brief never gives. Removed; thresholds are set during the pilot.
- **Observability that measured the wrong thing (D6).** Its first version watched whether components were running (latency, queue age, the summary check passing), not whether they were right. Rewritten around correctness: a *spot check* that opens a few random engagements and compares their real version with what the list shows, and content-team grading of summaries for completeness, faithfulness, clarity and neutrality.
- **Scope of the security requirement (D2).** Its first answer covered where the data is stored; re-reading "whatever tracks and surfaces that state" extended isolation to events, backfill, API, logs and metrics.
- **Summary generation (D5).** It proposed deterministic per-change-type rules plus an LLM; I rejected the rules because we do not know the template schema, keeping only the obvious deterministic check (citations and coverage).
- **Decline semantics (D4).** The walk-back flow (decline the latest, get offered the previous version) and the "from" column in the decision history came from me.
- **Presentation checked as a reviewer would see it (D7).** A final read of the rendered submission found what the text alone hid: the PDF had spilled onto a 4th page, sections 4–5 used internal names no outside reader would know ("drift check", "reconciliation"), and one example contradicted the rule it illustrated (it said a single summary covered two versions). Fixed and logged (D7): plain names defined once, the example corrected, the page limit restored.
- **Code that passed its own tests but was wrong (D7).** The Part 2 slice was drafted by the assistant, test-first, and all 26 tests passed. A review of the code against the decision log found two places where it had drifted from rules already recorded: it stored its own revision counter instead of the engagement's, so a late backfill reading could move an engagement back a version; and it declined any version published while the user had the review open, without the user ever seeing it. Both were reproduced with failing tests before being fixed. The random-history test had missed them because it only simulated what the assistant had thought of (publications and decisions), not plain saves, late readings or publications during a review.
- **Readability.** Several sections came out as jargon (the opening problem statement, test cases instead of a strategy, tradeoffs like "compute on read over push on publish"); I had them rewritten so a reader outside the conversation can follow them.

## How I would guide other engineers using AI on this system

- **Start every session from the brief and the decision log**, and require each change to quote the requirement behind it; anything unquoted is written down as an assumption or dropped.
- **Ask where every number comes from.** The assistant fills gaps with confident, invented figures; each one must trace to the brief, a measurement or an explicit assumption.
- **Let invariants check AI-written logic, and check what the invariants simulate.** The pending-update rule is a pure function ([`implementation/`](../implementation/)) with a test that replays 500 random histories and checks that an engagement never moves back and no version is declined unseen; an AI-written change ships only if these tests pass. Passing is not enough on its own: the test only covers the events it generates, so a reviewer checks that list against how the real system behaves (see the correction above).
- **Treat prompt and model changes as code.** A change to the summary generator ships only if the graded set of past releases does not get worse.
- **Human review for isolation, residency and the backfill.** AI may draft them, but a person reviews them, the negative isolation tests must pass, and the backfill runs first on a copy of a pilot firm.
- **No client data in AI tools.** Use template content or synthetic engagements when working with an assistant.

## Where AI should not be trusted in this domain

Working on this design, these are the places where the assistant's output could not be taken as it came:

- **Facts about Caseware's systems.** It states how the template store, the diff or the engagement system behave with the same confidence whether the brief says so or not (for example, that versions are numbered in order, or that the store can list them). Each such statement must be checked against the brief and, if it is not there, recorded as an assumption.
- **Numbers.** Latency targets, alert thresholds, sizes: it produces plausible figures with no source. None is accepted without a source, a measurement or an explicit assumption.
- **Security and isolation.** It defaulted to application-level filtering and to where the data is stored; the brief asks for structural isolation of everything that tracks and surfaces the state. This needs human reasoning and negative tests.
- **Whether the design is complete.** It declared decisions closed before the end-to-end flow was worked through, and it used a component in the observability section (the count of engagements affected by a new version) that the architecture never defined; a final read showed monitoring jobs still missing from the component table and the diagram. Completeness is checked by walking each flow, not by how finished the text looks.
- **What "working correctly" means.** Its first monitoring measured whether components were running, not whether their output was right. What counts as correct (for example, what makes a summary good) has to be defined by people who know the domain.
- **Its own tests as proof that its code is right.** Tests written by the same assistant share its blind spots: the slice's random-history test passed while two recorded rules were broken, because it never generated the events that break them. Tests prove what they exercise; a person checks what they exercise.
- **Whether an addition is worth it.** It proposes reasonable-sounding extras (an outbox, a per-firm copy of shared data, an extra field in the decision log) without weighing their cost; each one has to justify itself against the brief.
