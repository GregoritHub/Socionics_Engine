# HLE full Crux — C1 report v1

22 September 2026 · **C1 complete in its declared domain · 1/7 milestones complete.**

The engine now has a native movement executor whose intermediate semantic results are the inputs to subsequent work. The first circuit is **Theorize → Apply → Embody**, followed by an existing native action planner and, in the raw witnesses, a new model constructed from the retained result. Each step is paid and linked to exact content. C2–C7 remain open.

## What changed, how, and what becomes possible

| Question | Executed evidence |
| --- | --- |
| What changed? | An actor’s mistaken tool-condition account becomes an observation-supported personal interpretation. The tentative original model and the earlier mistaken account remain in history. |
| How did it change? | Theorize builds a scoped prediction from owned content. Apply consumes the generated model to instantiate and perform a paid inspection. The actor receives and paid-reads the actual outcome. Embody compares it with the prediction and consumes that comparison to retain a revised account. |
| What becomes possible afterward? | In the positive witness, the native planner changes from **inspect** to **use**, and use actually succeeds. In the reverse witness, it changes from **use** to **inspect** when the actual tool is damaged. A new model can also consume the generated retained account. |

This is a change in evidence-supported choice. The native physical primitive was already available; the circuit does not confer a newly practiced skill merely by acquiring an explanation.

The primary causal control removes the comparison result while keeping the same route and movement costs. The participant then continues to select inspection; the newly enabled use disappears. For the IEE pair, Theorize costs 8 units, Apply 20, and Embody 40 on both branches. Apply includes three native material-inspection work units. Reading, earlier/later planning, and the eventual action have their own charges. The control intentionally fails the ordinary semantic acceptance validator and is explicitly labeled as an evaluator intervention.

Matching-evidence cases preserve their previous action. They are useful execution checks, not counted as newly enabled capacities.

## What was implemented

- `MovementRequest` and three immutable versioned accumulation recipes over the common object store.
- Actual paid semantic handoffs, including interruption between comparison and retention.
- A real native inspection event consuming a generated trial, with explicit delivery and paid reading before learning from it.
- Owned retained accounts consumed by the existing planner and by subsequent model construction.
- An independent content auditor reconstructing exact field delivery, ownership, paid work, intermediate content, and observation-to-event correspondence.
- Exact U14 checkpoint import and continued old institutional behavior in `CruxEngine`.

The old `CognitiveRequest(purpose="integrate")` remains IT → I, formally **Embody**. The Crux route **Integrate**, ITS → ITS, is still for C2. Existing participant runtime modules retain their bytes. Two offline auditor functions gain an optional extension argument with unchanged default behavior; four C1 modules provide the new layer.

## Validation

| Evidence | Result |
| --- | --- |
| Distinct current tests | **475 pass:** 454 inherited native methods plus 21 current C1 methods; no failures, errors, or skips in the accepted stages. |
| Type/condition matrix | **64 cases:** 16 Model A types × both prior conditions × both actual conditions. |
| Content transfer | A second tool identity in the same finite workshop; no claim of a second semantic domain. |
| Raw witnesses | Five retained packages: enabled use, rejected use, supported model, second target, and comparison ablation. Four healthy witnesses pass ordinary semantic audit; the ablation must fail it. |
| Interrupted continuation | Nine boundary configurations across Theorize, Apply and Embody; exact checkpoint equality after identical continuation. Completed and failed-work restoration are also checked. |
| Boundaries | Unread evidence, foreign models, wrong scope, wrong trial, stale dependencies, resource exhaustion, cancellation, hidden material differences, forged content/debits, and disconnected predecessors. |
| U14 compatibility | Old circuit and institutional continuation preserve world/access state after upgrade. All 3,044 frozen baseline members and all 98 legacy runtime modules verify unchanged. |
| Performance baseline | 30 isolated timing samples plus six separately traced workers; all behavior, accounting, restoration and fixed-active-resolution gates pass. |

The first complete run passed 474 methods. Review then found an independent-audit gap: a paired edit to an observation and its delivery could be accepted before comparison began. The runtime had emitted the correct observation. The auditor now compares the complete projection against the actual trial event; the added control and all 21 affected C1 methods pass. The final total counts repeated methods once. The earlier run, the discovered gap, the amendment, and the first failed exhaustion-fixture run remain in evidence.

The 840 legacy tests reported for U14 were not rerun here. They remain historical evidence; the full inherited native population was rerun.

## First efficiency baseline

The active task is held constant while inactive history increases. Five timing samples per row run in separate sequential workers. The active interval includes the circuit, event receipt processing, later planning, and the later action; setup, checkpoint generation, restore, and audit are outside that interval. Memory figures come from a separate traced worker per row and describe additional allocations during active work, not the whole live engine.

| Inactive content | Records | Active median (ms) | Restore median (s) | Incremental active peak (MiB) | Raw engine checkpoint (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shared | 100 | 108.5 | 0.370 | 1.35 | 0.99 |
| Shared | 1,000 | 108.2 | 0.704 | 1.36 | 2.13 |
| Shared | 10,000 | 103.1 | 4.879 | 5.02 | 13.56 |
| Unique | 100 | 103.1 | 0.372 | 1.78 | 1.04 |
| Unique | 1,000 | 101.7 | 0.790 | 1.26 | 2.66 |
| Unique | 10,000 | 137.8 | 6.872 | 1.32 | 19.01 |

Every measured case performs **290 store resolutions over 55 distinct references**, three completed C1 movements, four semantic steps, and the same successful downstream use. Full-engine modeled spending is 160 units, including actor preparation. Increasing inactive records from 100 to 10,000 does not increase that active resolution count. Observed active medians span approximately 102–138 ms on the recorded Python 3.12.14 Linux runtime.

This is a baseline, not a speedup or asymptotic guarantee. Active allocation is not uniformly flat: the shared 10,000-record case reaches approximately 5.02 MiB of incremental peak allocation. Exact unique history still requires storage. Full restoration reaches 6.87 seconds, and the largest raw engine checkpoint is about 19.01 MiB; the corresponding raw world checkpoint is about 5.07 MiB and its compressed representation is about 0.23 MiB. These are different scopes and formats, reported separately.

The clearest next efficiency investigations are checkpoint representation/replay and the observed allocation peak. The inherited checkpoint embeds overlapping world/access history. Any compaction must preserve all exact identities, receipt evidence, private access, mistakes, conflicts, costs, and continuation. No total-memory bound or removal of relevant history is claimed.

## Scope and next step

C1 implements **three bounded accumulation recipes**, one explicit actor-owned candidate at a time, and at most two semantic steps per movement. The material test is inspection of a tool under the existing finite law. The route sequence is supplied by the witness; broader autonomous choice remains C6. Neither full natural-language meaning nor empirical psychological validity is established.

The 32-cell full-release ledger remains open: a C1 prototype witness does not satisfy the later transfer, Shell, nesting, and automatic-selection gates. **Six milestones remain. Next: C2 — Contemplate, Act, Commune, and Integrate under both polarities.**

## Reproduction and delivered evidence

The source README gives runnable commands. `tools/verify_c1.py` reconstructs the raw witnesses, validates the final source/evidence relation, checks the accepted test populations, and reconstructs the measurement coverage gates. The evidence retains original failed development, the successful pre-review full run, the final C1 review run, raw witnesses, all timing/traced samples, baseline identity verification, and the final acceptance decision.

This report implements the user’s three-question standard and the efficiency requirements of HLE_Full_Crux_Build_Specification_v2.md. The formal 32-route contracts remain those of that specification. All new content algorithms, numerical work extents, and acceptance choices are explicit engineering constructions.
