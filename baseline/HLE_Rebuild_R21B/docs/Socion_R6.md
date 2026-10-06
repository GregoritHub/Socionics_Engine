# Socion exchanges in rebuild R6

Release 0.6.0 · 16 September 2026

R6 extends `AssessedWorld` with independently stateful participants. `SocionWorld` retains the same journal, ownership world, Fool's Memory, Crux operations and R5 assessor. The new work is a local participant policy, paid reception through Model A, controlled exchange experiments and an explicit dyadic IDEA assessment.

## Source grades

| Mechanism | Status and source |
| --- | --- |
| Intertype frame transformations and element-preserving landing | Inherited checked mathematics, conditional on the supplied Model A tables. UMA verified revision, §9, paragraphs P0273–P0290; inherited M07. Sender-to-receiver landing uses the inverse frame relation. |
| Model A route, active element, support seats and numerical prices | Inherited R4 operational hypothesis. The structural mathematics does not derive these processing prices or psychological outcomes. |
| Each participant uses its own observations, histories, resources and response policy | Foundation §§2–4 and roadmap R6 require this separation. The executable policy below is an implementation choice. |
| A source reports from its retained account; acquired checking can trigger a fresh inspection before replying | New operational hypothesis. The checking capability itself is acquired by the unchanged R4 discrepancy/Embody mechanism. Its use for cautious replying is an explicit R6 policy extension. |
| Distinct delivery, reception, retention and consequential interpretation | Foundation §§3–4 and R5 handoff require evidence for these stages. The fixed ownership/query semantics are supplied. |
| WE initiation, definition and coordination return | Canon v2.1, §§7–8, plus the explicitly declared application predicate below. No inferred equivalence with a Crux route cell. |
| Policy state, notice cursors, scheduling and checkpoint representation | Engineering choices X01–X09 in `rules.json`. |

The original papers and R1–R5 runtime modules, except the expanded codec and current entry point/version metadata, remain unchanged. Original R1–R5 tests are unchanged. No universal type compatibility ranking or empirical validation claim is made.

## One participant turn

`AgentState` contains its owner's notice cursor, queued/current goals, current work specification, exact memory/capability references, response state and timeout count. It contains no other participant's private memory. The initial `AgentPolicy` is explicit per participant. `ConfigureAgent` makes a prospective, journaled experimental policy intervention between active goals; learning does not require that command.

`agent_view` resolves only an actor's next permitted notice, selected owned memory/binding revisions, own pending operation result, own wallet and own processing history. `socion_policy.decide` accepts that detached immutable view. It has no access to Truth, world ownership, the global journal or assessment reports.

`PlanTurn` records a policy decision. The next `advance` executes its pending R2, R3 or R4 command, or the new reception command. A decision cannot be skipped over an unexecuted operation. Paid partial work retains its original payload, basis, route and task identifier. A new command identifier resumes it without refund or repeated completed work. The journal retains both decisions and actual operations.

The finite task controller supplies a reusable processing sequence, not fixed answers or a predetermined partner's actions. It chooses among answering from memory, checking before answering, remaining silent, waiting, using its own account, inspecting, attempting a transfer and retaining consequences. Choice conditions use actual information, capabilities and resource availability. Goals, policy options, scheduling order, resource credits and experimental hidden interventions remain harness supplied.

Dispatch branches and queue bookkeeping have no simulated energy price. Reception, memory work, Model A routing and physical actions are charged. Their computational runtime is included in the descriptive profile. This is an explicit cost boundary, not a claim that cognition is free.

## Message grammar and processing

The fixed grammar permits an ownership query, an ownership report, and a reply-to address. Actor, object, context and revision identities are exact. A directed channel delivers testimony with sender identity. The channel also captures the sender's declared type and active information element at emission; this is explicit structural message metadata, not access to the sender's private memory or its evidence basis.

Reception maps the emitted element's source seat to its element-preserving receiver seat, computes a route from the receiver's current active element and charges the declared route plus one content unit. Completing that work changes the receiver's actual active element, which influences subsequent R4 processing. It does not itself establish the message as true or install its contents in memory. Reception is attention routing; no new Crux operator is asserted by relabeling it as a WE movement.

After completed reception, R3 writes and binds the report. An experimental stable object-to-card association chooses a cue from the existing deck. Collisions are permitted; this is neither card semantics nor a memory-capacity law. A separate cue can retrieve an exact retained checking lesson. R3 retrieval supplies the R4 Theorize account; Apply executes its resulting action, and Embody retains consequences and any acquired checking capability.

Older testimony is preserved in a separate addressed record and does not replace a later account. Ambiguous or unsupported packets remain delivered raw observations but are not interpreted by this grammar. Missing replies can trigger the declared local patience policy. These are restricted parsing and recency policies, not general language understanding, source-reliability inference or semantic repair. R8 remains responsible for broader language and meaning repair.

## Independent learning and controls

The independent-learning fixture changes two ownership histories through explicit world actions and hidden prospective corrections. Each participant subsequently receives its own discrepancy through actual Apply operations and independently acquires its own `inspect_before_transfer` capability through Embody. No capability or desired reply is injected into either participant.

The acquired lesson can influence a later reply and a goal on the other object. For the matched ablation, two branches restore the same checkpoint and wallets; `ConfigureAgent` changes only subsequent access to retained lessons. With access disabled, the source replies from memory and the receiver attempts transfer directly. With access enabled, the source inspects before replying and the receiver recalls the acquired guard and inspects before transfer. The earlier history and capability records remain intact in both branches. A four-condition control independently crosses sender and receiver lesson access to separate the two effects.

Other controls independently vary asking, response policy, full/occurrence observation access, energy, time, type routing, positional prices and scheduling order. The controlled same-packet panel covers 16 × 16 type pairs × 2 routing settings × 2 price settings. Sixty-four integrated cases vary the responding participant's type across the routing/price settings. At ample funding they retain the same semantic/action result while revealing route and cost differences. Equalized type routing removes declared type-label effects in the same-packet control. Type does not force an answer, a developmental destination or a relationship outcome.

## Explicit WE predicate

`DeclareDyad` specifies two distinct actors, one object, their shared world context, the ordered transfer/return protocol and a maximum charged-unit budget. `OpenRound` must precede its goals and starts in the left-owner domain. The operational identity feature is the declared participant-role ordering together with restored object ownership after actual successful transfers in both directions.

`CloseRound` evaluates only the declared completed interval. Identity requires exactly two appropriate goal results in the prescribed order, successful transfers in each application's own enactment records, and return of ownership. Interpretation requires, for each leg, the delivered message, completed reception, its observation in a recalled memory's provenance, its exact ownership proposition in the receiver's account, and application/retention of that account. Factual accuracy remains a separate R5/Truth question: an interpreted message may be false.

| WE phase | R6 interpretation |
| --- | --- |
| Initiate | The explicitly declared distinct participant standpoints. |
| Define | The declared shared context, complementary transfer/return expectations and exact object/role identities. |
| Engage | The recorded coordination return and consequential interpretation tests. Missing return evidence remains unassessed. |
| Align | General composition preservation remains unassessed; an observed engagement counterexample remains failed. |

Cost-path status is reported separately from endpoint identity. Every completed round remains in the study; a later success cannot remove an earlier failure. R5's original WE cells are unchanged and unassessed. The new WE cells live in `DyadReport`, under the explicit R6 declaration. No arbitrary finite-composition theorem is imported into the growing simulation.

## Continuation and affected work

The `hle-r6-v1` checkpoint contains the original configuration, initial profiles/policies and the complete typed journal. Replay executes each command and compares the generated transaction exactly, rebuilding all derived indexes, queued goals, pending decisions, partial work and assessment queues. Rehashed but semantically altered records reject. R2–R5 loaders remain available; automatic live-session migration between schemas is not supplied.

Notice intake processes new delivered observations. Ordinary decisions read one notice and selected owned addresses. An item-to-study index invalidates only affected dyadic reports; bounded draining records each report revision. `tests/reference_socion.py` independently reconstructs the tested rounds from the whole journal offline. Runtime decisions and assessment scheduling do not scan inactive journal history or unrelated studies.

The runtime still stores all history. Current participant state snapshots include queued goals; checkpoint size and replay cost grow. Recall has an explicit visit limit; object-cue collisions may broaden recall. Round close visits its relevant goal interval; cumulative reports enumerate their own completed rounds. The demonstration uses two participants and two objects. Population scaling, queue stability, recursive composition and sustained efficiency are R7/R10 work, not consequences of passing this bounded panel.
