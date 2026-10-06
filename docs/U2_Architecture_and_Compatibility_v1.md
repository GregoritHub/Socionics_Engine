# U2 common versioned object structure

Version 1 · 21 September 2026

U2 adds `hle_unified` beside the frozen R21B runtime. It implements the object and history contract needed by U3. The original `hle` modules remain unchanged. The new namespace depends on the baseline's strict immutable `Record` validation, logical time, and separately defined personal/evaluator status enums.

## Identity and historical meaning

`ObjectId(namespace, key)` identifies an instance. `ObjectRef(identity, revision)` addresses one exact immutable version. Neither a label nor a value hash identifies an instance. Identical bowls may share a definition reference while retaining independent custody and revision chains.

`ObjectVersion` carries its writer, roles, optional capabilities, exact definition binding, immediate predecessor, occurrence category, lifecycle, and small typed attributes. Native histories begin at revision 1 and advance consecutively. `resolve(ref)` never consults the current head. `head(identity)` is an explicit current-state request. Old definitions, relations, and accounts remain available after revisions.

Definitions have a meaning or explicit `None`, source status, constraints, and reusable operation references. Source statuses distinguish supplied meaning, engineering choice, unspecified meaning, and preserved legacy content. An unspecified meaning cannot silently receive invented text. Constraints remain declarations except for the explicitly supported material conservation law. Procedure descriptions do not acquire executable physical powers merely through naming.

## Roles and optional state

| Concern | State and validation |
| --- | --- |
| Material | Owner, custodian, positive integer quantity, exact unit definition, condition. |
| Concept | Typed propositions with exact subject, object, context, and temporal scope. |
| Procedure | Inputs, preconditions, constituent procedure revisions, effects, optional executor identifier. U2 does not execute a new paid procedure lifecycle. |
| Relation / commitment | Typed and named endpoints, direction, exact context, time scope, terms, and independent revision history. |
| Collective | Finite member identities, boundary, resources, and pinned summary dependencies. |
| Memory / agency | Optional instance-owned entries and acquired references. Sharing definitions or membership does not populate them. |
| Governance | Optional rule and obligation references. No autonomous institution-formation claim follows from storing these references. |
| Account | Referent, content, attributed time, holder when situated, and source references. |
| Attitude | Holder, exact target, endorsement, optional 0–100 confidence. |
| Assessment | Exact target, declared dimension, outcome, evidence, and reason. |

An ordinary material object requires none of the memory, agency, or governance capabilities. Capabilities are immutable state descriptions; U2 does not allocate a cognitive runtime for every object. Known native roles require their corresponding state, repeated state is rejected, and relations/propositions require objects with the context role for their context reference.

## Occurrence and assessment

Actual event, observation, remembered claim, hypothetical continuation, and interpretation are distinct occurrence categories. Personal endorsement and evaluator outcome are separate addressable objects. A fully endorsed prediction can remain factually failed.

An occurrence category cannot be changed through revision. Actual events cannot be rewritten. To relate a hypothesis to a later actual event, create a separate event and cite the prior referent/evidence. The native journal records object bookkeeping, including the act of storing a hypothesis; `actual_events()` selects only objects explicitly categorized as actual events. A metadata transaction is not automatically a physical event.

Logical journal order and the time attributed by an account are separate coordinates. U2 stores both; U3–U4 will implement the generalized participant-access, delivery, and operation-timing interfaces.

## Authority, transactions, and material lineage

`ObjectStore.commit` validates the entire transaction before publishing any version. A lock serializes commits. One identity has one authoritative writer throughout its native history. Stale or skipped revisions, repeated IDs with conflicting content, missing references, and inconsistent lineage reject without publishing a partial batch. An identical transaction-key retry returns the original transaction.

Every write has lineage. Creation, ordinary revision, definition change, membership change, transfer, division, combination, and replacement have separate change kinds. Causal evidence and a transformation's law must exist before the transaction. Cyclic content references may be introduced together in one transaction because they remain finite identity/revision leaves; causal provenance cannot point forward to evidence created by that same transaction.

The supported native material law is `u2.conserve-owned-quanta-v1`. Division, combination, and replacement require the acting instance to own and hold every consumed input; require common owner, custodian, unit, and condition; and conserve total quantity exactly. Consumed identities receive immutable retired revisions in the same transaction that creates fresh output identities. Retired material cannot be revived or spent again. Replacement conserves the declared quantity and records a new identity; it is not a repair or manufacturing model.

Native transfer changes ownership and custody together and requires the acting owner to hold the material. Generic revision cannot alter material state. Explicit creation is a simulator initialization/source operation. These native APIs are structural bookkeeping under a trusted simulator/service boundary. They do not charge a new participant wallet or claim completion of U4. Legacy participant operations continue to use all existing costs, partial-work and failure rules.

Composition resources are references, not newly credited balances. General collective resource ownership, effect decomposition, consent, and summary invalidation remain U11 work. The U2 tests establish representation and lineage, not those wider behaviors.

## Compatibility contract

The adapter maps every legacy `Ref(kind, key, revision)` bijectively to the namespace `legacy.ref.<kind>`, the same key, and the same revision. Native identities cannot be confused with legacy identities. Legacy records without their own identity require a caller-scoped explicit address; value equality never supplies it.

The structural adapter covers all 271 allowlisted legacy dataclass tags and 14 enum tags in the frozen codec registry. It enumerates inherited fields using `dataclasses.fields`, preserves tuple boundaries, and retains every scalar, enum, reference, and field. The base `Record` registry marker is not a dataclass and is rejected as a payload. This is a wire-support inventory, not a claim that every class has an independently executed fixture.

| Slice | Authoritative state | U2 view |
| --- | --- | --- |
| Native objects and relations | `ObjectStore` journal, with one writer per identity | Exact immutable versions. |
| Legacy world effects, observations, work, memories, and tasks | The existing `World` owned by `LegacyWorldBridge` | Detached role-tagged objects or typed values. |
| Legacy ownership relation | Existing chronological world changes | Addressable relation revisions rebuilt from that history, each citing its source event. |
| Legacy checkpoints, including v4 | Existing typed checkpoint and the appropriate legacy restore class | Field-by-field U2 object representation; exact recovery of canonical legacy checkpoint text. |
| Other legacy record families | Their existing runtime owner | Lossless generic record views; no invented domain semantics. |

`LegacyWorldBridge` executes the legacy R2 ownership/inspection/communication/memory slice. It does not move an entire developed R21B episode into native storage. Higher-level checkpoints can be structurally converted and then restored by their original runtime class. Compatibility views are immutable and rejected by native `ObjectStore`; they cannot become a second writable copy of legacy state.

For legacy descriptors, existing Ref revision semantics remain intact. Ownership changes become separate derived relation versions instead of manufacturing descriptor revisions. A compatibility envelope's predecessor is the preceding revision coordinate; the original record's actual causal fields remain untouched in its payload, and the adapter does not assert that an unprovided earlier record exists.

Only `participant_input` provides actor data, by adapting the existing permitted view. `inspect_object` and `ownership_history` are offline inspector interfaces. They are not supplied to participant policies. Native generalized situated access is U3 and is not yet implemented. Writer names are routing identifiers in a cooperative Python API, not authentication credentials or a hostile-code sandbox.

## Persistence and exactness

The U2 codec uses an explicit dataclass/enum allowlist, canonical JSON, a checksum, duplicate-key rejection, and strict field validation. It changes none of the legacy wire registry. Native restoration replays the full journal through the same integrity and material checks. Rehashed malformed journals still fail structural/semantic validation; checksums are integrity checks, not signatures.

Exact legacy text recovery applies to canonical checkpoints produced by the legacy codec. Noncanonical input whitespace is not preserved as historical meaning. All actual tested checkpoint inputs are canonical. U2 uses complete immutable revisions; delta storage, cross-instance physical interning, performance targets, and history compaction remain U3/U13 work.

## Validation scope

The frozen U1 acceptance cases U2-01 through U2-08 are implemented directly. Additional controls cover writer conflicts, stale writes, transaction atomicity, concurrent consumption, illegal occurrence promotion, malformed roles and references, conservation failures, illicit material changes, false beliefs, private observations, codec tampering, and semantic replay.

The adapter comparison enumerates all 216 sequences of three choices from the inherited six-operation action set. Each sequence checks participant projections, transaction outcomes, wallet charges, ownership, an independent history fold, and checkpoint reconstruction. The R2 partial-work witness retains the unfinished unit and charges only the remaining unit after the fixture's explicitly allowed supply. The separate v4 witness uses the existing IEE/12 zero-budget case, preserves its three-event journal and lack of acquisition, and continues exactly under a Tick.

The inherited 912-test result remains U1 historical evidence. U2 freshly runs 71 distinct applicable inherited tests, including the U1 protection index after deduplication, alongside its own 31 tests. No unified held-out seeds or legacy R21C release seeds are used. U3–U14 and U13 efficiency acceptance remain open.
