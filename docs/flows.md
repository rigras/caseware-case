# Flows

How the design in [`design.md`](design.md) behaves, step by step. Terms, tables and components are the ones defined there; decisions are referenced as D-N ([`decisions.html`](decisions.html)). Diagrams are Mermaid and render on GitHub.

1. [What the user sees](#1-what-the-user-sees)
2. [User journey: reviewing pending updates](#2-user-journey-reviewing-pending-updates)
3. [Accumulated updates, worked example](#3-accumulated-updates-worked-example)
4. [A new version is published](#4-a-new-version-is-published)
5. [A user opens the engagement list](#5-a-user-opens-the-engagement-list)
6. [A user applies or declines](#6-a-user-applies-or-declines)
7. [Backfill of existing engagements](#7-backfill-of-existing-engagements)
8. [Lifecycle of an engagement's row](#8-lifecycle-of-an-engagements-row)
9. [Summary generation](#9-summary-generation)
10. [Observability jobs](#10-observability-jobs)

---

## 1. What the user sees

Illustrative wireframe: screen design is not part of the brief, and the summary text below is made up for layout only (real summaries come from the JSON diff, §9). The statuses are the three defined in design §1.

```text
 Engagements — Firm ABC
 ┌──────────────┬────────────────┬─────────┬─────────────────────┐
 │ Engagement   │ Template       │ Version │ Template updates    │
 ├──────────────┼────────────────┼─────────┼─────────────────────┤
 │ Smith 2026   │ Audit Canada   │ v3      │ ● 2 updates pending │
 │ Jones 2026   │ Audit Canada   │ v5      │ ✓ Up to date        │
 │ Brown 2026   │ —              │ —       │ ⏳ Verifying…        │
 └──────────────┴────────────────┴─────────┴─────────────────────┘

 Review — Smith 2026 (v3 → v5)                       [AI-generated]
   What v4 changed   · Procedure "Lease review": new step added (C1)
                     · Checklist "Going concern": question reworded (C2) ⟲ changed again in v5
   What v5 changed   · Checklist "Going concern": question removed (C1)
                                        [ Apply up to v5 ]   [ Decline ]
```

## 2. User journey: reviewing pending updates

```mermaid
flowchart TD
    A["User opens the engagement list"] --> B{"Status of each engagement<br/>(computed from our tables, no file loaded)"}
    B -->|"Up to date"| Z["Nothing to review"]
    B -->|"Verifying…"| V["Engagement stays fully usable;<br/>status appears once its version is recorded<br/>(backfill, or the user opening it)"]
    B -->|"N updates pending"| W{"Summaries ready?"}
    W -->|"No"| X["Shows <i>Summary in preparation</i>;<br/>review opens once they are ready"]
    W -->|"Yes"| C["Open the review"]
    C --> D["Read one summary per pending version, oldest first<br/>marks: <i>changed again</i>, <i>previously declined, would be included</i>"]
    D --> E{"Apply up to vK?<br/>(K starts at the latest)"}
    E -->|"Apply"| F["Apply up to vK"]
    E -->|"Decline"| G{"Is a version older than vK<br/>still pending?"}
    G -->|"Yes: offer vK-1"| E
    G -->|"No"| H["Decline all"]
    F --> I["Recorded once, in the same transaction:<br/>current = K (if applied)<br/>declined-up-to = latest reviewed<br/>decision_log += who, when, from, to"]
    H --> I
    I --> J["List shows Up to date until a newer version is published"]
```

Walking back is the only valid order: versions are cumulative, so v5 cannot be applied without v4, but an engagement can stop at v4 (D4). The walk-back steps are UI only; the decision is one event.

## 3. Accumulated updates, worked example

The example from design §1. Pending = published versions newer than both the version the engagement is on and the highest version already declined (written *floor* below).

```mermaid
flowchart LR
    S1["<b>current v3</b> · declined-up-to —<br/>published: v4, v5<br/>floor v3 → <b>2 updates pending</b>"]
    S2["<b>current v4</b> · declined-up-to v5<br/>floor v5 → <b>Up to date</b>"]
    S3["v6 published<br/>floor v5 → <b>1 update pending</b><br/>summaries shown: v5 (<i>previously declined,<br/>would be included</i>) and v6"]
    S4a["Apply v6<br/><b>current v6</b> → Up to date<br/>(v5's changes come in too)"]
    S4b["Decline<br/>declined-up-to v6 → Up to date<br/>(v5, v6 not offered again)"]
    S1 -->|"decline v5,<br/>apply v4"| S2
    S2 -->|"content team<br/>publishes v6"| S3
    S3 --> S4a
    S3 --> S4b
```

## 4. A new version is published

One row and one summary per release, however many firms use the template. No firm database is touched and no engagement is loaded.

```mermaid
sequenceDiagram
    autonumber
    actor CT as Content team
    participant TS as Template store (existing)
    participant Q as Queue
    participant RP as Release processor
    participant SG as Summary generator
    participant SH as Shared tables<br/>template_releases · release_summaries
    CT->>TS: Publish "Audit Canada" v5
    TS->>Q: TemplateVersionPublished(template, v5) — listener hook
    Q->>RP: Deliver (retried until acknowledged)
    RP->>SH: Insert template_releases row (a repeated message adds nothing)
    Note over SH: From here on, every engagement below v5<br/>shows it as pending on its next list read
    RP->>SG: Request summary v4 → v5
    SG->>SH: Store summary (status: in review)
    CT->>SH: Approve (every summary at launch, sampled later)
    Note over SH: Users see the text once approved.<br/>Until then: "Summary in preparation"
```

Step 6 is expanded in [§9](#9-summary-generation). A lost message is caught by the version check ([§10](#10-observability-jobs)).

## 5. A user opens the engagement list

```mermaid
sequenceDiagram
    autonumber
    actor U as Auditor at Firm ABC
    participant UI as Engagement list screen
    participant API as Pending Updates API<br/>(in the firm's region)
    participant F as Firm ABC database<br/>engagement_versions
    participant SH as Shared tables<br/>template_releases · release_summaries
    U->>UI: Open the list
    UI->>API: GET pending updates (session token)
    API->>API: Firm taken from the token, never from the request
    API->>F: Read engagement_versions (credentials scoped to Firm ABC)
    API->>SH: Read published versions of those templates
    API->>API: Per engagement: floor = max(current, declined-up-to)<br/>pending = versions above floor<br/>filtered by existing per-engagement permissions
    API-->>UI: Up to date · N updates pending · Verifying…
    Note over API,F: A database query: no engagement file is loaded,<br/>response time does not grow with firm size
```

## 6. A user applies or declines

Also covers create, open and archive: the same hook, inside the engagement management system, writes our tables in the firm's own database.

```mermaid
sequenceDiagram
    autonumber
    actor U as Auditor
    participant EMS as Engagement management system<br/>+ engagement hook
    participant F as Firm database<br/>engagement + engagement_versions + decision_log
    U->>EMS: Apply up to v4 (reviewed up to v5)
    EMS->>EMS: Check existing per-engagement permission
    EMS->>F: BEGIN
    EMS->>F: Engagement change (applying content is out of scope)
    EMS->>F: engagement_versions: current = v4, declined-up-to = max(old, v5), new revision
    EMS->>F: decision_log: append (who, when, from v3, applied v4, reviewed up to v5)
    alt Every write succeeds
        EMS->>F: COMMIT
        EMS-->>U: Done, list shows Up to date
    else Any write fails
        EMS->>F: ROLLBACK
        EMS-->>U: Apply/decline fails, nothing half-recorded
    end
```

| Action | Effect on `engagement_versions` |
|---|---|
| Create | Row inserted: template, version, *verified* |
| Open | Version recorded for free (the load was already paid by the user); *verified* |
| Apply / decline | As above, plus a `decision_log` entry |
| Archive | Status *archived* (kept, so a late backfill write cannot bring it back) |

## 7. Backfill of existing engagements

The backfill fills `engagement_versions` for the engagements that existed before launch. It runs once per firm, in the firm's region, with that firm's credentials. Each load takes about a minute, so it goes slowly on purpose and must never slow users down.

```mermaid
flowchart TD
    A["1 · Inventory (cheap)<br/>list the firm's engagements, one row each: <i>Verifying…</i>"] --> B["2 · Pick the next <i>Verifying…</i> engagement<br/>recently opened first"]
    B --> C["3 · Wait for a load slot<br/>limits per region and per firm · mostly off-hours"]
    C --> D["4 · Load it without changing it (~1 min)<br/>read template, version and revision"]
    D -->|"loaded"| E["5 · Save it if its revision is newer than the row's<br/>row becomes <i>Verified</i>"]
    D -->|"failed 3 times"| F["Row becomes <i>error</i> + alarm<br/>never shown as Up to date"]
    E --> G{"More <i>Verifying…</i><br/>rows?"}
    F --> G
    G -->|"yes"| B
    G -->|"no"| H["Firm done"]
```

An engagement the user has created, opened or decided on is already *Verified* by the hook, so the backfill never picks it.

**A reading can arrive late; it does no harm.** In the minute a load takes, the user may apply an update. Every write carries the engagement's own revision number, and a write older than the one the row holds is ignored:

```mermaid
sequenceDiagram
    participant B as Backfill job
    participant E as Engagement management system<br/>+ hook
    participant T as engagement_versions
    actor U as User
    B->>E: Start loading the engagement (~1 min)
    Note over B,E: It reads v3, revision 12
    U->>E: Apply v4
    E->>T: v4, revision 13 (same transaction as the apply)
    B->>T: One minute later: v3, revision 12
    Note over T: 12 is older than 13: ignored, the row stays on v4
```

Order of rollout (design §2): the hook and the template-store listener are switched on **before** the backfill, so any change made while it runs is already captured.

## 8. Lifecycle of an engagement's row

Each engagement has one row in `engagement_versions`, in one of four states. *Up to date* and *N updates pending* are not states: they are computed from a *Verified* row every time the list is read.

```mermaid
flowchart LR
    N(["New engagement<br/>created"]) --> V
    X(["Existing engagement,<br/>found by the backfill"]) --> Q
    Q["<b>Verifying</b><br/>list shows: <i>Verifying…</i>"] -->|"loaded by the backfill<br/>or opened by a user"| V["<b>Verified</b><br/>list shows: <i>Up to date</i><br/>or <i>N updates pending</i>"]
    Q -->|"3 failed loads"| E["<b>Error</b><br/>list shows: <i>error</i>"]
    E -->|"opened by a user"| V
    V -->|"archived"| A["<b>Archived</b><br/>not listed"]
```

Apply, decline and open keep a row *Verified* and update it. An engagement can be archived from any state; the row is kept, not deleted, so a late backfill reading cannot bring it back.

## 9. Summary generation

One summary per new version, comparing it with the previous version, written once for every firm. Steps 1–4 run automatically when the version is published; step 5 is a person. The LLM only ever sees Caseware template content, never firm data.

```mermaid
flowchart TD
    A["1 · Diff tool compares v4 → v5<br/>each change gets an ID: C1, C2…"] --> B["2 · Add context: only the parts of v4 those changes touch"]
    B --> C["3 · LLM writes the summary, citing the change IDs<br/>never recommends apply or decline"]
    C --> D["4 · ID check (code): every change cited, no invented ID<br/>if it fails: one retry, then human review"]
    D --> E["5 · <b>Human gate:</b> the content team reviews it<br/>every summary at launch, a sample later<br/>an edit is saved as a new dated revision"]
    E --> F["6 · Users see it, labelled AI-generated<br/>until then: <i>Summary in preparation</i>"]
```

The same flow on a made-up change (illustration only; real content always comes from the diff):

| Step | Example |
|---|---|
| 1 · Diff | `C1`: a step was added to procedure 12 |
| 2 · Context | procedure 12 is titled "Lease review" |
| 3 · Summary | Procedure "Lease review": new step added (C1) |
| 4 · ID check | C1 is cited and nothing else is: passes |

*Changed again* marks are not part of generation: when a review shows several versions, code compares the paths each version changed and marks the items changed in more than one.

## 10. Observability jobs

Three jobs check that the system is right, not only that it is running: the version check and the spot check run on a schedule, the impact count after each publish. They run in each region with firm-scoped credentials, and only counts leave the region.

```mermaid
flowchart TB
    subgraph VC["1 · Version check"]
        direction LR
        V1["Versions in the<br/>template store"] --> V2{"All of them in<br/>template_releases?"}
        V2 -->|"no"| V3["Add the missing version + alarm<br/>(otherwise engagements show Up to date wrongly)"]
    end
    subgraph IC["2 · Impact count"]
        direction LR
        I1["New version<br/>published"] --> I2["Per firm: engagements it leaves<br/>pending, and still <i>Verifying…</i>"] --> I3["Dashboard<br/>a firm missing → alarm"]
    end
    subgraph SC["3 · Spot check"]
        direction LR
        S1["A few random<br/>engagements per firm"] --> S2["Load each in the<br/>background (~1 min)"] --> S3{"Real version = what<br/>the list shows?"}
        S3 -->|"no"| S4["Mismatch + alarm<br/>(must be 0)"]
    end
    VC ~~~ IC ~~~ SC
```

| Brief question | Answered by |
|---|---|
| How many engagements a new update affects | Impact count, per firm and region |
| Whether the check is running for every firm | A firm missing from the impact count or with no spot-check result; backfill progress |
| A firm's history of apply/decline decisions | `decision_log` (who, when, from, to): a query, not a job |
