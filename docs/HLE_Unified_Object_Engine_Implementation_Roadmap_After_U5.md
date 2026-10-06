# HLE unified object engine: implementation roadmap

Version 1.5 · U5 completed · 21 September 2026

**Progress: 5/14 milestones complete. U1–U5 are complete; nine milestones remain. Next: U6 — bounded anticipation and continuing autonomy.**

The destination is the architecture in HLE_Unified_Object_Engine_Conception_v1.md. The implementation baseline is the supplied HolonicLivingEngine_Rebuild_R21B_v1(2).zip. This roadmap specifies how to carry the working mechanisms into that architecture, generalize their scope, and test the resulting behavior.

The central engineering task is to make identity, relations, operations, situated access, and retained change work consistently across the engine. Common representation must preserve the differences between a material object, someone's account of it, an executable procedure, and a collective obligation.

## 1. Starting position

The attached R21B report records 912 distinct passing tests, 60 development candidates and 60 separately constructed witnesses, with all 40 positive-budget episodes on each side completing. Its evidence summary identifies these as development executions and lists no held-out seeds used. The supplied handoff leaves R21C release, shared/population, and performance acceptance open.

U1 has now reproduced all 912 inherited tests, six declared candidate/witness pairs, and two controls on the unchanged source. All fourteen fresh raw transaction-stream digests match the retained same-case digests. Six inherited performance configurations and both current v4 checkpoint measurements passed their declared U1 checks. The remainder of the original 60-case development panel remains historical evidence. See HLE_Unified_U1_Report_v1.md and the U1 source/evidence packages. U2 now adds a separate versioned object layer and exact legacy adapters, with all eight U2 cases established and 102 distinct tests passing in its final targeted run. U3 establishes compact exact history and native situated access, with 134 distinct tests passing in its final run. U4 now establishes native paid operation execution and material interactions, with 179 distinct tests passing in its final run; all four U4 cases and all 22 new raw witness checks are established. U5 now establishes the integrated conceptual/material circuit with 289 distinct passing tests and all 28 new raw witness checks established. Earlier foundation and roadmap statements that implementation had not begun describe the September 16 preparation state, not this R21B baseline. The conception's reference to an earlier R21C source comparison does not establish R21C release acceptance for the supplied package.

| Existing mechanism | Evidence in the inspected runtime | Migration implication |
| --- | --- | --- |
| Common references and chronological events | contracts.py, world_records.py, world.py, codec.py | Extend existing identities, provenance, and replay to all object roles. |
| Exact particulars separated from conceptual tension | memory_records.py: DetailQuery; concept_records.py: ConceptState; conceptual.py | Preserve this implemented separation and generalize its content and bindings. |
| Stable conceptual references and an explicit Fold bridge | concept_structure.py | Preserve the reference meanings and lawful routes; replace the single entrusted-use conceptual specialization with extensible structures. |
| Paid Model A processing and partial work | processing.py, metabolism_records.py, paid_work.py | Establish a common lifecycle for operations while retaining costs, incomplete work, and actor-owned receipts. |
| Material lineage, carrier treatment, and acquired capacity | development_contracts.py, compensation_records.py, reconciliation_records.py, conversion_records.py | Extend lineage and executable treatment to arbitrary addressable targets. |
| Individuation, recurrence, and clearance evidence | individuation.py, clearance_runtime.py, clearance_shell.py | Reuse the demanding retention tests while widening the supported domains. |
| Participant language and organization | language_records.py, organization_records.py | Generalize finite semantics and procedures without losing receiver interpretation, consent, and actual performance. |
| Recursive/shared closure | closure_records.py, closure_policy.py | Preserve current witnesses; extend beyond the declared lower repertoire and two supplied extension constructors. |

All runtime paths in this roadmap are relative to HLE_Rebuild_R21B/hle/ inside the supplied archive.

## 2. Milestone overview

The order below is a usable default execution order. Dependencies identify what must be established before a milestone can finish.

| Step | Deliverable | Depends on | Completion evidence |
| --- | --- | --- | --- |
| U1 — Complete | Frozen baseline and migration contract | — | All 912 tests pass; six fresh candidate/witness pairs and two controls reproduce; baseline measurements, scope ledger, and migration contracts delivered. |
| U2 — Complete | Common versioned object substrate | U1 | All eight U2 cases established; 31 U2 tests and 71 applicable inherited tests pass. Immutable revisions, roles, occurrence categories, relation history, material lineage, finite references, and lossless adapters delivered. |
| U3 — Complete | Compact particulars and situated access | U2 | All three U3 cases established; 32 U3, 31 U2 and 71 inherited tests pass. Exact compact history, indexed particulars, actor-owned access and binding history, and hidden-state isolation delivered. |
| U4 — Complete | Common operation lifecycle and material interactions | U2–U3 | All four U4 cases established; 45 U4, 32 U3, 31 U2 and 71 inherited tests pass. Native paid effects, material reservations, explicit consumption, delayed evidence and exact replay delivered. |
| U5 — Complete | Integrated Fool's Memory, Model A, and Crux | U3–U4 | All three U5 cases established; 289 distinct tests and 28 new raw checks pass. One paid circuit links contextual recall, lawful type-dependent routing, perspective realization, repair, evidence, retained correction and later use. |
| U6 | Bounded anticipation and continuing autonomy | U5 | Predictions, motives, waiting, exploration, action, and stopping have explicit causes and costs. |
| U7 | Shell patterns across arbitrary targets | U5–U6 | A recurring deformation changes encounter and action across applicable object types, with clear negative controls. |
| U8 | Generalized retained development and correction | U6–U7 | Practice changes later capacity; local correction, wider generalization, residual bindings, and recurrence remain distinguishable. |
| U9 | Expandable concepts and procedure composition | U4–U8 | Participants construct and revise reusable relations and procedures beyond supplied complete answers. |
| U10 | Grounded language and shared meaning | U3, U9 | Receivers understand, question, and repair novel compositions through their own processing. |
| U11 | General nesting and collective capacity | U2, U4, U8–U9 | Aggregate behavior agrees with constituent work, resource ownership, dependency changes, and membership transitions. |
| U12 | Participant-generated institutions and public Shell consequences | U7, U10–U11 | Rules arise through communication and enactment, survive succession, and require actual collective work to change. |
| U13 | Measured storage and execution improvements | Instrument from U1; acceptance after U12 | Matched workloads demonstrate savings while preserving outcomes, access, history, and modeled costs. |
| U14 | Sustained evaluation and inspectable release | U1–U13 | Frozen-source behavioral, replay, accounting, population, and performance gates pass, with failures retained. |

**Useful stopping points:** U5 gives the first demonstration of the shared architecture. U8 gives the smallest integrated loop with anticipation, generalized Shell dynamics, and retained correction. U12 supplies the major capabilities in the conception. U13–U14 establish their measured efficiency and release scope.

## 3. Detailed implementation steps

### U1 — Freeze the baseline and define the migration contract

**Completed on 21 September 2026.** The following requirements are satisfied by the U1 source, evidence, and report packages.

Preserve the supplied archive, source hashes, protocol versions, historical failures, and continuing checkpoints. Reproduce the existing validation needed to establish the working baseline. Record exactly which checks run, their source version, results, and outstanding failures.

Create a mapping from current record families and policies to their target roles: preserve, adapt, generalize, or retain only for compatibility. Declare protected behavior: identity, observations, costs, partial work, capacities, obligations, and historical interpretation.

Freeze the first development cases and reserve separate evaluation cases. Specify the migration comparison rules and measure baseline cost before choosing numerical performance budgets. These budgets must be fixed before optimization is tuned against them.

Keep R21C's historical status explicit. If completed R21C evidence is supplied later, verify its source and contract before adopting it. Otherwise, completing the old release remains a separately named task if old-release certification is wanted. Migration may proceed from a verified development baseline; it must not claim that the unexecuted release panel passed.

**Done when:** the baseline can be reproduced, its open claims are recorded, and every proposed architectural change has a defined comparison or new acceptance case.

### U2 — Extend the common object substrate

**Completed on 21 September 2026.** The separate `hle_unified` namespace implements the common object records, atomic native journal, explicit material lineage, and read-only legacy adapters. All eight U2 cases are established. The final U2 run passes 31 new tests and 71 distinct applicable inherited tests, including 216 matched legacy action sequences within one new comparison test. A native witness and exact legacy partial/v4 checkpoint witnesses are retained. All 3,044 baseline members and 98 runtime modules remain unchanged. See `HLE_Unified_U2_Report_v1.md` and the U2 source/evidence packages.

The U2 structural material commands are simulator bookkeeping; generalized participant access and paid operation execution were assigned to U3 and U4 and are now established by those milestones. The compatibility bridge keeps the legacy runtime as its authoritative writer. The full 912-test U1 run and the original development panels remain historical evidence, and U13–U14 acceptance remains open.

Build on Ref, Record, Proposition, and the existing journal. Give material objects, concepts, procedures, observations, commitments, and collective organizations compatible identity and revision rules. Relations must be addressable when they need their own evidence, revision, or consequences.

Represent shared definitions separately from individual instances. Give division, combination, replacement, membership, and changed definitions explicit lineage. Add optional capabilities for material state, memory, agency, or governance; ordinary tools do not require a complete cognitive runtime.

Represent occurrence status explicitly: actual event, observation, remembered claim, hypothetical continuation, and interpretation. Keep this distinct from a participant's confidence or endorsement and from an evaluator's assessment.

Introduce adapters so current domain records can participate during migration. Select one authoritative writer for each migrated state; compatibility views must not become a second source of truth.

**Done when:** two identical-looking bowls remain distinct objects; a false prediction exists without becoming an actual event; a revised rule retains its prior meaning; and migrated legacy cases preserve protected behavior.

### U3 — Generalize efficient particulars and situated access

**Completed on 21 September 2026.** U3 adds a compact authoritative backend with verified structural sharing and version differences; indexed exact particulars; explicit rights, delivery and processing receipts; actor-specific interpretation and acquired-use evidence; and detached participant views. All three U3 acceptance cases are established. The final run passes 32 U3 tests, all 31 U2 tests and 71 distinct inherited regressions: 134 tests, with no failures, errors or skips. Eight hidden-state variants preserve pre-delivery views, reasons and choices. Exact historical views, partial processing and the complete U2 native witness reconstruct through the compact representation. All twelve U2 and fifteen U3 witness checks pass. See `HLE_Unified_U3_Report_v1.md` and the U3 source/evidence packages.

The U3 processing adapter verifies explicitly imported actor-owned evidence; U4 now provides the separate native paid executor. The contextual binding walk is an access primitive; U5 now integrates it with paid Model A and Crux realization in the finite workshop. On the retained native fixture, raw checkpoint bytes fall from 41,846 to 23,087, while gzip bytes rise from 2,317 to 2,974. U13 efficiency acceptance remains open. At U3 completion, all U2 execution files and the frozen R21B baseline were unchanged.

Retain indexed names, dates, ownership details, event references, and processing receipts. Extend conceptual bindings to refer to those particulars without making every fact a Fool's Memory traversal.

Share immutable definitions and verified repeated structures physically. Store each actor's access, interpretation, evidence, confidence, history, and acquired use separately. Introduce versioned state differences and dependency indexes where exact reconstruction is possible. Full historical segmentation and performance tuning continue in U13.

Create a consistent participant-view interface. It must assemble only information that the participant can access and process. A global dependency invalidation may invalidate an internal cache; it must not deliver a hidden fact, explanatory reason, or actionable signal to an actor.

**Done when:** participants can hold incompatible accounts of one object; changing a hidden fact alone cannot alter a participant's information or decision; historical meanings reconstruct exactly; and shared storage grants no unearned knowledge or skill.

### U4 — Unify operations and make material behavior extensible

**Completed on 21 September 2026.** U4 implements one native start/advance/commit/cancel lifecycle over exact object revisions, paid actor budgets and explicit accessible evidence. Transfer, inspection, use, care, return, damage, repair and consumption have declared material effects. Atomic whole-instance reservations prevent duplicate spending, live dependency checks reject stale effects while preserving charges, and return fulfills its exact obligation. Physical events, observation delivery, paid reading, interpretation binding and acquired use retain separate histories. All four U4 cases are established; the final run passes 45 U4, 32 U3, 31 U2 and 71 inherited tests: 179 distinct tests. All 12 U2, 15 U3 and 22 U4 witness checks pass. The frozen R21B baseline is unchanged. See `HLE_Unified_U4_Report_v1.md` and the U4 source/evidence packages.

Native finite-workshop prices, physical affordances and explicit consumption sinks are engineering choices. Existing legacy episodes retain their authoritative writer and contracts. The U4 compatibility route uses prepare/execution stages; U5 now adds integrated Fool's Memory–Model A–Crux realization through the same native lifecycle. Generalized retained competence remains U8, composition remains U9, and U13–U14 acceptance remains open. Operation checkpoints favor exact audit/replay and contain redundant state; no efficiency claim is made.

Specify one operation contract: actor and participants, input revisions, accessible evidence, preconditions, transformation, affected relations, required work, route, partial progress, and effects.

Reuse the existing paid-job discipline. Before committing an effect, check dependencies and relevant physical constraints. Retain spent work when continuation becomes invalid. Preserve effects already performed; a later conceptual revision cannot undo history. Material execution, observation delivery, interpretation, and retention can finish at different times.

Carry the current transfer, inspection, use, care, and return operations through this contract. Add a small declared set of material affordances needed for the workshop: condition change, wear, repair, and resource consumption. Distinguish conservation rules from explicit sources, sinks, or regeneration in the world contract.

**Done when:** an interrupted repair resumes or fails honestly, concurrent work cannot double-spend a tool or resource, and one causal lineage connects the physical effect to later evidence. A newly named procedure cannot perform an unsupported physical action.

### U5 — Integrate Fool's Memory, Model A, and the Crux

**Completed on 21 September 2026.** U5 supplies stable suit/rank/cue definitions, bounded contextual recall, explicit conceptual tension, lawful paid Model A routes, addressable Crux content surfaces and evidence-derived retained interpretation. Its native workshop links an assistance offer concerning one saw to a paid plan, actual repair, delayed evidence, account revision and later paid use. Removing integration changes the later choice to inspection. All three U5 cases are established. The final run passes 38 U5, 45 U4, 32 U3, 31 U2 and 143 inherited tests: **289 distinct tests**, with no failures, errors or skips. All 28 U5 raw witness checks pass, alongside the 12/15/22 U2/U3/U4 checks. All 16 types retain identical grounded action under matched input while the first plan's modeled cost varies from 21 to 34 units. See `HLE_Unified_U5_Report_v1.md` and the U5 source/evidence packages.

The finite prior association, communicated offer, prices and action repertoire are declared inputs or engineering choices. The participant derives its plan and corrected account from accessible evidence. Retention is an exact actor/item/property/context account, not generalized acquired competence. Numerical curvature, broader personality validity, U6–U14 and R21C release acceptance remain open. All 3,044 frozen baseline members remain unchanged. The inherited entrusted-use prototype passes as a regression witness.

Make conceptual tension, contextual retrieval, perspective movement, and paid realization operate on the same object references.

Carry forward stable suit, rank, and cue identities. Preserve supplied reference meanings and mark unspecified meanings as unspecified. Permit each participant's situated associations and distortions to change through experience. Generalize the entrusted-use prototype while retaining it as a regression witness.

Use Model A to determine lawful processing paths and costs. Use Crux origin, destination, and polarity to specify the perspective relationship actually realized. Preserve the Fold bridge, including the absence of single-function I–IT and WE–ITS edges. Keep function dimensionality distinct from cube coordinates.

Build an inspectable workshop demonstration: an offer of assistance concerns an identified tool; a participant recalls applicable conceptual relations; paid work produces a physical consequence; delivered evidence revises the account; later behavior uses the retained change.

**Done when:** an inspector can follow that complete circuit without disconnected copies, unexplained state changes, or an evaluator supplying the answer. The 4D–3D–2D–operation ordering has operational responsibilities; a numerical curvature law remains open.

### U6 — Add bounded anticipation and continuing autonomy

Represent candidate continuations, expected consequences, uncertainty, and prediction error explicitly. Generate them from accessible memory and acquired procedures, charge their work, and preserve their hypothetical status.

Extend the existing participant scheduler to support continue, switch, ask, inspect, explore, rest, wait, and stop. Waiting must name the event, observation, or resource that could make work feasible. Unfinished thought and action must survive checkpoint restoration.

Give pressure, fear, fatigue, scarcity, and boredom explicit causes and limited effects on attention, urgency, available work, and exploration. Any recovery through food, rest, or replenishment belongs to a new versioned world contract; R21B's finite episode budgets keep their original meaning.

**Done when:** anticipation changes an affordable decision; a received surprise can trigger investigation; unavailable evidence causes waiting; repeated failure can change strategy; and need variables never award skill or development merely by increasing.

### U7 — Generalize Shell patterns and their target bindings

Represent a persistent deformation as a reusable pattern with owner, origin, triggers, executable effects, evidence, maintenance history, and context-specific target bindings. Keep the projecting participant, target, material carrier, and consequence bearer separately identifiable.

Support targets that are tools, people, groups, rules, memories, possibilities, actions, or relations. A target does not need a mind. Multiple participants can maintain incompatible projections onto the same object.

Implement a small initial language of deformation: unsupported obligation attribution, changed salience, altered forecast, exclusion of an otherwise available route, or added approval requirements. Declare these as operational choices and keep the language extensible.

Extend the demand-conditioned assessor. Separate accurate threat recognition, missing knowledge, insufficient resources, partner refusal, ordinary disagreement, and defensive maintenance.

**Done when:** one pattern transfers across distinct applicable targets and leaves unrelated targets unaffected; deformations cause observable changes in processing or action; generated histories are distinguished from injected detector fixtures; and assessment labels remain outside participant access.

### U8 — Make correction become retained, scoped capacity

Generalize release, contextual expansion, reorganization, practice, and reownership beyond the original loan domain. Preserve the original material's lineage through treatment, displacement, and regained ownership.

Allow counterevidence to revise a local binding while related bindings persist. Broader change must follow applicable experience and an altered reusable organization. Teaching or temporary support can enable performance without conferring independent mastery.

Reuse the existing demanding withdrawal, changed-partner, renewed-demand, and later-opportunity tests. Assess factual accuracy, useful capacity, pathway quality, and retained access separately. Use the Canon's declared identity features and return protocols; one endpoint cannot establish closure across arbitrary repeated operations.

**Done when:** the same or a harder declared demand can be handled through retained capacity after support is removed; local repair does not automatically clear every binding; residual recurrence is visible; and neither forgetting the problem nor a quiet interval counts as clearance.

### U9 — Expand participant-generated concepts and procedures

Replace complete scenario-answer menus with a bounded constructive language over acquired operations and accessible relations. Support relations, conditions, sequences, alternatives, and reusable subprocedures with explicit effects and dependencies.

Make new demands arise from discrepancies and persistent consequences. Let participants search existing capacities first, compose an extension, test it, retain useful results, and revise or split overbroad concepts when counterexamples arrive.

Each search remains finite and paid, but the representation must permit further funded work to extend its retained complexity. Preserve unfinished search. Report exhaustion only within the enumerated repertoire; running out of budget does not establish that no existing solution exists.

**Done when:** a participant creates a useful composition absent as a complete supplied answer, applies it in a held-out context, and revises a failed generalization. Changing evaluator labels or object names cannot supply the solution.

### U10 — Extend grounded language and shared meaning

Use the same referents and procedures for statements, conditions, questions, requests, explanations, intentions, and commitments. Expand the existing finite language without bypassing its grounding.

Track intended meaning, wording, receiver interpretation, and practical response separately. Learning a term requires the receiver's own access and processing. Misunderstanding must support questions, demonstrations, counterexamples, and revised use.

Introduce new vocabulary when a distinction is useful and sufficiently stable under the declared learning rule. Optional fluent wording can express established actor state; it must not write invented memories, agreements, actions, or skills into the simulation.

**Done when:** a novel composition changes another participant's behavior appropriately, and an ambiguous or incorrectly generalized term produces meaningful repair rather than automatic agreement.

### U11 — Implement general nesting and collective capacity

Generalize the current recursive/shared closure machinery using the conception's explicit coherence contract.

Every composite names its members, boundary conditions, resources, versioned summary, and dependencies. A collective action must decompose into actual work or use explicitly modeled collective effects. Overlapping membership is allowed, while ownership prevents double counting.

Specify which observations and interventions an aggregate summary supports. Resolve required detail before committing effects when the summary is insufficient. Retain recoverable detail or valid deterministic reconstruction; never invent discarded history.

Keep shared competence distinct from member competence. A participant can hold a representation of its organization through finite references without copying the entire organization recursively.

**Done when:** detailed and aggregate execution agree within the declared scope; child changes invalidate the correct parent results; membership changes preserve real duties and permissions; and a newcomer does not inherit skills merely by joining.

### U12 — Let institutions and public Shell consequences develop

Let independently adapting participants propose commitments and procedures, communicate reasons, negotiate, consent, enact, revise, teach, and dissolve them. Build from generic capabilities rather than providing a finished institution as the desired answer.

Allow a personal deformation to influence a message or action, gain uptake, become repeated practice, and acquire a maintained public rule. Preserve that causal sequence and the identities of participants who bear its consequences.

Collective correction must change commitments and practices through actual participation. One member changing an expectation does not erase a real rule. Include disagreement, refusal, legitimate boundaries, founder departure, newcomer teaching, and disputes.

**Done when:** an institution originates through participant operations, persists through relevant membership change, and is revised through collective work; personal correction and institutional correction can diverge without inconsistency.

### U13 — Demonstrate efficiency without losing meaningful differences

Instrumentation and economical schemas begin in U1–U3. This milestone profiles the completed feature set and accepts or rejects the efficiency claims.

Measure live memory, active processing, evaluator work, queues, compressed checkpoints, restore time, archival bytes, and historical reconstruction separately. Compare the common workload against frozen R21B, including its compressed checkpoints. For new capabilities, compare the optimized runtime against a straightforward reference implementation with the same capabilities.

Use verified shared definitions, instance differences, local binding differences, dependency-driven invalidation, segmented history, and event scheduling. Reuse only completed actor-owned work whose context and dependencies remain applicable. Lossy summaries need a declared observational scope and error policy.

Hold active work fixed while increasing inactive history. Also vary unique histories, dense interactions, and heavily shared structures. Account separately for actual machine savings and simulated energy/time; optimization cannot silently lower Model A prices.

**Done when:** preregistered matched comparisons meet the chosen cost budgets and show a measured improvement, while protected behavior, information access, reconstruction, and modeled accounting remain intact. A compact encoding alone is insufficient.

### U14 — Run sustained evaluation and deliver the inspectable engine

Freeze the final source, world contracts, participant policies, panels, and thresholds before release runs. Use genuinely held-out combinations of histories, types, target objects, partners, resources, and interaction patterns.

Carry forward all applicable regression obligations. Run new generalization, independent-accounting, partial-work, checkpoint, nesting, language, institutional, autonomy, and performance evaluations against that exact source.

Keep the old release contract distinct. If claiming R21C compatibility acceptance, its specified 16 TIM × 10 fresh seeds × 3 regimes panel, positive-regime witnesses, thirteen challenges, 100 later opportunities, two changes, and remaining gates must be satisfied under that contract. Those counts do not automatically define an adequate new-engine evaluation.

Deliver the source, versioned specification, complete evidence including failures and partial episodes, reports, and an inspector for the workshop demonstration.

**Done when:** the release report identifies which new-conception properties passed under which conditions, all required gates are satisfied, and unsupported claims remain explicitly open.

## 4. One demonstration carried through the milestones

Use the workshop in the conception as a continuing integration case.

A saw has actual condition, custody, and maintenance requirements. Three participants have different histories concerning assistance, control, care, and agreed responsibility. The initial histories are declared experimental inputs; subsequent decisions must come from the runtime.

| At milestone | What the demonstration should establish |
| --- | --- |
| U5 | One causal history connects the saw, the offer, a participant's interpretation, paid repair, and retained change. |
| U6 | Participants anticipate different consequences and can ask, inspect, act, wait, or decline for traceable reasons. |
| U7 | An applicable defensive pattern can bind to assistance with the saw and another object or relationship, while a valid boundary remains distinguishable. |
| U8 | Limited successful collaboration changes one binding; broader revision and remaining recurrence require separate evidence. |
| U9–U10 | Participants form a conditional distinction, compose a useful procedure, explain it, and repair a misunderstanding. |
| U11–U12 | A maintenance practice becomes a collective arrangement, survives membership change, and can transmit or correct a projection's public effects. |
| U13–U14 | The same process survives restoration, longer runs, changed resources, additional participants, and measured optimization. |

Add distinct material contexts and negative controls before using this scene as evidence of generality. Its purpose is to make integration visible, not to become the only situation the engine can solve.

## 5. Tests that protect the intended conception

| Risk | Required check |
| --- | --- |
| Shared storage merges personal identity | Identical objects and shared definitions retain separate instances, histories, access, and competence. |
| A hypothesis becomes world truth | Prediction, observation, interpretation, and actual occurrence remain distinguishable through execution and replay. |
| Hidden information affects a decision | Matched runs vary a hidden fact while holding the actor's available state constant; no premature information or decision difference is permitted. |
| Geometry becomes decorative | Route or capacity changes have measurable processing consequences; labels alone cannot satisfy a behavioral gate. |
| Shells become universal disagreement labels | Include ignorance, legitimate threat, adequate refusal, lack of opportunity, insufficient capacity, fatigue, and low resources. |
| Correction deletes the history | Original material, prior interpretations, consequences, spending, and surviving bindings remain recoverable. |
| Type determines a scripted personality | Compare matched types, histories, observations, and resources; disable individual mechanisms to identify what caused differences. |
| Search failure is called necessary development | Preserve search coverage, missing capacities, budget stops, equal alternatives, and unassessed cases. |
| Aggregate success conceals constituent failure | Independently reconstruct member work, consent, resource ownership, and parent effects. |
| Language invents capabilities | Trace every effective utterance to actual sender and receiver state and to executed operations. |
| Optimization grants free learning | Compare actor-owned acquisition and processing ledgers before and after storage or cache changes. |
| A finite panel becomes an unlimited claim | Report the actual domains, horizons, populations, budgets, constructors, and failed cases. |

## 6. Source constraints and open research

The conception governs this migration's destination. The foundation's authority distinctions continue to apply: source-defined structure, user clarification, implementation choice, and open mechanism must remain identifiable.

The source review used all seven supplied theoretical documents for their relevant constraints:

- Fools_Memory_Path_Manual (1).docx: stable card and suit organization, personal associations, distinction between rank and folded position, and unspecified Id/Identity traversal. The conception's explicit conceptual-tension direction governs the present use.
- A_Unified_Mathematical_Architecture_of_Socionics_Verified_Revision.docx: conditional Model A mathematics, distinct positional and element spaces, and a separation between accepted structures and proposed dynamic completions.
- Archetypal Shadow Complex - The Crux in the Locus of Control.docx: subjective projection, ownership, and relational interpretation. This source does not itself supply the arbitrary-target runtime schema.
- Unified_Shell_Geometry_and_Developmental_Dynamics_Readable_Edition.docx: demand-conditioned assessment, horizontal adaptation versus proposed higher closure, complementary retention, recurrence, and absence of compulsory fixed developmental tiers.
- A_Fresh_Perspective_on_Disorder.docx: preservation of material through conversion, demand sensitivity, and explicit distinctions among formal, definitional, and interpretive claims.
- Dense_Consciousness_Developed_Edition_v6_0.docx: retained complementary capacity under load and the status limits of mechanisms inherited from earlier kernels. Its earlier implementation claims do not automatically become new-runtime rules.
- Canon_of_Permanent_Truth_IDEA_v2_1_Corrected.pdf: predeclared identity features, failures and unassessed cases, endpoint versus path checks, and the equivalence-respecting condition required for generator tests to establish compositional closure.

The conception names additional sources such as the Kindred Fold and later Crux and memory documents. This roadmap uses the supplied conception's stated requirements and the inspected runtime bridge; it does not claim a fresh verification of every named external source or of their broader physical or psychological interpretations.

Three research questions remain explicit: a numerical account of the proposed 4D geometry, general Shell recognition across arbitrary domains, and broad equivalence guarantees for aggregation and generated transformations. Bounded executable contracts allow the migration to proceed while those wider claims remain open.

A 3D client, unrestricted natural-language fluency, and unlimited developmental complexity are not acceptance shortcuts. The common architecture should support later world expansion, while every demonstrated capability retains a stated scope.

## 7. Delivery and progress tracking

At each completed milestone provide:

1. A runnable source package with its source identity.
2. A versioned specification of changes and protected behavior.
3. Evidence with configurations, commands, outcomes, failures, and incomplete work.
4. A concise report of what passed and what remains open.
5. An updated roadmap with the exact completed and remaining milestone count.

If a milestone needs to split, publish its named substeps before treating the parent as complete. Earlier verified capacities remain credited, but a new representation does not inherit a validation claim merely through similar terminology.

**Current transition status: 5/14 milestones complete. Nine remain. Next: U6 — bounded anticipation and continuing autonomy.**

