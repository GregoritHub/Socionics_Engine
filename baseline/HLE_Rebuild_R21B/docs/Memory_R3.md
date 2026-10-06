# Relational Fool's Memory in R3

R3 implements a bounded experimental navigation and revision policy over the R2 world. The source defines the card arrangement and the use of contextual associations. It does not derive this search algorithm, processing price, or revision policy. The rules below are declared before acceptance evaluation.

## Coordinates and references

The source catalog contains 21 numbered Major Arcana, the unlocated Fool, 56 Minor cards and 52 Standard cards. Numbered cards use `(rank - 1) % 9 + 1`. Arcana preserve the source's Super-Ego, Ego and Identity labels. Suit panel readings are separate metadata; a suit card is not assigned a psychological layer by its rank. The two uses of Major in the source are distinguished by catalog identifiers.

Card identity, rank, folded location, retrieval context, content, provenance and navigation state are separate values. No card has a memory capacity. A binding connects an owner, an exact cue, an exact context, a semantic time scope and an exact memory revision. Several bindings may share either endpoint. Context labels can be declared privately; their existence does not establish their factual meaning in Truth.

## Experimental retrieval policy

An actor supplies ordered seed cues, one exact context, a semantic time, optional subject/relation filters, and a positive visit limit. The semantic time cannot be in the future. One paid seed-resolution operation snapshots the current matching binding revisions in cue order, then binding creation/update order. Scope matching is half-open. This is the moment at which associations are selected, including when initial work was deferred.

The remaining work follows a breadth-first frontier of exact memory revisions. Each distinct visited revision costs one energy and one time quantum. Duplicate targets are visited once. A cursor with no elected navigation policy still recalls directly cued memories. Electing the experimental linked policy adds outgoing memory links up to an explicitly configured number of hops. That number is an experimental competence setting, not a claim about psychological ability or a fixed engine depth limit. Stored memories and links do not change when this setting changes.

Each hit records the indexes of propositions matching the requested context, semantic time, subject and relation. Unmatched fragments may still lead to matching linked fragments. The result also preserves all visited addresses and traversal parents; it never invents missing details or issues a truth verdict. When the visit limit stops a nonempty frontier, the result reports truncation. A completed search may return no hits. Completion means the declared search finished, not that the memory is correct or complete.

The first funded step also freezes cursor policy/competence. Later binding, cursor or memory changes cannot redirect an in-progress recall. Stored links and bindings always reference exact revisions. Direct historical resolution remains available even after rebinding. Ordinary retrieval selects current binding heads; reconstructing what the entire association map looked like in the past is an offline replay operation.

## Revision and use

An explicit write supplies content, holder attitude, links, provenance and the exact expected previous memory revision (or none for creation). Completion checks that expected head again. A competing update causes a paid failure, preserving work and the current head. Writes preserve prior records and do not rewrite bindings or inbound links.

The participant helper `observed_revision` copies only the selected propositions of a delivered observation. Direct event observations produce endorsed observed content; testimony produces tentative content. These are holder attitudes under this experimental policy, never evaluator accuracy. An empty or ambiguous selection rejects instead of manufacturing a fact. Revision does not implicitly change another memory or generalize to other situations.

Bindings use the same compare-and-replace rule and preserve their previous revisions. New bindings must cite the target memory; replacements must also cite the previous binding. Recall results can supply the exact recalled memories to `ParticipantInput` and to the existing permitted action basis. The example ownership policy transfers only on one unambiguous recalled ownership value naming itself; otherwise it asks to inspect. It receives no Truth interface.

## Work and persistence

Writing costs one unit plus one per proposition and link. Binding costs two units. Context declaration, cursor configuration and inbox acknowledgement cost one unit. These are explicit experimental prices shared with R2's integer wallets; they are not measured biological rates. Each recall step costs one unit per resource. Selected-record payloads and seed buckets still affect real CPU work; the numerical prices do not assert constant CPU cost.

Partial work persists in the same world journal. Recall yields after a caller-specified number of steps or resource exhaustion, with no participant result until completion. Each performed recall step has its own WorkRecord; a zero-funded attempted step is deferred. The event reports partial work when earlier steps exist. Simple writes retain funded progress, charge only remaining work, and publish changes only on completion. Malformed or unauthorized inputs reject before mutation; valid attempts with stale preconditions fail after paid work.

Inbox acknowledgements retain actor-specific cursors and check their expected prior value. R3's selective input API defaults to no memories and reads only the inbox suffix and explicitly requested owned revisions. The inherited R2 API remains available for compatibility and still enumerates active beliefs. New participant paths use the selective API.

R3 transactions extend the same journal and record index; there is no second event or fact store. Current cue/context buckets and actor record indexes are derived. Checkpoint restoration re-executes every command and compares every transaction, rebuilding bindings, tasks, cursors and indexes. R2 checkpoints remain readable through the R2 world. Diagnostic exports and full replay are deliberately offline and grow with retained history.

## Scope

The Id/Identity relationship and repeating traversal remain unelected. No automatic layer progression, three-vertex replay, rank-from-edges rule, Shell detector, false-belief drain, card-to-Crux mapping or inferred memory capacity is introduced. R4 supplies realized Crux and Model A processing; R5 evaluates the integrated IDEA and Shell panel.
