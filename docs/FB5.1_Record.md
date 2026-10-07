# FB5.1 — Population over workflow selection: complete

[source_defined] Entry is the accepted FB4.2 checkpoint. The prospective population protocol is `contracts/C7_Workflow_Population_Protocol_v1.json`; its digest is stored beside it before implementation changes.

[source_defined] The scheduler may accept the Phase 2 workflow-selection request type alongside the inherited `SelectionRequest`, but still chooses only whose paid turn runs. It supplies no route, recipe, result, skill, truth, resource, replenishment, new goal or population growth.

[source_defined] Legacy `hle-c7-population-v2` checkpoints and tests remain exact legacy behavior. Workflow-selection populations receive a new tagged schema and restore with their own workflow engine.

[derived] The implementation adds typed workflow requests to `Population`, preserves the exact v2 output path for inherited populations, and uses `hle-c7-workflow-population-v3` only when a workflow demand is present. The workflow turn advances the paid comparison and its native movement without moving route or recipe choice into the scheduler.

[machine-checked] Development attempts 1 and 2 exposed only local test-fixture and auditor-interface mistakes; both are preserved under `evidence/FB5.1`. Development attempt 3 passed all 11 new methods plus all eight unchanged inherited population methods, 19 methods total.

[machine-checked] Acceptance attempt 3 lost its uncommitted execution workspace before the two long runners completed. Its observed partial results are preserved but credited to no gate. Acceptance restarts as attempt 4 from the committed implementation source.

[machine-checked] Acceptance attempt 4 passed 713 distinct methods with zero failures, errors or skips: 602 inherited methods, 74 workflow/Shell/interruption/Model G methods, 21 C7 and population methods, six workflow-nesting methods, six workflow-composition methods and four workflow-development methods. Every runner reported unchanged source bytes.

[machine-checked] The accepted source freeze contains 1,295 Python/contract files and has SHA-256 `659c4b10032d183cf1cf67c066cc367a4543bc9f8c532c8f8b329c549e035c25`. Of the 1,288 FB4.2 files, 1,286 are byte-identical and exactly the two preregistered implementation targets changed: `hle_unified/population.py` and `hle_unified/population_audit.py`. Seven preregistered protocol, test and evaluation files were added; none were removed.

[machine-checked] Six raw worlds passed independent reconstruction without importing or replaying the scheduler, selector, engine or fixtures. Across fairness, interrupted continuation, material feedback, repetition stop, exhaustion and mixed legacy/workflow cases, the panel retained 177 scheduler turns, modeled 1,901 paid energy units and reconstructed 21 native completions. The interrupted case restored exactly; the repetition case stopped both supplied demands after two equal retained results; the exhaustion case stopped only on zero wallets; the mixed case kept legacy and workflow decision families distinct.

[machine-checked] The scheduler accepts `SelectionRequest`, `WorkflowSelectionRequest` and `WorkflowCapacitySelectionRequest`, rejects duplicate actors and foreign demands, advances only the selected actor's paid comparison/native work, and preserves separately paid material feedback. Forged charge and decision summaries are rejected by the independent population auditor.

[source_defined] Exact commands, starts, durations, exits and counts are in `evidence/FB5.1/attempt4/commands.json`. The accepted raw archive is `Socionics_Final_Build_FB5.1_Evidence.zip`, 2,005,000 bytes, 163 members, SHA-256 `d7ad70da1231eba014f89282b3e2e476b93444c5a8c8f28a76bb1fb8a2247bac`. Exact Library/file identities and restoration instructions are in `evidence/FB5.1/attempt4/Raw_Evidence_Index.json`; 130 evidence files present before indexing are covered by `Raw_SHA256.json`.

[derived] What becomes possible: the fair bounded scheduler can now sustain independently owned demands whose content path is chosen by the Phase 2 workflow selector, while preserving legacy C7 checkpoints and distinguishing the two request/decision families. This does not establish truth, spontaneous goals, replenishment, population growth, learned skill, optimal scheduling, general development or exhaustion of future opportunities.

[open] Batch 5.2 is next: sustained panel and costs. Release 1.0 remains incomplete; no theoretical register item is closed. Phase 7 remains unauthorized without the author's separate explicit R5 ruling.
