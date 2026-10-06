# U3 compact particulars and situated access

Version 1 · 21 September 2026

U3 adds `hle_unified.compact`, `hle_unified.particulars`, and the public `hle_unified.u3` exports. The five original U2 runtime modules and the frozen R21B runtime retain their original bytes. These additions implement the U3 storage/access contract; U4 remains responsible for paid native operation execution, and U5 for integrated Fool's Memory–Model A–Crux realization.

## Authority and scope

The current implementation roadmap, its frozen U1 acceptance cases U3-01 through U3-03, the target conception, and the new-build foundation govern this milestone. The storage schema, selectors, receipt adapter, contextual binding walk, and deterministic policy probe are **engineering choices**. They implement no new psychological claim, numerical geometry, Shell diagnosis, or universal learning mechanism. Source-defined card meanings and all legacy Model A prices remain unchanged.

The new APIs are trusted simulator/service boundaries, matching the U2 boundary. A participant policy receives only a detached `ParticipantView`. It receives neither `AccessLedger` nor `CompactStore`, their inspectors, permissions, checkpoint bytes, content pools, dependency indexes, or evaluator state. This is an information-flow contract within the simulation, not a sandbox against hostile Python or a guarantee about wall-clock timing side channels.

## Compact authoritative storage

`CompactStore` retains the U2 native laws and exact `ObjectId`/`ObjectRef` meanings. It is an alternative authoritative backend, not a live second writer mirroring an `ObjectStore`. Importing a full-snapshot store replays its completed journal into a new backend; the caller then chooses the authoritative instance. The independent full-snapshot store is used as a comparison oracle in tests.

The backend stores:

- An immutable value pool, indexed by verified structural content hashes. Equality is checked before reuse, and decoded immutable structures are shared physically. Object identities are never derived from these hashes.
- One field-difference row per object revision. Revision and immediate predecessor remain exact; unchanged fields reconstruct from the predecessor. An explicit `None` and a field omitted from a delta have different meanings. Boolean and integer values remain distinguishable.
- A chronological journal containing exact version references, transaction metadata, and lineage. It does not retain a second set of full version snapshots.
- Exact reverse dependencies and an internal derived-view cache. Dependency changes can evict cached views without notifying a participant.

Checkpoint-local integer indexes avoid repeating content hashes on the wire. Restoration checks the outer checksum, typed node grammar, finite backward structural references, duplicate values, revision predecessors, transaction order, and all U2 semantic/material constraints. It then regenerates the compact representation exactly. Unused nodes, incomplete histories, unsupported state and noncanonical deltas are rejected. Checksums do not authenticate an independently rewritten, self-consistent history.

`canonical_checkpoint()` reconstructs the U2 full-snapshot wire form for independent comparison. `checkpoint()` stores the compact form. `resolve(exact_ref)` never substitutes a current head. `dependents(exact_ref)` is an inspector interface. The stricter U3 retry comparison also rejects changing a boolean to an equal-valued integer under an existing transaction key.

Delta reconstruction follows the predecessor chain. Full historical segmentation, workload tuning, cache budgeting, and U13 machine-performance acceptance remain open. The compact checkpoint is smaller in raw bytes in the retained workshop fixture, but its gzip representation remains larger than the full-snapshot equivalent.

## Exact particulars and observation rights

`Grant` identifies one actor, one exact source revision, a subject revision, and a nonempty set of `Selector` records. A selector names an indexed key, a category, and an explicit dataclass/tuple field path. Supported categories are name, date, ownership, event, receipt, definition, and detail. Scalar values remain scalar values; selected immutable definitions and procedure descriptions can also be shared.

Grants are service-side rights, not participant information. They do not deliver content, resolve later revisions, recursively disclose references, or change a participant's visible history. Revocation prevents further delivery under that grant; it does not erase already delivered or retained memory. Actor admission is anchored to the person role at the actor's first revision, so replay does not reinterpret an earlier grant through a later actor descriptor.

A delivery records its actor-local key, explicit delivery time, source revision, and selected particulars. Its source occurrence category remains intact: a remembered claim is not promoted to an actual event. The participant initially receives only the arrival key and time. Delivery times cannot run backwards within an actor's stream.

An explicit source reference may be visible while the referenced object's contents remain inaccessible. `ParticipantView.resolve(ref)` returns only processed fields for that exact source; an inaccessible reference and a nonexistent reference both return the empty result. It never returns a complete world object or follows an object's definition, ownership, lineage, or source links automatically.

Evaluator-role objects cannot be granted. Another actor's private accounts, attitudes, memory entries, or acquired capability state require an explicit permitted recipient observation instead of direct disclosure. A grant to a person's public name does not expose that person's private capabilities.

## Processing receipts and acquired use

The U3 access adapter imports processing evidence as ordinary U2 `Role.RECORD` objects written under the declared `u3.processing` authority. Their immutable attributes record actor, operation, work key, exact input revisions, required units, cumulative completed units, and cumulative spent units. The adapter checks all of these before accepting a result. Required work must be positive; progress cannot exceed it or erase already recorded progress/spending.

This is a **trusted completion-evidence interface**, not a new paid executor. The deterministic U3 fixtures explicitly supply these receipts; they do not claim that a new Model A route, wallet debit, practice episode, or physical repair produced them. Existing legacy paid work and its regressions retain their original executable accounting. U4 must connect native execution to this interface and enforce spending, routes, feasibility, interruptions, and dependency checks.

For `read`, partial receipts remain visible to their owner and leave content pending. A complete receipt tied to that actor, delivery key and exact source makes its selected particulars available. Saving and restoring partial work preserves the pending state and accepted receipts. The cumulative work values are observations of one job's progress, not amounts to sum as additional debits.

For `bind`, completed evidence must match the exact actor-owned interpretation and its processed particular sources. For `acquire`, the actor must have processed the exact procedure structure, know the context reference, and possess a matching completed acquisition receipt. Reading a procedure's name, receiving its description, sharing another actor's stored definition, or borrowing another actor's receipt is insufficient.

`can_use(procedure, context)` means **retained acquisition evidence for that exact procedure and context**. It does not prove current material feasibility, supply an executor, or execute a described action. A procedure with no supported executor remains physically unexecutable even when acquisition evidence is represented. New procedure revisions and other contexts do not inherit this evidence automatically.

## Participant views and conceptual bindings

`ParticipantView` contains immutable particulars, pending arrivals, actor-owned processing receipts, interpretation history, acquired-use evidence, and actor-local history. It contains no global clock, global event count, hidden change notification, pool identity, cache freshness flag, or invalidation reason. Its detail, category, subject, typed-value, exact-source, receipt and work indexes use only that snapshot.

`lookup()` and exact-source/receipt retrieval do no conceptual traversal and do not modify modeled work. They expose already completed processing results; they are not a free substitute for a future paid retrieval operation. The stored legacy `DetailQuery` mechanism and its prices remain unchanged.

A conceptual binding refers to an existing U2 interpretation object, actor, target revision, cue revision, context revision, meaning/content, endorsement, confidence, processed detail addresses, links to retained actor bindings, and its completion receipt. Thus interpretation identity and history are addressable in the same native store. Two participants can bind incompatible interpretations to the same target without changing material truth or sharing their confidence.

`traverse(cue, context, visit_limit=...)` is a finite contextual walk over retained bindings. It starts from current retained binding revisions, follows exact actor-owned links in that context, stops on revisits, and reports truncation when its visit bound prevents completion. Older binding revisions and their exact meanings remain available through history. This walk is a U3 access primitive; it is not a claim to implement a U5 paid Fool's Memory path or Model A route.

The `tests_u3.fixtures.choose` probe proposes a request using the latest accessible ownership particular and contextual acquired-use evidence. It cites the same source revision used by direct lookup. It receives only the participant view and executes no material action. Its purpose is a falsifiable decision/reason comparison, not an autonomy or realistic-personality claim.

## Hidden changes and restoration

Material transfers, definition revisions, another actor's processing, and private acquisition can invalidate internal caches. Rebuilding a participant view uses retained access history, never global current truth. In the declared matched panel, eight hidden-state variants preserve byte-identical pre-delivery views and identical policy choices/reasons. A permitted new delivery followed by completed processing can then change the available ownership detail and decision.

The access checkpoint includes the compact world plus an immutable access command/result log and shared access values. Restoration replays rights, deliveries, processing, bindings and acquisition against exact source revisions, rederives projections, compares results, and rejects unused or inconsistent material. `view(actor, through=n)` reconstructs an actor-local historical position without exposing other participants' event counts. Temporary historical reconstruction caches are discarded after use.

The access service is serial in U3. Concurrent native operations, live rights races, resource reservation, and active-operation invalidation belong to U4. Native retention/forgetting policies and unrestricted concept growth are not introduced here.

## Reproduction and inspection

From the extracted `HLE_Unified_U3_v1` directory, with Python 3.12 and the standard library:

    python tools/reproduce_u3.py --out /tmp/hle-u3-reproduction

Use a new output directory. The runner retains commands, timestamps, source hashes, per-test results, baseline checks, and full U2/U3 witnesses. It does not rerun the complete historical 912-test U1 panel, the original candidate population panels, or reserved release seeds.

The offline inspector prints a participant snapshot from a situated checkpoint:

    python tools/inspect_u3.py /tmp/hle-u3-reproduction/u3_witnesses/situated.completed.checkpoint.json --actor alice

Add `--through N` for an actor-local historical position. World checkpoints and global inspector outputs are evaluator artifacts; policies receive only `ParticipantView`.
