# FB5.1 — Population over workflow selection: active

[source_defined] Entry is the accepted FB4.2 checkpoint. The prospective population protocol is `contracts/C7_Workflow_Population_Protocol_v1.json`; its digest is stored beside it before implementation changes.

[source_defined] The scheduler may accept the Phase 2 workflow-selection request type alongside the inherited `SelectionRequest`, but still chooses only whose paid turn runs. It supplies no route, recipe, result, skill, truth, resource, replenishment, new goal or population growth.

[source_defined] Legacy `hle-c7-population-v2` checkpoints and tests remain exact legacy behavior. Workflow-selection populations receive a new tagged schema and restore with their own workflow engine.

[derived] The implementation adds typed workflow requests to `Population`, preserves the exact v2 output path for inherited populations, and uses `hle-c7-workflow-population-v3` only when a workflow demand is present. The workflow turn advances the paid comparison and its native movement without moving route or recipe choice into the scheduler.

[machine-checked] Development attempts 1 and 2 exposed only local test-fixture and auditor-interface mistakes; both are preserved under `evidence/FB5.1`. Development attempt 3 passed all 11 new methods plus all eight unchanged inherited population methods, 19 methods total.

[machine-checked] Acceptance attempt 3 lost its uncommitted execution workspace before the two long runners completed. Its observed partial results are preserved but credited to no gate. Acceptance restarts as attempt 4 from the committed implementation source.

[open] Frozen full-regression and raw-panel acceptance evidence remain to be completed.
