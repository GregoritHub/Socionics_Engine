# R2 deterministic world and Truth record

The operational rules below are implementation choices linked to W01–W10 in `rules.json`. They supply the R2 test world; they are not claimed as psychological laws.

## State and identity

`WorldConfig` declares exact versioned actor/object descriptors, one context, initial ownership, private wallets, transfer visibility and directed message links. The demonstration uses two actors and two objects. Initial identity and ownership are public; later ownership changes can be hidden. Descriptor revisions resolve exactly. Only the explicitly configured active revision participates in world actions; metadata aliases never silently substitute for a historical referent.

Every committed command advances the public logical clock once. Event order is `(tick, 0)` and immediate delivery is `(tick, 1)`. A transaction contains one canonical `WorldEvent`, referenced work, observations, any explicit message/belief records and the affected task. Repeating an identical command ID returns its original event without advancing time or charging twice. Reusing that ID for different input rejects.

Truth maintains current facts, per-fact timelines, exact record lookup, wallet balances, task progress and memory heads as derived indexes. Changes carry exact before/after facts; resource deltas are reconstructed through the event's `WorkRecord` references. The log stores no whole-world snapshot per event. Command payloads remain alongside realized outputs to permit independent command replay; this small implementation does not claim optimal archival compression.

## Participant boundary

`World.participant_input(actor, after=cursor)` returns an immutable `ParticipantInput` and a new inbox cursor. It includes only that actor's delivered observations, current owned belief records, resources and the public clock. Passing the cursor on the next call avoids old observation traversal. The R2 belief list contains current records only; R3 will replace all-current-record exposure with a stated retrieval policy where appropriate.

`World.run_policy` calls a cooperative policy with this input and enforces the returned actor. It never supplies the world, Truth view, evaluator results, checkpoint, another actor's memories or event objects. Python processes themselves are not a hostile-code security sandbox. A policy that independently captures a simulator reference violates the declared interface.

All initial entities are known. A later hidden change does not reach a participant until an allowed witness projection, direct inspection, action feedback or explicit message delivers it. Transfer witnesses can receive the changed ownership or an occurrence-only observation with no ownership payload. The acting participant receives its own outcome and any authorized direct result. Receiving an object does not automatically notify its new owner in this fixture.

The clock is public, so this isolation claim concerns undeclared **content**, not secret event timing. Counterfactual controls hold the clock, initial observations, actor resources and other permitted inputs equal.

## Operations and resources

| Operation | Required work | Result |
| --- | --- | --- |
| Inspect | 1 unit | Deliver the object's current ownership to the actor. |
| Transfer | 2 units | Change ownership only if the actor is the current owner and the recipient differs. |
| Send | 1 unit | Deliver attributed, unverified propositions through a configured directed link. |
| Retain | 1 unit | Store a participant-supplied belief revision with checked ownership/provenance. |

Each unit consumes one energy quantum and one time quantum under versioned R2 rules. These are independent finite budgets; time-budget quanta are not the public logical tick. There is no automatic recharge, maintenance drain or false-belief penalty. The simulator can submit an explicit external credit with a reason.

`Attempt` wraps the R1 `ActionRequest` with a command ID, task ID and optional message/memory payload. The convenience `WorldPort.apply` and `run_policy` execute inspect/transfer requests. Send/retain use the explicit envelope; R2 does not supply an autonomous message or belief generator.

A paid work unit stays charged whether the eventual operation succeeds or fails. Insufficient work remains partial or deferred; it cannot change ownership or deliver a message. Resuming a task preserves its original request and accumulates prior work, charging only the remainder. The world checks the current action precondition at completion, so interrupted work can fail if circumstances change. A failed/completed task is terminal; a later genuine attempt needs a new task ID.

Malformed requests, unknown/inaccessible references, another actor's private evidence and conflicting task specifications reject before any state mutation. These are API validation failures. A well-formed attempt with a false ownership precondition or unavailable configured channel is a world failure with a retained event and charge.

## Belief existence and factual agreement

R2 retains explicit `MemoryRevision` fixtures through the action boundary. This is provenance and storage groundwork for R3, not relational Fool's Memory, navigation or autonomous belief formation. A `held_by` fact records possession of a belief record; the record's separate attitude distinguishes endorsement, tentativeness, dispute or retraction. Possession does not mean endorsement or accuracy.

The Truth view's `check(claim, at)` makes a **pointwise** comparison at an explicitly supplied time within the claim's scope. It compares exact subject, relation, object, context and revision. A known contrary fact gives `failed`; a matching fact gives `established`; unknown relation/identity/context, out-of-scope time or future evidence gives `unassessed`. It never treats an untested whole interval as proved. This interface does not perform IDEA identity returns or Shell assessment.

Fact timelines are as-recorded histories. Stored open-ended propositions are assertions; a later timeline entry ends their applicability in the derived view without mutating the old record. Historical reads therefore use `fact_at`/`check`, not an old proposition's open end as an assertion of eternal truth.

## Corrections and affected work

The simulator may append a `Correction` identifying the event whose single ownership assertion is still the current head. The correction supplies a new owner and reason, creates a new event with `corrects`, and takes effect at the new moment. It is an administrative record repair, not a paid transfer or automatic participant notification.

Original events, observations, costs and old as-recorded queries remain available. Corrections invalidate factual checks on the affected relation. Queries of the repaired present use the new record; queries of the original recorded past retain the original assertion. This limited semantics deliberately does not claim retroactive causal-history reconstruction. Corrections of a non-head ownership assertion or a multi-object initial event reject and require a separately designed migration/re-simulation procedure.

`changed_since(event_cursor)` returns an indexed suffix of event IDs and affected fact keys. Resource/task consumers can resolve that event's work references without scanning preceding history. Per-fact revision counters and reverse query dependencies invalidate affected factual checks only. R5 will add assessment-level dependencies; the current cache covers R2 factual checks.

## Replay and continuation

`world.checkpoint()` returns allowlisted typed JSON with a schema version and SHA-256 corruption check. It contains the configuration and ordered transactions. `World.restore(text)` starts at genesis, executes each command, and requires equality with every recorded event, work record, task, belief, message and observation. This rebuilds reference, idempotency, delivery, task, fact and resource indexes. Unknown schemas, duplicate IDs or semantically forged transactions reject even if the outer checksum has been recomputed.

The checksum is not authentication. Loading is an explicit full-history operation, not a constant-time snapshot load. Derived evaluator caches are disposable and recomputed; no IDEA assessment state exists yet. The caller's inbox cursor is explicit caller state: retain it alongside a participant controller when that controller is added. Any supplied valid cursor works identically before and after replay.

## Evidence and remaining scope

The test suite uses independent full-history fact/resource folds, a separate operational ownership oracle over 216 action sequences, all 16 combinations of energy/time budgets from 0 through 3, hidden-information interventions, checkpoint continuation at every prefix of the demonstration and a guard against ordinary global-history access with 0/2,000 inactive events. Additional process runs vary Python hash randomization. The evidence script reports descriptive action, evaluator, checkpoint and restore cost separately.

This closes R2 only. The A01–A15 integrated panel stays open through R5; R2 provides groundwork for A03, A04, A06, A07, A14 and A15 without claiming the completed memory/metabolism/assessment versions of those checks. No Shell generation, clearance, learned correction, language growth, institution or sustained population result is asserted.
