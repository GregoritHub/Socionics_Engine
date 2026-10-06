# R14 — generated demands and participant-selected work

## Scope and entry point

`hle.autonomy.AutonomousWorld` extends the complete R13 `DevelopmentalWorld`, which extends the existing world, memory, processing, assessment, Socion, language and organization chain. New workshop events, actor decisions and demand revisions live in the **same typed journal**. Existing R13 content and meaning commands remain usable; the R14 suite appends them to a generated-demand run and verifies exact replay.

The default command `python -m hle` runs the finite workshop. Its round-robin scheduler offers an actor a turn; it does not assign the actor a workpiece, ask for a loan, give a lesson, choose cleaning or prescribe a return. `autonomy_step(actor)` dispatches one already selected command or one paid policy quantum. Resume dispatch changes only a command identity for the same previously selected task; it is not another policy choice.

The environment and policy have explicit boundaries. The engine is given generic workshop physics, a finite primitive menu and seeded standing motives. Each actor first retains its own motives through paid Write and Bind. These motives are **not claimed to be spontaneously invented values**. The controller supplies neither the later maintenance/return demands nor a completed action sequence. Those demands arise from the actor comparing retained motives with observed consequences.

The grammar contains three demand families: preparing an owned workpiece, maintaining an affected tool, and honoring an accepted due return. Instance, material, participants, source events, current availability and outcome vary; the engine does not invent arbitrary new demand predicates at R14. The evaluation seeds vary referent names and declaration ordering within this grammar, not the physical laws or a stochastic population model.

## Concrete loop

The borrower observes an owned raw workpiece and a tool owned by another participant. Paid recall makes the preparation motive and known ownership available to the policy. When no owned clean tool is available, it can request a voluntary loan. The holder receives and interprets the request, recalls its own material, needs and boundary policy, and independently lends or refuses.

Successful use makes the raw workpiece ready. Under the elected wear law, it also makes the tool dirty. If the user borrowed the tool with an accepted return condition, use makes that return due. These are **persistent world relations**, not generated-demand flags. They remain after the action and through clock-only events.

Only later observation, retention, contextual recall and paid selection expose the two resulting needs: restore the tool's usable condition and return the entrusted tool to its accepted lender. If both are active and return requires a clean tool, the actor chooses cleaning first, then return. Fresh observations and recall confirm each satisfied condition. Losing a motive or hiding a memory cannot mark the physical obligation resolved.

This loop instantiates the source's persistent-consequence → new-demand pattern. It does not establish a developmental boundary, Shell, acquired complementary closure or higher altitude. Meeting these needs with the available repertoire is ordinary adaptation in the represented domain.

## Records and commands

`autonomy_records.py` defines immutable version-one values using existing actor, event, memory, work, binding and demand references:

| Record | Responsibility |
| --- | --- |
| `WorkshopConfig` | Declared owned object conditions; explicit wear and due-after-use laws. |
| `AutonomyPolicy` | Actor, standing motives, available primitive menu, lending/asking boundary, reserve and quantum limit. |
| `WorkshopPacket` | Typed loan request with explicit return consent, help request, evidence-supported lesson or refusal. |
| `WorkshopCommand` / `WorkshopJob` | Physical operation, exact inputs and basis, request witness where needed, paid progress and outcome. |
| `AutonomyTurn` | Actor and work quantum only. It has no task objective, Shell flag or desired result field. |
| `LocalView` | Detached own observations, completed paid recall, applicable current memory, own resource budget and policy state. |
| `ViewSnapshot` | Exact references and proposition indices reconstructing the same local view during unfinished processing. |
| `AutonomyJob` | Route plan, reference snapshot, paid units and outcome. It contains no unpublished policy answer. |
| `AutonomyState` | Inbox position, pending selected work, archival patches, contextual memory pointers, interpreted requests and local attempt history. |
| `DemandRecord` | Resolved R12 `DevelopmentalDemand`, actor/material, status and reason. |
| `AutonomousTransaction` | Work, observations, physical or policy job, participant state, processing state and generated demand revisions in the shared journal. |
| `AutonomousCheckpoint` | Full inherited configuration and journal, plus workshop laws and actor policies. |

Generated demands reuse the R12 contract: origin type/events, discovery observations, family and protocol, required outcome/movement, context, participant, exact material/motive revisions, constraints, duration, resource envelope and prior demand revision. Root preparation comes from a retained participant motive; maintenance and return demands are marked consequence-originated. The formal I→IT expenditure requirement names an intended outcome, not completed individuation.

Different families are not silently ordered as harder. The R12 conservative demand comparator and its requirements remain unchanged. The two source effects can coexist and impose prerequisites without creating an arbitrary scalar developmental score.

## Permitted information, currentness and choice

`autonomy_policy.decide(LocalView, key)` is a pure function. It has no world, Truth, evaluator, foreign-memory or global-history parameter. A separately testable projection constructs that view from actor-owned records. Physics may inspect simulator facts to implement consequences; the participant policy may not.

Observing a message, interpreting it, retaining it and recalling it are separate steps. A lender cannot execute an accepted loan from an unreceived request, a generic consent flag, a different borrower or a different material. A lesson must cite actual own observed or retained use evidence. A missing teacher example produces refusal rather than a fabricated skill. The available teaching example transfers access to a **predefined finite use primitive**; it is not an invented general procedure language.

Before selection, current contextual recall validates binding and memory heads. Withdrawn, disputed or superseded material cannot count as currently available. Historical observations remain accessible as history. An invalid/truncated context produces an unresolved outcome, not satisfied demand. Archival editing may inspect the head of the record it is revising; consequential selection still uses a completed paid RecallQuery.

The policy can select native action, inspection, recall, help seeking, teaching, waiting, refusal, revision, or finite search exhaustion. Loan holders may refuse based on their own preparation need, ownership, condition or stated boundary. A silent response remains waiting. When all known alternatives have actually failed or refused, the reported exhausted search concerns the declared local repertoire, not every possible future solution.

Opaque messages unsupported by the finite grammar can be received and marked uninterpreted once. Their neutral parsing route is an engineering convention, not a claimed semantic classification. Such a message does not create a fabricated task or keep the actor repeatedly reading the same envelope.

## Paid work, continuation and separate observations

Policy interpretation/selection is routed through existing Model A processing. Current TIM remains fixed; the route to a declared parsing or selection element determines its positional work price, multiplied by the considered finite content extent. Numerical prices are engineering choices, not psychological energy laws.

A policy decision is computed and published **only after its declared work is paid**. Its reference snapshot, partial payment and processing reservation are checkpointed. Completed selection uses the remaining wallet after thinking costs when deciding whether action is affordable. Physical use, cleaning, lending, return, inspection, message reception and relational memory also incur their actual charges.

The dispatcher mechanically resumes already selected partial reception or memory work. It must not start another policy turn while those operations reserve processing. Duplicate command identities return the original event without another charge; a changed command with the same identity rejects. Partly paid physical operations have no partial world effect; they complete or fail under their actual preconditions and preserve all paid work.

Need count, observed-state revision count, primitive-budget shortfall and repeated unsuccessful local targets are separate recorded quantities. An observed revision may be a normal successful change, not a contradiction. The repeated-attempt measure is the elected narrow operational proxy for the protocol's boredom term; no claim about human boredom is inferred. Clock-only quiet does not increase an activity pressure or force a new task.

When the actor's standing conditions are satisfied, inbox relevant input is consumed and no job is pending, the scheduler leaves the actor at rest. No new journal event or wallet charge is needed merely to keep it busy. Resource-exhausted initialization and work are reported as censored/unresolved, not successful quiet or clearance.

## Persistence and net-change controls

Removing wear removes the maintenance demand. Self-ownership instead of an accepted loan removes the return demand. Removing the due-after-use trigger leaves no presently due return under that altered declared law; it does not establish all future social obligations fulfilled.

A counterfactual fixture uses successful use followed by explicit cleaning/return interventions **before discovery**. The actor later remembers the final clean, returned state and does not generate those cancelled needs merely because transient activity occurred. These interventions are labeled controls and are absent from positive autonomous runs.

Conversely, a world effect is not automatically erased from participant belief when hidden. Direct repair leaves the earlier demand pending until a permitted observation and recall establish satisfaction. Moving custody via an ordinary R2 transfer also does not cancel the accepted loan relation: a borrower unable to return a tool still held elsewhere records an unresolved obligation.

## Checkpoint and historical compatibility

The same allowlisted typed codec stores inherited and R14 journal records. A real regression exposed a short-name collision between R5 `assessment_records.Opportunity` and R12 `development_contracts.Opportunity`. R14 now preserves the historical short wire name and uses an explicit qualified tag for the later distinct type. Encoder lookup uses exact registered class identity, so an unregistered dataclass named Opportunity cannot impersonate a supported record. Old checkpoints keep their original wire names.

Restore reconstructs all views from the journal and compares every replayed transaction. Rehashing an altered demand, snapshot, selected action or payment does not bypass replay. Bounded tests cover every prefix of the complete positive trace and new actor schedulers started at five intermediate round boundaries. Those fresh schedulers select future work independently rather than receiving a saved solution sequence.

The independent demand reference reconstructs predicates from exact paid-recall snapshot references without invoking live selection or reading simulator Truth. The independent resource audit folds genesis balances, credits and every debit and verifies partial-job counters. Neither is a Shell detector.

Normal R14 code does not iterate the complete global journal to select work; a guarded-history test checks this after 500 inactive clock events. It still has costs for the current memory catalogue, current demand heads, queues, journal growth and offline replay. The evaluated property does not certify R21's increasing-history latency or storage budget.

## Source and claim boundaries

The source basis is the R14 plan, Shell Geometry §§11–12, the foundation's own-information boundary, and the R13 handoff. Their source-defined distinctions are preserved. The workshop laws, standing motives, semantic templates, policy priorities, cue allocation, work prices and acceptance instances are explicit implementation choices.

R14 supplies generated instances and consequential participant choice in this finite world. It does not supply spontaneously invented motives, arbitrary prose understanding, unlimited new action invention, an emergent economic/social institution, all four developmental complexes, or a new Shell/clearance/altitude verdict. R15 must demonstrate genuine self-maintaining compensation rather than relabel ordinary ignorance, waiting, refusal or resource shortage as pathology.
