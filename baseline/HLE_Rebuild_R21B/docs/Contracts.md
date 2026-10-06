# R1 interface contract

These records define what later runtime components must exchange. They are immutable values, with local type and consistency checks. A record's existence does not prove the event happened or that its references are authorized. R2 must enforce world ordering, reference resolution, ownership and transaction rules at the service boundary.

## Identity and history

`Ref(kind, key, revision)` identifies one exact revision. A historic address must never silently resolve to the current revision. Actor and object identity are explicit references; a claim with another actor, context or time scope is a different proposition even when its graph shape matches.

`Moment(tick, order)` supplies a total logical ordering. `TimeScope` is half-open `[start, end)` with `None` for an explicitly open end. Strings and integers may be proposition values; object/actor references use `Ref`, not names packed into prose. Relation interpretation is supplied by versioned world rules in R2.

| Record | Required information | Deferred runtime obligation |
| --- | --- | --- |
| `WorldEvent` | ID, order, actors/objects, action, context, before/after changes, actual causal-rule witnesses, work, outcome and explicit corrections. | Validate deltas against world state; enforce causal order and correction semantics. |
| `Observation` | Observer, event/message source, source/delivery times, delivered propositions, channel rule, visibility limits and uncertainty. | Apply the actual observation policy and noise model; prevent unpermitted delivery. |
| `MemoryRevision` | Owner, retention time, propositions, links, observations, derivations, claim attitude, retained procedures and exact predecessor. | Resolve provenance and historic versions; execute retention/revision. |
| `CueDescriptor` | Symbol/card identity, deck, suit, printed rank, folded location and source layer label. | Validate the complete card catalog and any chosen non-card cues. |
| `CueBinding` | Exact cue, context, memory revision, owner, time scope and learning evidence. | Resolve associations in context and preserve prior binding meanings. |
| `CursorState` | Owner, current cues, elected procedure if any and practice evidence. | Measure or learn navigation competence without making the memory organization depend on it. |
| `MovementRecord` | Holon, optional demand, formal route/polarity, selected procedure, preconditions, inputs, ordered processing/work witnesses, outcome and retained references. | Implement the content transformation and its consequences. |
| `WorkRecord` | Available amounts, credits, actual charges, resulting amounts, required/performed work, status and reason. | Execute a transaction and prevent double-spending or duplicate charges. |
| `AssessmentSpec` | Versioned state/identity/rules, explicit protocols, domains, resources, path conditions, comparison rules and declared scope. | Register the specification before testing and keep failed protocols in the family. |
| `AssessmentResult` | Spec/protocol reference, measured dimension, evidence status, witnesses and exact tested sequences. | Compute the result; check identity features are discriminating; establish any claimed closure conditions. |

## Resources and incomplete work

Integer quanta are an engineering choice for deterministic accounting. Each resource unit references a versioned rule; R1 does not specify energy-per-thought, per-type rates, replenishment, or a mandatory false-belief drain. Those are choices to state and test later.

Every work record requires `before + credited - charged = after` for each declared unit, with nonnegative amounts and explicit zero balances. Charges may occur on failure or deferral. A full processing budget can still end in failure. Recording actual work separately from the outcome prevents unsuccessful attempts from disappearing from the ledger. A refund, if justified later, must be an explicit credit, not an implicit consequence of route inversion.

## Memory flexibility

A memory has no required A/B/C labels, replay path, suit, card rank or storage layer. It may carry several propositions, links and cues. The nine-position fold belongs to a cue descriptor, not to the total memory capacity. The interface permits the same cue in different contexts and several cues to the same memory revision. This is representational support only; retrieval, binding updates and recall quality remain R3.

The source labels Id and Identity remain unequated. No Sun → Judgement → World recurrence or other identity traversal is supplied. The descriptor accepts the source label without inventing its dynamics.

## Participants and evaluator

`ParticipantPolicy.choose` receives a `ParticipantInput` containing delivered observations, the participant's own memory revisions, its resources and explicit demands. It returns an action request grounded in participant-visible references. `EvaluatorTruthPort` is a separate interface and is never an argument to the policy.

The input constructor rejects observations for a different observer, future delivery, another owner's memory, future retention and evaluator-only evidence in an action's stated basis. This is useful boundary validation, not a proof against hidden-state leakage. R2 must show that changing unobserved world facts cannot change participant action before a permitted channel delivers information. Ledger uniqueness and reference authorization also remain R2 work.

## Assessment boundaries

Factual agreement, identity return, path conditions and retained capacity are distinct dimensions. An endorsed belief is an attitude, not a truth flag. World vocabulary can record that someone holds a belief without asserting its proposition as world truth.

`IdeaCell` is phase × perspective. `Route` is origin × destination. Both use named perspectives, preventing an accidental index swap between the Canon's I/We/It/Its order and Crux's I/IT/WE/ITS order.

The result contract requires witnesses for established or failed claims and explicitly supports unassessed claims. It cannot certify meaningful feature maps, protocol success, Shells or universal composition from data shape alone. Those computations and their controls belong to R5.
