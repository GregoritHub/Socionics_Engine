# Socionics Research Lab — Release 1.0 assessment

[source_defined] 8 October 2026 · report v3 · **RELEASE HELD**. Milestone C7 remains 6/7; 0/32 full-release rows are complete. The amended goal is not complete. Phase 7 has not started and requires the author's separate R5 ruling.

## Decision

[source_defined] Final Build Plan batch 6.3 says: “If not, hold, and list the open rows. Either is an acceptable outcome of this batch.” The reviewed ledger follows that rule. Command-level success cannot supply missing evidence or make an unexecuted negative control pass.

[machine-checked] Batch 6.2 completed all 47 declared commands on the unchanged 1,355-file source freeze. All 732 distinct accepted method IDs passed with exact ID equality, all 81 isolated cost workers passed, and both kernel probes passed. The raw run contains 2,373 compressed files. Engine code, baseline files and inherited contracts were not changed in this final assessment.

[open] Three underlying evidence defects prevent release:

1. **§9.8 continuation coverage.** The final protocol declares 192 comparisons: 32 cells × two settings × three boundaries. The final ledger verifier checks 32 workflow interruption restore pairs; passing regression methods exercise additional boundaries, but a complete raw per-boundary/settings mapping is not established.
2. **Canonical §9.11 nesting.** The four scenarios require ordinary, failed-child, membership-change and withdrawal evidence in each setting. The canonical exported parent/context/cancelled-child worlds do not separately identify the membership-change and withdrawal worlds. Their regression method passes; that is not a replacement for the required raw references.
3. **FB5.6 negative control.** `verify_longitudinal_shell.py` reports six tamper rejections, but the forged-completion branch raises and catches an exception without constructing/submitting a forged completion. The original protocol requires all six actual controls. The count is preserved as a historical tool result and is not credited as proof.

[source_defined] Exact source instructions and hashes are in `evidence/FB6.2/Release_Evidence_Findings.json`; every affected cell is listed in `Cell_Evidence_Failures.json`. The old joint ledger remains unchanged as `C7_Final_Ledger_v1.json`. `C7_Final_Ledger_v2.json` is the current reviewed decision. Its §9.12 status is held because the reviewed release acceptance is withheld despite successful execution checks.

## What changed, how, and what becomes possible

[source_defined] The final work added a frozen command runner, independent canonical-family reconstruction and exact test/measurement assessment. The Model G and axis layers remain read-only structure from their accepted batches. The accepted generated-content continuation and sustained-panel mechanisms remain present. No theoretical register item is closed by this assistant.

[derived] The delivered inspector gives each cell's three-question view, fresh witness/control links and release limitations. The evidence package permits inspection of actual saved checkpoints, histories, command logs, failed attempts and digests. It supports bounded research and exposes the unsupported release claims without altering their historical records.

## Frozen execution evidence

[machine-checked] These are implemented checks on the R21B-based engine; the negative-control limitation above remains explicit.

| Check | Result |
| --- | --- |
| Exact accepted test inventory | 732/732 distinct; no missing, duplicate, failed or skipped IDs |
| Workflow scripted matrix | 512 worlds + 32 matched controls, independently reconstructed |
| Workflow automatic matrix | 512 worlds + 32 withholding controls, independently reconstructed |
| Sustained amendment panel | 32/32 cells with paid generated-result consumers and matched withheld controls |
| Continued families | All five; raw reconstruction and causal controls |
| Longitudinal Shell | 29 raw worlds, two exact restore pairs; forged-completion control remains unproved |
| Canonical choice/type/responsiveness | 583 worlds: 551 valid and 32 deliberate ablations |
| Canonical Shell | 143 raw witnesses |
| Canonical families/nesting/context | 15 worlds and seven causal pairs; missing raw nesting scenarios remain open |
| Canonical population | 12 final/intermediate worlds |
| Kernel probes | Closure 10/10; below-DCNH 17/17; five intake kernel hashes unchanged |
| Frozen files | 1,355, matched before/after commands and at final assessment |

[source_defined] The source/freeze was committed before evaluation at `a060509eb4146e06c2a9ecaca5c0c9f19c8558ee`. Freeze SHA-256: `0a5ec54771c04838c0a1b41a82e3adc4e91eae20c0daed8a16c3aec147c414f7`. The phase-specific protocol was committed earlier at `903367a934831ffee92a362bc2a7366a0d1fb89c`; SHA-256 `db508117b91030d6683d474381210e9fac53c83764cfce6041c8f8e710b187c3`.

[machine-checked] The command-level assessor's original `attempt1/Acceptance.json` remains preserved. The reviewed root `evidence/FB6.2/Acceptance.json` has `execution_passed: true` and `passed: false`. This prevents the older convenience predicate from promoting incomplete evidence to release completion.

## Measured costs

[machine-checked] Measurements ran one protocol/worker at a time after every evaluation/probe job finished. The native panel used 33 workers, workflow 24 and workflow population 24. Ratios compare the specified medians on this host.

| Panel | Ratio | Fixed limit |
| --- | ---: | ---: |
| Unchanged native API / preserved C5 | 1.282084 | 2.0 |
| Native inactive history | 1.127849 | 3.0 |
| Workflow unique / shared history | 1.066942 / 1.062025 | 3.0 |
| Population unique / shared history | 1.058579 / 1.129317 | 3.0 |

[source_defined] No optimization gain, constant-time total execution or general cost-per-capacity claim is made. Raw timing, restoration, audit, trace and platform records are retained separately.

## Open rows

[open] Each row remains false. The reviewed §9.12 hold follows from the underlying evidence defects, not from a failed timing measurement.

| Route | Polarity | Open evidence items |
| --- | --- | --- |
| Contemplate | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Contemplate | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Act | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Act | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Express | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Express | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Share | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Share | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Theorize | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Theorize | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Embody | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Embody | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Coordinate | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Coordinate | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Organize | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Organize | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Identify | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Identify | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Mobilize | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Mobilize | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Commune | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Commune | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Institutionalize | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Institutionalize | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Understand | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Understand | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Apply | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Apply | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Educate | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Educate | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Integrate | accumulation | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |
| Integrate | expenditure | §9.8; canonical §9.11; FB5.6 control; reviewed §9.12 |

## Delivery and reproduction

[source_defined] Source: `Socionics_Research_Lab_Release_1_0_Held_Source_20261008.zip`. Evidence: `Socionics_Research_Lab_Release_1_0_Held_Evidence_20261008.zip`. Extract both into one empty directory; both use the root `Socionics_Research_Lab_Release_1_0_Held/`. The repository preserves the source and documents. Exact archive identities, checksums and restore instructions are in `evidence/FB6.3/Delivery_Index.json`.

[source_defined] From the unpacked root, use the commands in `docs/FB6.3_Reproduce.md`. They verify the source/evidence manifests, the unchanged freeze, the 739 historical ledger references, all FB6.2 file hashes, the 32-row held decision, the inspector data/filters and ordinary canonical-family reconstruction. Results are recorded separately in `evidence/FB6.3/Clean_Unpack_Verification.json`. The older final verifier is a historical implemented check and is not a validator of the reviewed v2 decision.

[source_defined] To repeat the entire unchanged 6.2 command run without overwriting the delivered attempt:

```sh
python3 tools/run_c7_final_regression.py evidence/reproduction-6.2 --stage all
python3 tools/verify_c7_final_regression.py evidence/reproduction-6.2
```

[source_defined] Original command records retain their actual absolute execution paths. A newly executed run records its own paths. The command assessor's success does not resolve the three known proof defects. The sealed 5.2.1 pyref remains unavailable and its separate rerun is owed, as the plan explicitly permits.

## Limits and remaining work

[source_defined] Workflow claims stay within eight tasks, eight inputs, two participants, unit-duration serial scheduling and slots 0–1,000. The work does not establish unrestricted meaning, general learning, spontaneous institutions, open-ended growth, a universal Shell detector, calibrated energy rates or claims about people. Reading, assent and practiced ability remain distinct. The inspector has structural/event verification only; pixel rendering is not claimed.

[derived] Resolving this hold requires the missing indexed continuation/nesting worlds and a real forged-completion negative test, with prospectively declared validation, a new source freeze if executable files change, and the required rerun. No baseline reinterpretation or theoretical ruling is implied by these evidence defects. Under the user's standing instructions, continuation stops after this formal held decision; the revised goal remains incomplete.
