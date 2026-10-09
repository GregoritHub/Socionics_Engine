# Evidence, scope and reproduction

[Documentation index](../README.md) · [First run](First_Run.md) · [Capabilities](Capabilities.md)

## Current accepted result

[machine-checked] Release 1.0 was accepted at commit [`5c55754`](https://github.com/GregoritHub/Socionics_Engine/commit/5c55754b9068c4d47eafcbecc2ecca5d43cff316). The [decision](../../evidence/Corrective6/Delivery_Decision.json) links the full-run, independent joint and clean-delivery assessments. Earlier held decisions are preserved as historical results, not retroactively promoted.

| Measure | Accepted result | Meaning and source |
| --- | --- | --- |
| Required jobs | 54 passed | Orchestration commands, including evaluation/probes and measurement protocols; [acceptance](../../evidence/Corrective5/attempt1/Acceptance.json) |
| Distinct methods | 742 passed | Exact unique test IDs, retaining all 732 prior IDs plus ten corrective methods; [inventory](../../evidence/Corrective5/attempt1/Accepted_Method_Inventory.json) |
| Measurement workers | 81 | Isolated subprocess workers; not 81 additional semantic cases |
| Frozen files | 1,381 unchanged | [Final source freeze](../../C7_Corrective_Final_Source_Freeze_v1.json) |
| Joint coverage | 32 rows, both settings | 16 routes × two polarities, canonical and workflow evidence per row; [ledger](../../C7_Final_Ledger_v3.json) |
| Historical identities | 739 exact hashes/sizes | Distinct historical ledger objects; not the total number of delivered files |
| Fresh compressed raw files | 3,182 | Subset of the 4,284 members in the fresh raw manifest; archive also includes the manifest |
| Native continuation audit | 192 comparisons | Plus six negative worlds; see [clean raw audit](../../evidence/Corrective6/corrective-native_clean_verification.json) |
| Parent audit | Eight scenarios | Exact restores and six forged-success controls; [assessment](../../evidence/Corrective6/corrective-parents_clean_verification.json) |
| Inspector | 32 cells; 1,312 references | Hash/size checks, filters and reset passed; pixel rendering was not claimed |
| Kernel probes | 10/10 and 17/17 | Closure and below-DCNH probes on intake-identical R21B; sealed pyref reruns remain owed |

[machine-checked] Clean assembly verified **3,221 source members, 15,993 historical delivered members and 4,284 fresh evidence members**. Those counts describe different manifests and include overlapping files; they should not be added as a count of unique experiments. See [Clean_Assessment.json](../../evidence/Corrective6/Clean_Assessment.json).

[machine-checked] The native reference timing ratio was 1.067112 against a 2× limit. The largest recorded workflow inactive-history ratio was 1.070766 and population ratio 1.041623, against 3× limits. These are host-specific tolerance checks, not a claimed optimization gain. See the [release report](../HLE_Full_Crux_C7_Release_Report_v4.md) and complete acceptance record.

## What each level of reproduction establishes

| Activity | What you need | What it establishes |
| --- | --- | --- |
| [Documentation first run](First_Run.md) | A clone and Python | One fresh selected workflow and generated-Shell comparison |
| Targeted test suite | Source and the selected test directory | Those named methods on your checkout, not the full release |
| Inspect committed acceptance | A clone or GitHub | The saved result and protocol; reading it is not rerunning it |
| Exact historical delivery verification | Pinned source plus every indexed archive | Byte identity, provenance and independent raw reconstruction of saved evidence |
| Fresh full computational rerun | Pinned source, required restored input, fresh output directories and full protocol | New evaluation/measurement results on your host |

## Access to raw evidence

[source_defined] The repository contains the engine, protocols, manifests, assessments and some smaller evidence artifacts. Large archives are held separately and referenced by exact file identities and SHA-256 values. Their presence in an index does **not** mean an unauthenticated GitHub visitor can download them. Access remains subject to the archive owner's authorization. This documentation does not republish private files or change their permissions.

- [Historical component index](../../evidence/FB6.3/Durable_Components.json): thirteen original components.
- Prior corrective archives: [Corrective1](../../evidence/Corrective1/Raw_Evidence_Index.json), [Corrective2](../../evidence/Corrective2/Raw_Evidence_Index.json), [Corrective3](../../evidence/Corrective3/Raw_Evidence_Index.json).
- [Fresh corrective archive](../../evidence/Corrective5/Raw_Evidence_Index.json): saved and downloaded again with matching whole hash and ZIP integrity.
- [Historical reassembly assessment](../../evidence/Corrective6/Historical_Reassembly_Assessment.json): verified exact identities, hashes and sizes.

If you do not have an indexed archive, you can still run the small example and inspect committed code/results. You cannot claim to have independently reproduced the complete historical release. Do not substitute regenerated bytes for missing historical objects or bypass access controls.

## Exact accepted source and complete commands

[source_defined] The accepted source delivery is pinned at [`83621ec`](https://github.com/GregoritHub/Socionics_Engine/tree/83621ecddac7384f025f02ba3a5228f48256fb5f), with [source manifest](../../C7_Corrective_Delivery_Source_Manifest_v1.json) and [archive index](../../evidence/Corrective6/Source_Archive_Index.json). Current researcher documentation is newer than that immutable snapshot. An old full-delivery manifest need not match newer README bytes; the evaluated engine source freeze remains unchanged.

For a separate pinned worktree after cloning:

```sh
git worktree add --detach ../srl-release-1.0 83621ecddac7384f025f02ba3a5228f48256fb5f
```

Then follow [FB_Corrective6_Reproduce.md](../FB_Corrective6_Reproduce.md) exactly. It describes the 16-component historical reassembly, common source/evidence root, clean verifier and complete evaluation commands. The reassembler requires a new destination, verifies archive hashes and rejects differing collisions. The full computational run also requires the exact restored FB5.6 recurrence input at its recorded path; a bare clone must not pretend to supply it.

The full run has separate **evaluation** and **measurements** stages. Wait until all evaluation processes stop before measurements; preserve the prescribed worker isolation and tolerances. The old absolute execution paths in command records are provenance and must not be rewritten to suggest a different machine executed them. A fresh run records its own paths and times.

The standalone [inspector](../HLE_Full_Crux_C7_Inspector_v4.html) can be downloaded and opened locally. It embeds the per-cell data and references; full raw-evidence inspection requires the assembled package. GitHub's source-file view is not the interactive inspector.

## Running a new experiment

[source_defined] State the question, applicable domain, alternative explanation, control, outcome and failure condition before altering behavior. Use a separate branch and new output directories. Keep original contracts, baseline files, accepted worlds and failed attempts intact.

Prefer discriminating questions: does withholding a received result change a later answer? Does a hidden change leave the actor's information unchanged until paid access? Does a local correction survive the declared renewed demand? Does a real consent withdrawal prevent an unauthorized commit? Distinguish a hypothesis from a fixture condition and a record count from a semantic consequence.

Freeze the executed code before a counted run. Compare exact method identities, not totals alone. Preserve raw worlds, command records, hashes, failures and controls. An ordinary auditor should reject a deliberately invalid control; a control reaching a desired endpoint does not make it valid. Report unsupported or untested claims explicitly.

[open] Human validity, general learning, unrestricted meaning, universal Shell detection, source rulings and pyref reruns remain outside the software acceptance decision. Phase 7 requires separate explicit R5 authorization. Existing license notices and rights are unchanged.
