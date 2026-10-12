# Phase 7 reproduction

[source_defined] This experiment is authorized by [R5](FB7_R5_Authorization.md) and governed by [Energy Contract v1](../contracts/Energy_Contract_v1.md) and [Energy Protocol v1](../contracts/Energy_Protocol_v1.json). Their `.sha256` sidecars preserve the prospective contract identities. `legacy-r4` remains the default; `grade-v1` is an opt-in engineering hypothesis.

## Use the switch

[derived] Create the initial finite world and law using the ordinary world-building APIs, then select the model once:

```python
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
engine = WorkflowFinalSelectionEngine.create(world, law, resource_model='grade-v1')
checkpoint = engine.checkpoint()
restored = WorkflowFinalSelectionEngine.restore(checkpoint)
assert restored.resource_model == 'grade-v1'
assert restored.checkpoint() == checkpoint
```

[derived] Omit the keyword, use `resource_model='legacy-r4'`, or use the existing constructors to retain legacy behavior. Experimental creation derives a fresh initial store; the supplied store is not modified. Started worlds cannot be repriced. Complete step energy is charged on entry, once; subsequent time quanta finish the prepaid step without charging energy again. Every time quantum still consumes time. Cancellation gives no refund.

[derived] Read completed use from raw transactions without mutating the engine:

```python
from hle_unified.conditioning_audit import observations
rows = observations(engine.world.journal())
```

[source_defined] Rows contain eight element counts, four axis loads/tilts, all greatest-load ties, and separate D/C/N/H formula sums. This is a completed-use observation, not subtype identification. The formula source caveat remains part of each row. Nothing reads these observations to price, select, schedule or modify Shell behavior.

## Reproduce evaluations

[derived] Run from the repository root with Python 3.12 and standard-library dependencies. Each output path must be new. The tools configure their own import paths.

```sh
python3 tools/run_energy_regression.py evidence/local-phase7-regression
python3 tools/evaluate_energy_panel.py evidence/local-phase7-panel
python3 tools/verify_energy_panel.py evidence/local-phase7-panel
```

[source_defined] The panel runs 512 automatic pairs, 64 withheld-child controls, 12 core population pairs and 96 extension pairs, at exactly the registered funding. The verifier independently checks raw histories; it does not import execution modules. A panel summary alone is not acceptance. Source hashes must remain unchanged through generation and verification.

[derived] Historical conditioning requires the exact missing raw members named by the existing FB5.1–FB5.6 evidence indices. Verify their archive and member hashes before extraction; do not replace existing files with different bytes. The 225 aliases and exact hashes are in `evidence/FB7.1/Historical_Conditioning_Inputs.json`.

```sh
python3 tools/evaluate_conditioning.py evidence/local-phase7-conditioning
```

[derived] For performance, create an isolated read-only reference checkout of the recorded pre-extension source and run after other measurements finish. One warmup and three measured samples execute sequentially for each configuration; no timings use memory tracing.

```sh
git worktree add --detach ../energy-reference 6960145517974f6c69b8ae66b5b56de2c35cbbe1
python3 tools/measure_energy.py evidence/local-phase7-costs ../energy-reference
```

[source_defined] Model comparisons are descriptive, with no optimization claim. The inherited 2× unchanged-native and 3× inactive-history guards apply to matched legacy workloads. Exact pre-extension legacy checkpoint equality is also required. A failed prediction is retained; prices or funding must not be tuned after results.

[open] The final report and candidate decision determine which evaluations were accepted. Interrupted development and invalidated freezes remain explicitly uncredited. Large raw archives retain their exact durable identifiers and hashes in the corresponding evidence indices; repository access alone does not confer access to a private archive.

[derived] The final historical supplement includes 169 additional exact Corrective5 aliases. Restore the member paths in `evidence/FB7.3/Corrective_Inputs.json`; combine its `inputs` with the original 225-entry index in a separate data root. See `FB7.3_Record.md` for the unchanged-reader invocation. `Historical_Status_Labels.json` keeps accepted, held and uncredited attempts separate. The forged raw-transaction control remains explicitly outside the engine-envelope input set.

[derived] The accepted audit also ran as four disjoint 155-pair partitions using the exact same frozen `verify_energy_panel.py`. `attempt2/Audit_Partitions.json` records their complete membership. The final archive omits duplicate symlinks: to replay a partition, read its `summary.json` and create each engine/population/control file link to `../attempt2/<file>`, then run the ordinary verifier on that partition. A serial verifier run on the full `attempt2` directory is equivalent and needs no partition links. The aggregate result requires exactly 620 distinct original pair IDs, all four unchanged-source passes, 548 ample pairs and 64 controls.
