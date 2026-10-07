# FB5.1 — Population over workflow selection: active

[source_defined] Entry is the accepted FB4.2 checkpoint. The prospective population protocol is `contracts/C7_Workflow_Population_Protocol_v1.json`; its digest is stored beside it before implementation changes.

[source_defined] The scheduler may accept the Phase 2 workflow-selection request type alongside the inherited `SelectionRequest`, but still chooses only whose paid turn runs. It supplies no route, recipe, result, skill, truth, resource, replenishment, new goal or population growth.

[source_defined] Legacy `hle-c7-population-v2` checkpoints and tests remain exact legacy behavior. Workflow-selection populations receive a new tagged schema and restore with their own workflow engine.

[open] Implementation and frozen acceptance evidence remain to be completed.
