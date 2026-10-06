# C1: common content execution

22 September 2026. Engineering implementation of C1 in the full-Crux specification, version 2. The acceptance report records the final decision; this file describes the mechanism and its limits.

## The change

The inherited U5 circuit derives its conceptual answer before constructing its intermediate surfaces. It remains available with its original behavior. `CruxEngine`, an extension of the complete `InstitutionEngine`, adds a movement executor whose paid semantic steps produce the actual content consumed by subsequent steps and operations.

The new interface is `MovementRequest`. Each request selects an immutable versioned recipe, an owned retained input, a context, a Fool’s Memory cue, and exact processed evidence addresses. Hypothesis construction additionally names an accessible policy definition. The request cannot supply a completed answer.

| C1 recipe | Formal movement | Actual content responsibility |
| --- | --- | --- |
| condition-hypothesis-v1 | Theorize, I → ITS, accumulation | Convert the actor’s explicit condition account and read action policy into a scoped, tentative prediction with an inspection test. Unknown or disputed input remains uncertain. |
| condition-trial-v1 | Apply, ITS → IT, accumulation | Instantiate that model into an inspection trial; complete only after the separate native inspection work creates its actual event. |
| condition-retention-v1 | Embody, IT → I, accumulation | Compare the model with its received and paid-read trial outcome, then consume that comparison in a retained personal interpretation. |

Theorize uses an N Fold edge; Apply uses T; Embody uses a T edge followed by N. Each edge follows a paid Model A route, with the existing positional and polarity prices. Alternative attitudes within the same declared families are supported and tested. The recipe does not infer competence from a type label.

This is a minimal content language: scoped condition propositions, tentative predictions, a declared test, comparison results, and retained interpretations. It does not yet implement arbitrary hypotheses, relational discovery, commitments, shared meaning, or the full content language promised for C7.

## Paid intermediate results

At start, the executor validates access and freezes the explicit input. It does not compute the finished semantic answer. During `advance`, crossing a semantic step’s paid threshold creates a `c1.step` object. Its account records the actual output propositions. Its metadata names the predecessor, recipe, paid operation revision, perspective endpoints, polarity, and payment threshold.

For a multistep movement, the next step takes that previous step’s content. When a work call crosses two thresholds, the second consumes the first result constructed in the same atomic batch. When interrupted between them, it consumes the already committed first result after restoration. A final semantic result is not actor-retained until the completed movement’s receipt binds it through the existing access ledger.

Apply’s generated trial supplies the actual native material command. Its three material work units are additional to the semantic route work. Native inspection samples the real material state at commitment. That actual event is distinct from the model’s prediction. The actor gains no outcome knowledge until the event is delivered and paid-read.

The original model remains a tentative historical model even after contrary evidence. Embody produces a separate owned account with the comparison retained in its causal predecessor. That account can feed both the old native action planner and a subsequent C1 Theorize request. A new model therefore can originate from the circuit’s generated retained result.

## Compatibility

The legacy request `CognitiveRequest(purpose="integrate")` continues to mean IT → I, which the formal map names **Embody**. Its API, historical labels, and record namespace are preserved. The Crux route **Integrate**, ITS → ITS, remains work for C2.

C1 retention writes the established `u5.account` structure, so the existing planner consumes the corrected account without a second policy or a scenario-authored answer. The native primitive `use` was already available; the positive witness demonstrates a corrected belief enabling its selection. It does not demonstrate acquisition of a new motor skill or named procedure.

`CruxEngine.from_u14` replays an exact U14 checkpoint under the new engine schema. The existing world, actor access, commands, and accounting remain equal. Old institutional negotiation is also tested after import. No old participant runtime module is changed. Two offline audit functions gain an optional extension-flag argument; their default behavior is unchanged.

## Evidence and independent reconstruction

`crux_audit.py` reads raw object transactions and the raw access-event archive. It independently reconstructs permitted field projections, paid reads, owned bindings, semantic postconditions, and content handoffs. It does not import the C1 executor, content transformer, or selector. It reuses the existing independent route/material/accounting auditor with an explicit C1 work-extent validator.

The positive witness begins with a mistaken damaged-tool account while the actual target is serviceable. Its tentative model predicts damage. The actual inspection contradicts that prediction. Comparison and retention revise the owned account; the old planner changes from inspect to use, and native use actually succeeds. A later model is built from the corrected account.

The inverse witness begins with a mistaken serviceable account while the actual tool is damaged. The actual trial leads the actor to select inspection rather than its formerly selected use. Matching-evidence cases preserve their prior action: ordinary successful execution is not reported as a newly enabled capacity.

An evaluator-only subclass removes the comparison result while retaining the route and its paid work. Subsequent use disappears. This counterfactual intentionally fails the ordinary semantic validator; it is not a supported alternate recipe or a passing engine result. A separate fully paid cancellation leaves no retained correction.

## Efficiency boundary

Definitions and exact immutable structure use the existing compact store. Movement records refer to prior objects; they do not copy entire trajectories. A C1 request has one explicit candidate and at most two semantic steps. There is no exhaustive search over all compositions and no new global scheduling scan.

The first baseline varies inactive history through 100, 1,000 and 10,000 objects, separately for shared and unique content. Thirty isolated timing samples and six separate traced workers measure active execution, restoration, audit, incremental live allocation, checkpoint sizes, and resolved records. Initialization, serialization, restoration and audit are excluded from active circuit timing. Instrumented resolution counts and memory measurements are collected separately from the primary timing samples.

These are first C1 measurements, not an optimization speedup claim. Full unique history still costs storage, and the inherited engine checkpoint includes embedded world/access history. Expansion in participants, alternatives and composition depth remains unmeasured for these new recipes. Those dimensions become applicable as C4–C7 supply the corresponding semantics.

## Limits and next milestone

- Only three accumulation recipes are implemented in C1; no 32-cell completion claim is made.
- The circuit tests an existing tool’s condition by inspection. It does not discover a physical law or perform an arbitrary intervention.
- C1 route sequencing is supplied by the witness. Participant selection across the full Crux belongs to C6.
- Transfer to a second tool identity is the same workshop domain, not the two distinct content settings required for full release.
- New Shell deformation, self-routes, shared transformations, cross-system integration, and general nesting remain C2–C7 work.
- Exact restoration is assessed in the recorded Python runtime. No unrestricted scalability or psychological validation follows.

The next implementation milestone is C2: Contemplate, Act, Commune, and Integrate under both polarities. The same three-question evidence and continuous efficiency requirements apply.
