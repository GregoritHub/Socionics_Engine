# FB6.1 — Joint §9 ledger

[machine-checked] Batch 6.1 is complete. `tools/evaluate_c7_final.py` built `C7_Final_Ledger_v1.json` as 32 route/polarity rows × two settings. Every evidentiary field names an immutable archive, saved raw member, byte count and SHA-256. No module count, historical pass label or prose-only inheritance closes a cell.

## What changed

[source_defined] Added the joint ledger builder and a separately implemented verifier. The builder integrates canonical C2–C7 evidence with accepted FB2.4–FB5.6 workflow evidence. The verifier does not import the builder; it reconstructs the expected section status from saved worlds and only then compares the ledger.

## How

[machine-checked] Five original evidence archives and seven Final Build archives were restored without rewriting them. The builder linked per-cell semantics, changed content, mechanism, downstream consequence, matched semantic control, automatic selection, both Shell phases, polarity comparison, partial continuation, type coverage, costs, five-family applicability and the two bounded nesting panels. Non-family cells carry an explicit §9.5 non-applicability code.

[machine-checked] The verifier independently reconstructed all 32 rows, agreed with all 32, opened the complete 1,024-case two-setting type panel, and hash-checked 739 unique raw-member identities declared by the compact ledger. The accepted source freeze covers the builder, verifier and prospective final protocol.

[source_defined] Accepted FB6.1 archive version 2: `Socionics_Final_Build_FB6.1_Evidence.zip`, 4,182 bytes, seven files and no directory entries, SHA-256 `e431d3b472acbae2cbb124d10d002dc29e132edc61142fe9bd1b81f6c0fb005e`. Exact durable identities, both preserved prior-version identities and restoration instructions are in `evidence/FB6.1/Raw_Evidence_Index.json`.

## What becomes possible

[derived] Batch 6.2 can now add a release-freeze acceptance object and rebuild the same ledger without changing its schema. That is the only currently missing ledger item: every row is false solely on §9.12 until the frozen regression, panels, probes and measurements run.

## Commands and counts

- [machine-checked] `python -m py_compile tools/evaluate_c7_final.py tools/verify_c7_final.py` — exit 0.
- [machine-checked] `python tools/evaluate_c7_final.py <restored-evidence-root> C7_Final_Ledger_v1.json` — 32 rows, 0 complete, release freeze absent, exit 0.
- [machine-checked] `python tools/verify_c7_final.py <restored-evidence-root> C7_Final_Ledger_v1.json --output evidence/FB6.1/attempt1/independent_verification.json` — 32 reconstructed, 32 agreed, all 1,024 type worlds opened and 739 ledger-declared raw members hash-checked, exit 0.

## Failures and fixes

[machine-checked] Two provisional expectations were wrong: canonical controls were expected to pass the ordinary auditor, and FB4.2 face rows were expected per polarity rather than per route pair. Both failures are retained in `evidence/FB6.1/attempt1/Failure_Log.md`; neither run counted. The corrected accepted run occurred after the source freeze.

## Freeze and next state

[source_defined] Accepted FB6.1 source freeze: `evidence/FB6.1/attempt1/source_freeze.json`. Ledger SHA-256: `86aac0409319b470989540750c1beaef8216b94e968a4437dd254ecd204a531d`.

[open] Release 1.0 is not yet complete. Next is FB6.2, freeze/regression/measurement. Phase 7 remains forbidden without explicit R5.
