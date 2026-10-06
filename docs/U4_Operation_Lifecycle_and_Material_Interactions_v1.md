# U4 common operation lifecycle and material interactions

Version 1.0 · 21 September 2026

U4 is the native paid executor for the common object architecture. It consumes exact revisions and actor-accessible inputs, retains interrupted work, checks physical dependencies before committing effects, and creates evidence that can be delivered and processed later. Its fixed workshop semantics and prices are engineering choices under `u4.finite-workshop-v1`. Integrated Model A, Fool's Memory and Crux realization remains U5.

## Authoritative components

| Component | Responsibility |
| --- | --- |
| `operation_records.py` | Immutable request shape, registered primitive signatures, fixed finite costs and world-contract identity. |
| `operations.py` | One common start / advance / commit / cancel lifecycle; finite actor budgets; exclusive reservations; command identity; observation and processing integration; replay. |
| `material.py` | Supported physical transformations and atomic material validation in `OperationStore`, which extends `CompactStore`. |
| `operation_audit.py` | Independent offline fold of raw transactions, reconstructing resource charges, stock sinks, reservations and physical consequences without executor caches. |
| `u4.py` | Public native U4 imports. |

Every job, budget, receipt, observation, actual event and changed material is an ordinary versioned object. Private service indexes locate current jobs, wallets and reservations; immutable transactions are authoritative. Checkpoint restoration reconstructs those indexes by deterministic command replay. No second material writer is introduced.

Three inherited files receive explicit extension points: `records.py` adds the paid-material lineage category; `store.py` delegates that category to a validator which rejects it in the base U2/U3 store; and `particulars.py` makes backend and receipt-authority selection class-specific. Existing U2/U3 wire values, schemas and behavior retain their meanings. `NativeAccess` admits the native paid receipt writer, while ordinary U3 `AccessLedger` keeps its original imported-receipt writer. The complete frozen R21B source remains unchanged.

## Operation contract

| Contract element | Retained representation and enforcement |
| --- | --- |
| Actor and participants | Exact actor identity plus enumerated participant identities in the job. A transfer recipient must be a declared participant. |
| Input revisions | Target, tool, stock, procedure, relation, draft and practice references plus enumerated input refs. |
| Accessible evidence | Actor-processed detail addresses, source revisions and a known contextual reference. Pending reads instead identify an already delivered actor-owned input. |
| Preconditions | Versioned primitive executor and world contract determine required roles, custody/ownership, condition, resource compatibility and availability. These are checked at physical commit. |
| Transformation | One registered primitive. A procedure's name cannot supply an executor; named procedures require exact supported structure and actor-owned acquired-use evidence. |
| Affected relations | The explicit obligation reference, where applicable; physical return and fulfillment of the exact obligation occur in one atomic transaction. |
| Work and route | One prepare quantum followed by the declared execution extent. Required, completed and spent units are cumulative immutable job fields. |
| Partial progress | Each advance writes a new job revision and, for paid work, a matching actor-wallet debit. No physical effect occurs before a separate commit. |
| Dependencies | Pinned material, unit, definition, procedure, relation, context and world-contract revisions where applicable. Old immutable delivered evidence is not silently replaced by a new head. |
| Effects | Revised material, exact resource sink changes, any obligation revision, final job state, actual event and causal lineage commit atomically. |

The route is an operational stage sequence, not a claim that U4 has implemented a Model A/Crux content transformation. Legacy type-dependent processing and prices remain unchanged. U5 will connect the native lifecycle to those mechanisms.

## Lifecycle and reservations

`start` validates the request's accessible basis and reserves all required material instances atomically, or retains a waiting job with no partial reservation. `advance` spends the minimum of the work limit, remaining work, available energy and available time. One unit costs one energy and one time. `ready` means the full work extent has been paid; it does not mean a physical effect has happened. `commit` checks live dependencies and preconditions, then either records the complete effect or a failed attempt. `cancel` releases reservations while preserving all spent work.

Whole-instance exclusive reservations cover targets, tools and stock containers. This deliberately conservative granularity prevents double spending; it does not maximize parallel use of a large stock container. The service serializes commands with a reentrant lock. Real thread contention and both deterministic contender orders are covered by tests. A waiting contender can continue after release, but if its old material revision has changed it finishes as stale and needs a new, informed request.

Staleness is checked at commit. A job can therefore pay its remaining work before learning that its physical basis is no longer valid. Spent work is never refunded. The engine does not automatically replan or replenish resources; these are later autonomy/world-contract concerns.

Repeated delivery of the same command identity returns the original result without charging twice. Reusing an identity with different content is rejected. A terminal job cannot resume under a new command. Cancellation and failed attempts remain visible in raw history.

## Material repertoire and costs

Costs include the one prepare quantum and apply equally to energy and time.

| Operation | Units | Actual native effect |
| --- | ---: | --- |
| Transfer | 3 | Owner and custodian change from the owning/holding actor to the named recipient. |
| Inspect | 3 | Sample the current physical state of an accessible material identity at commit; observation delivery remains separate. |
| Use | 3 | A serviceable held tool gains one wear unit; reaching its declared limit makes it damaged. |
| Care | 4 | A worn serviceable held tool loses one wear unit; one compatible, actor-owned care quantum is consumed. |
| Return | 3 | Custody of a borrowed tool returns to its owner and its matching open return obligation becomes fulfilled. Ownership stays with the owner. |
| Damage | 3 | A serviceable held tool becomes damaged at its declared wear limit. This is the initial declared condition-change affordance. |
| Repair | 6 | A damaged held target becomes serviceable at zero wear; one compatible repair quantum is consumed and the held repair tool gains wear. |
| Consume | 3 | The requested positive number of available owned stock quanta enters the explicit consumed sink. |
| Read | 2 | Delivered particulars become available through an executed actor-owned processing receipt. |
| Bind | 3 | An actor-authored interpretation draft is retained against its processed evidence. Content generation and integrated conceptual realization remain U5. |
| Acquire | 3 | Matching successful, observed, actor-owned practice supports retained use of one exact procedure in one context. Generalized independent mastery remains U8. |

The first five are native implementations of the existing operation families. The legacy APIs and their in-flight jobs continue under their own authoritative writer and original contracts; U4 does not silently reprice or rewrite legacy episodes. Their compatibility tests remain mandatory. The native material vocabulary is the small declared workshop set, not arbitrary physical semantics or U9 procedure composition.

The material quantity field is lifetime accounted stock. A monotonic `consumed` counter records an explicit sink, so `available = quantity - consumed` and `available + consumed = quantity`. A fully consumed stock object retains identity and historical quantity but has no spendable availability. Tool repair does not create stock. Initial genesis is the only stock/work endowment in this contract; regeneration and replenishment are unsupported. Initial physical conditions are declared scenario inputs, not developmental outcomes.

## Effect, observation, interpretation and retention

A successful physical commit creates one actual event. A participant receives a separate observation only through an explicit permitted delivery. That observation pins the event and its historical before/after facts; later wear does not rewrite an earlier repair report. A delivered observation is pending until paid reading commits. Interpretation binding and acquired-use retention require their own paid operations and receipts.

The delivered fields include outcome and the event's allowed material facts. Internal failure reasons, stale dependency identities, reservation indexes and evaluator results do not enter those observations. The engine's inspector and return values are simulator interfaces; policies must receive only `participant_view`. A hidden definition revision can invalidate an internal cache or unfinished effect without changing a participant's undelivered information or policy probe.

A completed repair is not rolled back by a later conceptual revision, failed continuation or changed procedure. Historical access reconstructs from each actor's own history sequence. Another participant's reading, binding or practice does not grant access or acquired use.

## Accounting, replay and limits

`audit_transactions` reads exported chronological transactions and derives work debits, reservation conflicts, resource sinks, physical changes and causal event links. It does not call the executor's material transformation, consult its job/wallet/reservation indexes, or accept an assessor's success flag. Mutation controls show that forged charges and wrong physical repair outputs are detected. This is an independent U4 bookkeeping check, not the entire future U14 release audit.

The native store checkpoint, access checkpoint and complete operation checkpoint are separately restorable. The operation checkpoint retains initial conditions, typed commands and expected final state for exact replay validation. It intentionally includes redundant audit material and is not an optimized persistence layout. Restoration replays complete history; normal operation uses current affected records and reservation indexes. U13 storage, memory and throughput acceptance is open.

The service is a trusted simulator boundary, not a hostile Python security sandbox. Low-level world writers and simulator disclosure/declaration methods belong to the harness. Participant policies are isolated by receiving detached views. Unsupported declarations cannot mint native material, work wallets, receipts or actual effects through the operation service.

## Reproduction

From the extracted source directory, with Python 3.12:

    python tools/reproduce_u4.py --out /tmp/hle-u4-reproduction

Use a fresh output directory. Inspect the native workshop's paid accounting:

    python tools/inspect_u4.py /tmp/hle-u4-reproduction/u4_witnesses/workshop.completed.checkpoint.json

Inspect Alice's exact participant view:

    python tools/inspect_u4.py /tmp/hle-u4-reproduction/u4_witnesses/workshop.completed.checkpoint.json --actor alice

The final acceptance report supplies actual counts and source identity. U14 held-out seeds, R21C release seeds and U13 efficiency gates remain separate and unused by U4.
