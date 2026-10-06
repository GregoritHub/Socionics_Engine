# HLE unified object engine — U14

This package contains the complete bounded workshop engine, a frozen release evaluation, and a read-only inspector. Read `docs/HLE_Unified_U14_Report_v1.md` for the final decision, actual results and limitations. The 51 native and 98 legacy runtime modules retain their U13 identities. U14 adds evaluation and inspection tools, not a new behavioral policy.

Use Python 3.12 on Linux; the standard library is sufficient. All commands below run from this source directory and require fresh output directories. The accompanying evidence package contains the completed executions and original failures.

## Inspect the demonstration

Open the accompanying `HLE_Unified_U14_Inspector_v1.html` in a browser for a self-contained, read-only view. It makes no network requests.

For exact participant state and historical object versions, point the inspector at a checkpoint in the evidence package:

```sh
python tools/inspect_u14.py /path/to/evidence/population/p-50001-abundant/final.checkpoint.json.gz --actor bob
python tools/inspect_u14.py /path/to/evidence/population/p-50001-abundant/final.checkpoint.json.gz --actor bob --assess --html /tmp/hle-inspector.html
python tools/inspect_u14.py /path/to/evidence/population/p-50001-abundant/final.checkpoint.json.gz --actor bob --assess --object workshop:u12-press-50001-bob --revision 1
```

Default exports contain only the selected actor's received accounts and owned work. `--assess` adds simulator history and accounting, clearly labeled. Accounts may be stale: an evaluator's current truth does not become participant knowledge.

## Reproduce the release

The following functional panels may run independently. `--jobs` controls separate case processes; use a value appropriate for available memory and CPU. A completed case is never overwritten. `--resume` resumes an interrupted panel only with the identical frozen source and case configuration, preserving any failure already recorded.

```sh
python tools/evaluate_u14.py --stage native --out /tmp/hle-u14/native_tests
python supplement/evaluate_legacy_isolated.py --out /tmp/hle-u14/legacy_tests --jobs 3
python tools/evaluate_u13_fidelity.py --out /tmp/hle-u14/fidelity
python tools/run_u14.py --panel autonomy --jobs 3 --out /tmp/hle-u14/autonomy
python tools/run_u14.py --panel controls --out /tmp/hle-u14/controls
python tools/run_u14.py --panel population --jobs 2 --out /tmp/hle-u14/population
python tools/run_u14.py --panel language --out /tmp/hle-u14/language
python tools/run_u14.py --panel nesting --out /tmp/hle-u14/nesting
python tools/u13_witness.py --out /tmp/hle-u14/witness
python tools/verify_baseline.py --out /tmp/hle-u14/baseline_initial.json
```

The delivered legacy result executes all 840 unchanged tests in 37 fresh module processes. `U14_Regression_Execution_Amendment_v1.json` freezes the complete ordered test inventory and runner before this run. An earlier monolithic attempt stalled and its diagnostic rerun crashed the interpreter; both remain in evidence. The cause is unresolved. For investigating that execution limitation, the original monolithic command remains `python tools/evaluate_u14.py --stage legacy --out /tmp/hle-u14/legacy_monolithic`; that is not the mode used for the delivered complete regression result.

After all other task-owned computation has stopped, run the sequential timing comparison:

```sh
python tools/measure_u14.py --out /tmp/hle-u14/measurements
```

Copy the retained `inherited/HLE_Unified_U13_Evidence_v1.zip` from the delivered evidence package into the same relative location under `/tmp/hle-u14`. It is required to verify the adopted full U13 measurement panel. The original assessment retains its failed care-only scarcity expectation. Reproduce it explicitly:

```sh
python tools/verify_u14_release.py --evidence /tmp/hle-u14
cp /tmp/hle-u14/acceptance_summary.json /tmp/hle-u14/acceptance_summary_v1.json
```

That command records the original decision in `acceptance_summary.json`; retain it as `acceptance_summary_v1.json` before the versioned reassessment. The final release additionally requires the newly frozen stronger controls:

```sh
python supplement/run_exhaustion.py --out /tmp/hle-u14/exhaustion --jobs 3
```

Run those functional controls before the isolated measurement command. After retaining the original decision as described above, compute the final reassessment:

```sh
python supplement/verify_release_v2.py --evidence /tmp/hle-u14
```

The original checker intentionally exits nonzero for its retained scarcity failures; run the copy command even after that expected result. The final decision preserves the original failed expectation. It requires raw proof of paid repair fallback in every affected original case, all original behavioral invariants, and ten new controls with both maintenance paths constrained. It fails closed on missing outcomes, changed source, failed mandatory checks, raw checkpoint/transaction digest mismatches, or failed performance gates. A deliberate code edit requires a new versioned protocol and execution manifest; do not silently overwrite this release's identity.

## Engine APIs and scope

For direct API imports, put this directory and `baseline/HLE_Rebuild_R21B` on `PYTHONPATH`. Existing tools configure those paths themselves. `InstitutionEngine` carries the earlier native layers; the source retains all focused APIs and examples. The explicitly activated legacy adapter remains available:

```python
from hle_unified.efficiency import install_legacy_optimizations
install_legacy_optimizations()
```

The workshop supplies finite affordances, history inputs and interaction opportunities. Participant processing pays the unchanged prices; observations, interpretations, learned procedures, consents, effects and public consequences retain distinct provenance. This release does not claim unrestricted conversation, an autonomous open-world society, unlimited complexity, a 3D client, empirical psychological validity or separate R21C certification.

See `docs/U14_Architecture_and_Scope_v1.md`, `docs/U14_Development_Record.md`, `contracts/U14_Protocol_v1.json` and `U14_Execution_Manifest_v1.json`. Earlier milestone documents and source manifests are retained historical records; the U14 report and completed roadmap give current status.
