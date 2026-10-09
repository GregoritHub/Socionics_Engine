# Reproduce the corrected release candidate

[source_defined] Python 3 and the standard library run the engine and evidence auditors. Node is used only for the standalone inspector's structural/filter check. The separate sealed pyref rerun remains owed; Phase 7 is not authorized.

## Exact inputs and clean assembly

[source_defined] Resolve the thirteen exact identities in evidence/FB6.3/Durable_Components.json and the three archives in evidence/Corrective1/Raw_Evidence_Index.json through evidence/Corrective3/Raw_Evidence_Index.json. Preserve the originals. The recovery script verifies each archive's original SHA-256 and size, rejects unsafe paths, checks collisions, extracts the nested original C7 archive, then verifies all 739 original ledger objects and four raw manifests. It requires an absent destination directory.

```sh
python3 SOURCE/evidence/Corrective6/reassemble.py ARCHIVES CLEAN_PARENT/Socionics_Research_Lab_Release_1_0
```

[source_defined] Extract the indexed corrective source and fresh evidence packages into CLEAN_PARENT. Both use the same Socionics_Research_Lab_Release_1_0 root. Check their archive SHA-256 values against the final delivery index first; the clean verifier checks their complete member manifests. Historical evidence resolves under evidence/historical. Original FB6.2 and Corrective1–3 records retain their source-relative paths as well. Never replace a colliding file with different bytes.

```sh
cd CLEAN_PARENT/Socionics_Research_Lab_Release_1_0
python3 evidence/Corrective6/verify_clean.py
```

[source_defined] This verifies the complete source/evidence manifests, frozen source, historical identities, original and corrected method inventories, job/result/log hashes, recorded dependency and measurement ordering, intake-identical kernel, corrected ledger provenance, independent raw native/parent/longitudinal reconstructions, inspector data and every filter. Auditors operate on copied raw panels under verification-output; delivered evidence remains untouched. Inspector pixel rendering is not claimed.

## Fresh computational reproduction

[source_defined] The commands below execute a new run; archived evidence is never overwritten or relabelled. Keep source equal to C7_Corrective_Final_Source_Freeze_v1.json. A source change requires a separately declared freeze and complete new attempt. Measurements must wait until the entire evaluation/probe pool has stopped.

```sh
python3 tools/run_corrective_release.py evidence/CorrectiveReproduction/attempt1 --stage evaluation
python3 tools/run_corrective_release.py evidence/CorrectiveReproduction/attempt1 --stage measurements
python3 tools/verify_corrective_release.py evidence/CorrectiveReproduction/attempt1
python3 tools/build_corrective_ledger.py evidence/historical evidence/CorrectiveReproduction/attempt1 evidence/CorrectiveReproduction/attempt1/Corrective_Ledger.json
python3 tools/verify_corrective_ledger.py evidence/historical evidence/CorrectiveReproduction/attempt1 evidence/CorrectiveReproduction/attempt1/Corrective_Ledger.json evidence/CorrectiveReproduction/attempt1/Corrective_Ledger_Assessment.json
```

[source_defined] The original absolute command paths are historical provenance. They are not edited to imply execution in a different workspace. A fresh reproduction writes its own paths, timings and command records. Timing results are host-specific and must meet the same fixed 3x inactive-history and 2x unchanged-native limits; no optimization gain is claimed.
