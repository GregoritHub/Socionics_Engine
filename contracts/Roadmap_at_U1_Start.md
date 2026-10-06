# HLE unified object engine: implementation roadmap

Version 1 · 21 September 2026

**Recommended sequence: 14 implementation milestones, U1–U14.** Planning is complete; none of these implementation milestones is marked complete by this document.

The destination is the architecture in HLE_Unified_Object_Engine_Conception_v1.md. The implementation baseline is the supplied HolonicLivingEngine_Rebuild_R21B_v1(2).zip. This roadmap specifies how to carry the working mechanisms into that architecture, generalize their scope, and test the resulting behavior.

The central engineering task is to make identity, relations, operations, situated access, and retained change work consistently across the engine. Common representation must preserve the differences between a material object, someone's account of it, an executable procedure, and a collective obligation.

## 1. Starting position

The attached R21B report records 912 distinct passing tests, 60 development candidates and 60 separately constructed witnesses, with all 40 positive-budget episodes on each side completing. Its evidence summary identifies these as development executions and lists no held-out seeds used. The supplied handoff leaves R21C release, shared/population, and performance acceptance open.

These are reported historical results. This planning review inspected the source, report, and packaged development summary; it did not rerun the experiments or independently audit every raw trace. Earlier foundation and roadmap statements that implementation had not begun describe the September 16 preparation state, not this R21B baseline. The conception's reference to an earlier R21C source comparison does not establish R21C release acceptance for the supplied package.

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
| U1 | Frozen baseline and migration contract | — | Identified source, reproducible baseline checks, scope ledger, and declared evaluation rules. |
| U2 | Common versioned object substrate | U1 | Identity, revisions, first-class relations, roles, and legacy adapters work without merging distinct instances. |
| U3 | Compact particulars and situated access | U2 | Shared structure preserves separate histories, observation rights, conceptual bindings, and exact retrieval. |
| U4 | Common operation lifecycle and material interactions | U2–U3 | Paid, resumable operations produce actual effects, delivered evidence, and dependency-aware results. |
| U5 | Integrated Fool's Memory, Model A, and Crux | U3–U4 | One workshop event changes material state, a participant's conceptual account, and later action through a traceable circuit. |
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

Preserve the supplied archive, source hashes, protocol versions, historical failures, and continuing checkpoints. Reproduce the existing validation needed to establish the working baseline. Record exactly which checks run, their source version, results, and outstanding failures.

Create a mapping from current record families and policies to their target roles: preserve, adapt, generalize, or retain only for compatibility. Declare protected behavior: identity, observations, costs, partial work, capacities, obligations, and historical interpretation.

Freeze the first development cases and reserve separate evaluation cases. Specify the migration comparison rules and measure baseline cost before choosing numerical performance budgets. These budgets must be fixed before optimization is tuned against them.

Keep R21C's historical status explicit. If completed R21C evidence is supplied later, verify its source and contract before adopting it. Otherwise, completing the old release remains a separately named task if old-release certification is wanted. Migration may proceed from a verified development baseline; it must not claim that the unexecuted release panel passed.

**Done when:** the baseline can be reproduced, its open claims are recorded, and every proposed architectural change has a defined comparison or new acceptance case.

### U2 — Extend the common object substrate

Build on Ref, Record, Proposition, and the existing journal. Give material objects, concepts, procedures, observations, commitments, and collective organizations compatible identity and revision rules. Relations must be addressable when they need their own evidence, revision, or consequences.

Represent shared definitions separately from individual instances. Give division, combination, replacement, membership, and changed definitions explicit lineage. Add optional capabilities for material state, memory, agency, or governance; ordinary tools do not require a complete cognitive runtime.

Represent occurrence status explicitly: actual event, observation, remembered claim, hypothetical continuation, and interpretation. Keep this distinct from a participant's confidence or endorsement and from an evaluator's assessment.

Introduce adapters so current domain records can participate during migration. Select one authoritative writer for each migrated state; compatibility views must not become a second source of truth.

**Done when:** two identical-looking bowls remain distinct objects; a false prediction exists without becoming an actual event; a revised rule retains its prior meaning; and migrated legacy cases preserve protected behavior.

### U3 — Generalize efficient particulars and situated access

Retain indexed names, dates, ownership details, event references, and processing receipts. Extend conceptual bindings to refer to those particulars without making every fact a Fool's Memory traversal.

Share immutable definitions and verified repeated structures physically. Store each actor's access, interpretation, evidence, confidence, history, and acquired use separately. Introduce versioned state differences and dependency indexes where exact reconstruction is possible. Full historical segmentation and performance tuning continue in U13.

Create a consistent participant-view interface. It must assemble only information that the participant can access and process. A global dependency invalidation may invalidate an internal cache; it must not deliver a hidden fact, explanatory reason, or actionable signal to an actor.

**Done when:** participants can hold incompatible accounts of one object; changing a hidden fact alone cannot alter a participant's information or decision; historical meanings reconstruct exactly; and shared storage grants no unearned knowledge or skill.

### U4 — Unify operations and make material behavior extensible

Specify one operation contract: actor and participants, input revisions, accessible evidence, preconditions, transformation, affected relations, required work, route, partial progress, and effects.

Reuse the existing paid-job discipline. Before committing an effect, check dependencies and relevant physical constraints. Retain spent work when continuation becomes invalid. Preserve effects already performed; a later conceptual revision cannot undo history. Material execution, observation delivery, interpretation, and retention can finish at different times.

Carry the current transfer, inspection, use, care, and return operations through this contract. Add a small declared set of material affordances needed for the workshop: condition change, wear, repair, and resource consumption. Distinguish conservation rules from explicit sources, sinks, or regeneration in the world contract.

**Done when:** an interrupted repair resumes or fails honestly, concurrent work cannot double-spend a tool or resource, and one causal lineage connects the physical effect to later evidence. A newly named procedure cannot perform an unsupported physical action.

### U5 — Integrate Fool's Memory, Model A, and the Crux

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

**Current transition status: 0/14 implementation milestones complete. Next: U1 — freeze the supplied baseline, establish reproducible comparisons, and define the migration contract.**

