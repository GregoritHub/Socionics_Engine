# Code map and extension points

[Documentation index](../README.md) · [Capabilities](Capabilities.md) · [First run](First_Run.md)

The project is a set of Python modules, scenario tools and auditors. Historical names and schema versions remain to preserve compatibility. `hle_unified.__version__` is an inherited module marker, not the current project release decision; use [Delivery_Decision.json](../../evidence/Corrective6/Delivery_Decision.json) for release status.

## Where to begin reading

| Question | Entry points |
| --- | --- |
| How are identities, facets and history represented? | [records.py](../../hle_unified/records.py), [store.py](../../hle_unified/store.py), [codec.py](../../hle_unified/codec.py) |
| What can a participant know? | [particulars.py](../../hle_unified/particulars.py): `AccessLedger`, `ParticipantView`, grants and receipts |
| What makes an action physically valid? | [operation_records.py](../../hle_unified/operation_records.py), [operations.py](../../hle_unified/operations.py), [material.py](../../hle_unified/material.py) |
| How are Model A processing paths priced? | [cognitive_routes.py](../../hle_unified/cognitive_routes.py), preserved [model_a.py](../../baseline/HLE_Rebuild_R21B/hle/model_a.py) |
| How does content become a realized Crux result? | [crux_content.py](../../hle_unified/crux_content.py), [crux_execution.py](../../hle_unified/crux_execution.py), [crossing_execution.py](../../hle_unified/crossing_execution.py), [self_execution.py](../../hle_unified/self_execution.py) |
| How is canonical automatic choice made? | [selection_records.py](../../hle_unified/selection_records.py), [selection_policy.py](../../hle_unified/selection_policy.py), [selection_execution.py](../../hle_unified/selection_execution.py) |
| How are timed workflows represented and selected? | [workflow_records.py](../../hle_unified/workflow_records.py), [workflow_content.py](../../hle_unified/workflow_content.py), [workflow_selection_policy.py](../../hle_unified/workflow_selection_policy.py) |
| Where do Shells and correction operate? | [shell_records.py](../../hle_unified/shell_records.py), [shell.py](../../hle_unified/shell.py), [shell_policy.py](../../hle_unified/shell_policy.py), [development.py](../../hle_unified/development.py) |
| How are social changes implemented? | [grounded_language.py](../../hle_unified/grounded_language.py), [collective.py](../../hle_unified/collective.py), [institutions.py](../../hle_unified/institutions.py) |
| What schedules continued work? | [population.py](../../hle_unified/population.py), [workflow_continuation.py](../../hle_unified/workflow_continuation.py), [workflow_agenda.py](../../hle_unified/workflow_agenda.py), [workflow_agenda_population.py](../../hle_unified/workflow_agenda_population.py) |
| Where are structural Model G/DCNH queries? | [model_g.py](../../hle_unified/model_g.py), [axes.py](../../hle_unified/axes.py), [source tables](../../contracts/sources/) |

## Engine families are deliberately distinct

| Class / module | Role |
| --- | --- |
| `SelectionEngine` in [selection_execution.py](../../hle_unified/selection_execution.py) | Canonical automatic outcome selection over the inherited content language |
| `WorkflowEngine` in [workflow_execution.py](../../hle_unified/workflow_execution.py) | Timed-workflow request execution; inherited canonical APIs remain available |
| `WorkflowSelectionEngine`, `WorkflowCrossingSelectionEngine`, `WorkflowSocialSelectionEngine`, `WorkflowFinalSelectionEngine` in [workflow_selection_execution.py](../../hle_unified/workflow_selection_execution.py) | Preserved successive workflow-selection classes; the final class supplies the expanded automatic setting |
| `WorkflowShellEngine` in [workflow_shell_execution.py](../../hle_unified/workflow_shell_execution.py) | Extends the final selector with the paid workflow Shell admission gate |
| `WorkflowInterruptionEngine` in [workflow_interruption_execution.py](../../hle_unified/workflow_interruption_execution.py) | Extends that gate to interrupt after a paid workflow intermediate |
| `WorkflowNestingEngine` in [workflow_nesting_execution.py](../../hle_unified/workflow_nesting_execution.py) | Separate bounded parent/child workflow execution branch |
| `WorkflowContinuation`, `WorkflowAgenda`, `FairWorkflowAgendaPopulation` | Scheduling wrappers with their own recorded continuation contracts; use the matching wrapper's restore method |

A class inheriting earlier mechanics does not make all wrapper schemas interchangeable. Use `type(engine).restore(engine.checkpoint())` for the producing class, or the explicitly declared conversion method where provided. The first-run example deliberately uses the earlier self-route selection class for its small scenario, not as a claim that this is the only or newest workflow entry point.

## Executors, auditors and fixtures

Executors perform work and append records. Policy modules compute bounded choices from permitted inputs. `*_audit.py` modules reconstruct claims from journals/access records; sharing record definitions does not authorize calling the executor to confirm itself. `tools/verify_*.py` supply command-line assessment entry points. For example, [workflow_selection_audit.py](../../hle_unified/workflow_selection_audit.py) checks the selector independently.

`tests_*` directories contain fixtures as well as test methods. Fixtures explicitly establish starting worlds, budgets, histories and opportunities. They are useful for reproducible research and the [first run](First_Run.md); calling a fixture is not a demonstration of spontaneous world or goal generation. Deliberate tampering/bypass subclasses are negative controls, never production alternatives.

The accepted orchestration is [run_corrective_release.py](../../tools/run_corrective_release.py), governed by the hashed [54-job protocol](../../contracts/C7_Corrective_Evaluation_Protocol_v1.json). [verify_corrective_release.py](../../tools/verify_corrective_release.py) checks the complete result; [verify_corrective_ledger.py](../../tools/verify_corrective_ledger.py) checks the joint ledger; [verify_clean.py](../../evidence/Corrective6/verify_clean.py) checks assembled delivery. See the [reproduction guide](Evidence_and_Reproduction.md) before running these substantial jobs.

## Preserved layers

`baseline/` is sealed. `reference/`, old protocols, source freezes and historical evidence are reference material, not cleanup candidates. New experiments should use a branch, separate output directories and a prospective protocol. Do not edit accepted evidence to make it match a new implementation. The large documentation history can be navigated through [docs/README.md](../README.md) without moving files and breaking archived paths.
