# HLE new-build foundation

Version 1.0 · 16 September 2026

**Preparation is complete. Implementation has not begun.** This handoff defines the rebuild around the clarified Fool's Memory model, Crux transformations, Model A and Socion exchanges, and a simulator-owned Truth record. The corrected IDEA Canon is included as the assessment specification.

The first target is a small, inspectable simulation. A reader must be able to follow an event through observation, memory, interpretation, action, consequence, and retained correction. Language, institutions, and larger populations follow after that process works.

## 1. Source authority and status

The user's clarifications in the current conversation govern the integration where earlier documents describe a narrower or different model. Documents govern only the mechanisms they actually define. Code and passing tests establish implementation behavior under their assumptions; they do not establish those assumptions as true.

Every substantive rule in the new implementation must identify one of these statuses:

| Status | Meaning |
| --- | --- |
| Source-defined | Explicitly supplied by an identified document, with its original claim grade preserved. |
| User clarification | A modeling direction stated in the present discussion. |
| Implementation choice | An engineering or operational definition selected for the rebuild and open to comparison. |
| Open | A mechanism or correspondence that the sources and conversation do not establish. |

An implemented hypothesis remains a hypothesis. A unit test cannot promote it to a derived result.

Read `Source_Decisions.md` for the source decisions and `Source_Manifest.json` for original filenames, packaged paths, and SHA-256 hashes. The primary source set and original 5.2.1 archive are included unchanged. Other project papers are preserved as references; their presence does not activate all their rules.

## 2. One process, several descriptions

| Component | Role in the rebuilt system | Status of the integration |
| --- | --- | --- |
| Fool's Memory | Retained relationships, cues, contexts, associations, and access to content; navigation competence varies independently of the existence of this organization. | Manual plus user clarification; executable navigation policy still to be specified. |
| Crux | Origin, destination, polarity, and the realized transformation of content between I, IT, WE, and ITS. | Route grammar is source-defined; content operators need explicit implementation. |
| Model A | Type-dependent routing, processing, retention, and resource accounting within each holon. | Reuse checked structural mathematics selectively; operational effects require tests. |
| Socion | Exchanges among differently organized participants, with distinct observations, histories, resources, and responses. | Source framework plus implementation choices for exchange. |
| OIG and Shell assessment | Demand and trajectory evidence: activation, cancellation, retained change, recurrence, carrier behavior, and persistent distortion. | Source-defined framework; detailed detectors remain proposed operationalizations. |
| Truth | Simulator-owned history and relational views of what the declared world actually establishes. | User-requested reference plus proposed engineering design. |
| IDEA | Explicit tests of identity preservation under declared transformations and returns. | Corrected Canon v2.1, with application-specific definitions still required. |

These are views and operations over linked state, not seven copies of every fact. One causal event may support several views through stable references.

### Distinctions that must survive implementation

- A card's rank, folded location, and associated content are separate. The nine-location fold does not imply 720 independent cells, one memory per card, rank measured by edge count, or an obligatory three-vertex replay.
- The organization operates without deliberate cursor skill. Unmanaged activity alone does not establish a Shell.
- Crux route labels describe transformations. Merely renaming a packet Theorize or Embody does not implement one.
- The Crux route table is origin-by-destination. IDEA's grid is phase-by-perspective. Their two sets of sixteen cells are different objects.
- Map perspectives by their labels and meanings. The Canon's listed order I, We, It, Its differs from the Crux two-bit order I, IT, WE, ITS.
- A formal inverse route does not automatically recover lost information, undo a consequence, or refund resources. An actual return protocol must do the required work.
- A type influences processing; it does not prescribe every decision, a private route system, or a predetermined developmental outcome.

## 3. Minimal state and boundaries

The following is an implementation contract, not a claim that the documents derive one unique schema.

| Record | Required contents |
| --- | --- |
| World event | Stable ID, logical time/order, actors, affected objects, action, relevant before/after facts or reconstructible changes, context, and causal links actually supported by the world rules. |
| Observation | Observer, source event or message, delivered content, delivery time, visibility limits, and any explicitly modeled noise or uncertainty. |
| Individual memory | Addressable content and relationships; actor/object referents; context and time scope; cue bindings; claim status; observation provenance; revisions; retained capability where applicable. |
| Movement | Holon, demand, origin/destination/polarity, content references, preconditions, selected operation, processing history, costs, outcome, and retained changes. |
| Assessment | Versioned identity criterion, protocols and their domains, predeclared comparison rules, evidence, result, and scope of the claim. |
| Resources | Available amounts, actual charges, incomplete work, and explicit failures or deferrals. |

The Truth record uses the same referents and relationship vocabulary as individual memories. It records that a holon holds a belief separately from whether the belief's content agrees with the world. Its authority extends to facts established by this simulation; it is not an oracle for undeclared meanings, hypothetical causes, or the validity of the entire theory.

Holons receive observations and messages through explicit interfaces. They do not read Truth state, evaluator conclusions, another holon's private memory, or a hidden future. The evaluator may inspect simulated internal processes for assessment, but those observations must not leak back into participant decisions.

The truth history records events once. Relational views reference those events. Retention, archiving, and later compaction must retain the evidence needed for promised comparisons and replay. A correction to a world record must be explicit and must invalidate affected assessments.

## 4. The first worked circuit

Use a small resource world with visible actions and unequal access to information. A simple ownership transfer provides a checkable starting case; a small intervention task provides a second case for learned causal claims.

1. A resource transfer occurs. The world records the giver, recipient, object, and time.
2. One holon sees an incomplete part of the event and forms an uncertain account. Another witnesses the transfer.
3. The first holon uses its relational memory to retrieve relevant content and forms an explicit account of what happened. Theorize must create a checkable claim or procedure with referenced evidence.
4. Apply selects a concrete action from that account. The action has costs and observable consequences.
5. The holon receives relevant testimony or direct evidence through a permitted channel. Delivery, consideration, and retention are separately observable.
6. Embody changes retained understanding or usable capacity when warranted. The next comparable demand tests whether that change remains available.
7. Exchange with the other participant affects the process through that participant's own memory, processing, and resource state.

The I → ITS → IT → I circuit is a selected demonstration, not a mandatory universal recall order or developmental sequence. Source-defined route names constrain what each operation is intended to accomplish. The implementation must exhibit those consequences.

Introduce at least one held-out situation. Repeating a scripted answer in the identical setup is insufficient evidence of a reusable capacity.

## 5. What the corrected Canon adds

**Include Canon v2.1 as a required assessment reference.** It specifies how to make a return claim precise, while requiring the application to supply the state, identity features, and actual operations. It does not generate the world's dynamics or determine Fool's Memory navigation.

For a declared state x, a transformation f, return policy r, and identity feature map κ, the tested return condition is:

`κ(r(f(x))) = κ(x)`

The implementation must meet the following obligations from the Canon:

1. Specify the state space, identity features, transformation/return policies, input domains, and relevant memory/resources before evaluating success. An unavailable or inapplicable operation must be represented explicitly.
2. Preserve failures. Do not remove an unsuccessful protocol from its family after seeing the result, or change κ to erase the failure. Revised assessments receive new versions.
3. Use established, failed, and unassessed as evidence statuses. A missing test is not a pass.
4. Separate preservation at a completed endpoint from conditions on the path. Resource use, hidden compensation, time limits, and intermediate violations require their own checks.
5. Treat generator tests as covering all finite composites only when the equivalence-respecting condition in §6, Equation 17, is proved for the relevant model/domain. Otherwise report the sequences actually evaluated and leave general closure unestablished.
6. Do not use approximate equality as if it were the equivalence relation in that theorem. Approximate error and its accumulation need separate bounds.
7. Do not assume finite-state termination for a growing simulation. The Canon's finite bound is not an efficient runtime algorithm.
8. Distinguish the IDEA assessment filter from a learning or candidate-generation process. The Canon explicitly treats generation as a separate operation.

**Stability is not factual correctness.** A persistent false account can preserve its identity. A corrected account can change its previous identity while becoming more accurate. Track at least three separate outcomes: agreement with the world, preservation of a declared useful capacity, and the cost/path of its realization.

Choose identity features appropriate to the claim. Preserving the ability to check ownership is different from preserving a particular false accusation. A constant or overly coarse feature map can make every test pass without establishing anything useful.

The Canon supplies no missing proof of recursive Cross coherence, no card-to-Crux correspondence, and no Id/Identity traversal. Those remain open.

## 6. Distortion and Shell assessment

First align claims by referent, relation, context, and relevant time. Graph shape alone is insufficient: replacing one person's identity with another can preserve connectivity while changing the claim.

Keep these measurements separate:

| Measurement | Proposed operational meaning |
| --- | --- |
| Checkable factual disagreement | Contradicted claims divided by claims the declared world semantics can adjudicate; report the numerator and denominator. |
| Unresolved claims | Claims whose interpretation or world evidence does not permit adjudication; never silently treat them as correct or incorrect. |
| Coverage | Relevant available/delivered information and relevant retained information, using a declared comparison set; distinguish information never observed. |
| Relational disagreement | Wrong actors, ownership, sequence, context, or causal claims, with the disputed links identified. |
| Revision and retention | Whether suitable evidence changes a claim or procedure, whether that change persists, and whether it helps on a later comparable demand. |
| Compensatory work | Actual recurring processing, actions, suppression, displacement, or defensive reconstruction needed to maintain an account. |

Do not combine these into one arbitrary score during the first demonstrator. A rate with zero adjudicable claims is unassessed. Remembering almost nothing must not look like perfect accuracy.

Within this model, a Shell candidate requires a specified demand and evidence of self-maintaining distortion or prevented movement through the relevant correction/return process. Corrective evidence must be interpretable and available under the tested resource conditions; mere delivery is not proof that a holon could use it.

The sources identify premature translation, forced placement, new defensive structure, residual fragmentation, and, in Unified Shell Geometry, foreclosure. Each sign needs an operational definition and a traceable witness. No inactivity-only detector is acceptable: rest and foreclosure can share the same observed trajectory.

For projection/repression, preserve the causal chain when it is actually produced by the model: internally generated material, its access/ownership treatment, selection of an external carrier, action toward that carrier, consequence, and later displacement or re-ownership. An ordinary mistake about another participant does not by itself demonstrate that chain.

Shell clearance requires renewed demand and retained correction or capacity, with the relevant persistent distortion reduced or absent under the declared assessment. A correct final answer, one quiet interval, a reset, or a route label does not establish clearance. Detector fixtures and deliberately injected failures may test assessment behavior; claims of generated Shells require separate runs in which the pattern arises through the implemented dynamics.

## 7. Acceptance panel for the first integrated demonstrator

These are planned checks, not executed results.

| ID | Case | Required distinction or evidence |
| --- | --- | --- |
| A01 | Cue reuse | One cue accesses different memories in different contexts; one memory can have several cues. |
| A02 | Variable recall structure | Useful retrieval works without requiring exactly three vertices or a fixed universal replay order. |
| A03 | Observation isolation | Hidden facts cannot change a holon's action unless a permitted information path conveys them. |
| A04 | Wrong actor, same shape | The evaluator catches a referent substitution despite identical graph connectivity. |
| A05 | Ordinary ignorance | Missing observations produce uncertainty/limited coverage and do not alone count as a Shell. |
| A06 | Resource-limited correction | Insufficient time or energy is recorded as a limitation; distinguish it from persistent defensive rejection with adequate opportunity. |
| A07 | Stable false account | An identity-return test may pass while factual agreement fails. Both results remain visible. |
| A08 | Correct endpoint, distorted path | Returning a correct answer does not conceal persistent compensation or invalid carrier treatment. |
| A09 | Rest and foreclosure | Matched quiet trajectories receive different assessments only when demand and opportunity evidence justify the distinction. |
| A10 | Retained correction | Corrective experience changes a later action on the same demand and a held-out comparable case. |
| A11 | Projection and re-ownership | Trace the material-to-carrier-to-action chain and test whether correction changes its later use. |
| A12 | Model A participation | Trace structural routing and cost effects under controlled exchanges; distinguish type effects from different observations or random seeds. |
| A13 | Return composition | A passing single return that fails on repetition remains a failure of the broader claim; the Canon's three-state counterexample is a useful assessor fixture. |
| A14 | Continuation | Save/reload reproduces complete relevant state, further actions, costs, and assessments with the same inputs. |
| A15 | Incremental evaluation | Changed-state comparisons agree with an independent complete comparison on a bounded fixture, while unaffected inactive history is not traversed every tick. |

Predeclare seeds, horizons, resource conditions, definitions, and pass criteria before each implementation evaluation. Inspect failures before extending the panel. Do not claim emergence from a fixture that assigns the desired outcome directly.

## 8. Efficiency and evidence rules

Use stable addresses for reusable structure and provenance. Retain the context, binding version, or override needed to reconstruct its historical meaning. An address into today's mutable owner state is insufficient for yesterday's event.

Schedule work from changed events, memory links, obligations, and resource availability. Reassess only affected claims during ordinary ticks. Use complete comparison and replay offline to check the incremental machinery. Do not add a full-history scan merely to compute a convenient metric.

Measure action-processing cost, evaluator cost, checkpoint cost, active work, retained history, queue growth, and stored bytes separately. Hold active work fixed while varying inactive history to reveal hidden scaling. State hardware and workloads; do not promise efficiency from design alone.

Log enough to reconstruct contested results. Use references and compact provenance where sufficient. Archival growth is a real cost even if active processing remains stable. No unconditional bounded-memory or unrestricted-complexity claim is made.

## 9. Open mechanisms and their gates

| Open question | Current handling | Gate |
| --- | --- | --- |
| Id versus Identity and the repeating cycle | Preserve the source labels; do not invent a Sun → Judgement → World traversal. | Any implementation that uses that cycle. |
| Full navigation/link-selection rule | Specify an experimental policy, separate from the fixed cue arrangement, and compare it against worked examples. | R3 and its acceptance checks. |
| Card relationships to Crux movements | Retain distinct coordinates; an explicit, testable mapping must justify any connection. | R4; claims about deeper correspondence remain open. |
| Recursive Cross coherence | Candidate abstraction and composition rules must be labeled as proposals. Parent/child coherence cannot be assumed from route closure. | R7. |
| Individual Shell signs to OIG patterns | Use joint demand/trajectory evidence; do not claim a unique detector from K or R alone. | R5 and later detector extensions. |
| Identity features for learned organizations | Choose discriminating features per assessment and version changes. | Each IDEA assessment. |
| Developmental selection | Define operationally what capacity is retained and what new demand it meets; do not import a mandatory color progression. | R5/R7 and beyond. |

These open points need not prevent the small demonstrator. Its conclusions must remain within the mechanisms actually specified and tested.

## 10. Handoff status

**R0 foundation preparation: complete. New implementation: 0/10 milestones complete; 10 actionable steps remain. Next: R1 — isolate the reusable mathematical core and establish the new contracts.** See `HLE_New_Build_Roadmap_v1.md`.

The former build remains historical reference. Its last reported position was 12A.1e.4 complete, parent progress 4/14, 11 actionable steps remaining, and efficiency acceptance open. That track is paused by the rebuild decision; none of its successes or open work is silently relabeled as completion of this new plan.

This package contains source material, a specification, an acceptance plan, and previously recorded baseline evidence. It contains no implemented replacement engine and no new runtime acceptance results.
