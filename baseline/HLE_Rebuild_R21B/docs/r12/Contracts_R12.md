# R12 developmental contracts

These contracts specify the next runtime integration boundary. They use the existing R11 `Ref(kind, key, revision)` address space and immutable exact values. Every new record declares `schema_version=1`; an unknown version, a mutable list substituted for a tuple, or a Boolean substituted for an integer is rejected.

The contract constructors validate local types and internal consistency. They are not permission checks, live journal resolvers, world transformations, or Shell detectors. R13 must resolve each exact reference and check actor access before executing work. R16–R20 must construct assessment evidence from actual trajectories. Supplying a constructed assessment record cannot alter the current engine's actor, capacity or altitude.

## Unified state

| Source coordinate | Contract field | Meaning |
| --- | --- | --- |
| Γ | `gamma` | Fixed TIM, stack and 4–3–2–1–1–2–3–4 dimensions. |
| H | `organization` | Revisioned current organization/procedure. |
| m | `movement` | Existing formal Crux route and polarity. |
| c | `content` | Exact memory/observation references. |
| S | `shell_episodes` | References to separately assessed episodes; no injected live Shell flag. |
| φ | `phase`, `phase_evidence` | An assessed work phase, with event/debit evidence; unassessed is valid. |
| ι | `residual` | Exact event, queue and eligible-engagement observations. Continuous intensity has no elected scalar measurement law in R12. |

The state additionally references demands, opportunities, resources, material lineage, retained capacity revisions and trajectory events. It has no assignable altitude field. Recursive altitude can only be derived from separately established closure evidence in R20.

## Versioned records

| Record | Required content and safeguards |
| --- | --- |
| `DevelopmentalDemand` | Origin events and discovery evidence; required outcome and movement; context, participants, material, constraints, duration and resource conditions; ordered requirements; comparison protocol and optional prior demand. |
| `DemandComparison` | Current and prior identities, equal/greater/lesser/incomparable relation, exact changed requirements, and reason. |
| `Opportunity` | Demand, actor, delivery, interpretation, available operation, cost, resources, constraints, seat, queue entry and distinct eligible engagements. Delivery alone does not establish usable opportunity. |
| `MaterialTreatment` | Persistent material lineage, originating actor/events, current actor/treatment, carrier, previous revision, selection evidence, paid work and consequences. Cross-revision validation prevents rewritten origin or discarded provenance. |
| `DevelopmentalWork` | Owned input references, operator, formal movement, event/debit references, required/paid units, work status and outputs. A partial job cannot publish usable outputs; completed work requires full payment and a result. |
| `RetainedCapacity` | Holder, aspect, executable operator, exact contextual binding, lineage, acquisition debits, practice events, dependencies, current/superseded/withdrawn status and predecessor. R13 must enforce current availability during retrieval. |
| `ShellEpisode` | Demand/material scope, sign hypotheses, maintaining mechanism, eligible opportunities, trajectory, frozen protocol and relevant capacity revisions. An established status without evidence is rejected; assessment execution remains R16. |
| `ClosureEvidence` | Candidate and lower organizations, demand, finite repertoire, exhaustion versus censoring, alternatives tested, preserved lower capacity, new capacity/coherence evidence, minimality order and tied minima. A wrapper or censored search cannot establish closure. |
| `IdentityContract` | Declared state domain, discriminating features and control pairs, scoped by a versioned protocol. This does not claim the feature map is behaviorally adequate without its controls. |
| `ReturnProtocol` | Identity, actual transformation/return policies, applicability, resource/path conditions, sequences and optional equivalence-preservation proof. No proof is supplied for growing-world composition. |
| `AcceptanceEvidence` | Frozen protocol digest, exact case, status, execution kind and evidence references. Missing execution stays unassessed; fixture evidence cannot substitute for runtime evidence. |

`schema_description_v1.json` lists the complete dataclass fields and types. These records deliberately reuse the existing event, work, memory, binding, procedure, protocol and assessment kinds. In particular, a capacity is a revisioned owned memory carrying an executable procedure; a material treatment revision is memory content rather than a second world-object ownership system.

## Demand comparison

Requirements are nonnegative integers under an explicitly elected order: more temporal dependencies, simultaneous obligations or missing testimony imposes more of that requirement. The comparison is a conservative partial order. It applies only when the declared family, protocol, outcomes, movement, context, parties, lineage, constraints, duration length and resource envelope agree, and the same requirement dimensions are present.

All dimensions equal gives equal demand. Some increased and none decreased gives greater demand, with exact witnesses. The reverse gives lesser demand. Mixed changes or altered comparison scope gives incomparable. A different partner/context is useful generalization evidence, but is not automatically a harder instance. Starvation cannot be silently substituted for an increased requirement.

## Identity and evidence

Persistent actor/material identity, Identity card metadata, and IDEA κ have separate contracts. Card identity does not set a holon's personal meaning; κ does not redefine a material's origin. κ is fixed within a given assessment. Factual accuracy, identity preservation, path quality and retained capacity remain separate outcomes.

The exact OIG quotient definitions are recovered from the pinned 5.2.1 source. `LensContent` declares domain membership and foreign representatives, context and projection version. The observation function computes V, N, K=V\N and equality partitions R for a bounded offline path. It does not classify a Shell. Runtime projection from rich content into these representatives is an explicit R16 integration obligation; the structural reference comparison does not validate an arbitrary projection.

## R13 integration obligations

1. Resolve and authorize every new reference against the main journal and owned memory.
2. Integrate finite content operations and personally learned associations through paid contextual retrieval, revision and publication.
3. Extend the main codec to include pending jobs, receipts, queues, bindings, capacity dependencies and partial payments.
4. Continue interruption/retry without double debits or publication of unfinished results.
5. Preserve content aspect independently of sender activity and keep active element, Model A seat, perspective and capacity distinct.
6. Demonstrate held-out retrieval, different meanings from different histories, stale/withdrawn-capacity rejection, and exact continuation during partial work and memory revision.
