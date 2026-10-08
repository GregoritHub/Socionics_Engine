# FB6.2 — Frozen evidence run complete; release acceptance withheld

[source_defined] Entry: accepted FB6.1 at `dda44b3dc6b7cf91ef72d430066bb227a2df27c9`, with the approved FB5.3–FB5.6 amendment. The original plan permits the 6.2 exit when every executed-file hash matches and panels pass **or failures are recorded against their cells**. The execution is complete; three unsupported release-evidence claims are recorded against all 32 affected cells. This is not an unconditional release acceptance.

## What changed

[source_defined] Added three tools: the frozen command runner, an independent canonical-family saved-world verifier, and the exact regression/measurement assessment. No engine module, inherited contract or baseline file changed. The previously absent phase-specific evaluation protocol was committed prospectively at `903367a934831ffee92a362bc2a7366a0d1fb89c`, before implementation/evaluation. Protocol SHA-256: `db508117b91030d6683d474381210e9fac53c83764cfce6041c8f8e710b187c3`. This does not retroactively preregister FB6.1.

## How

[machine-checked] Restored all 3,089 entry repository files by exact Git blob identity. Twelve historical archives matched their recorded sizes/digests. The exact FB0.1 archive supplied the five intake kernel hashes; all five match the sealed R21B files. Original archives and historical failures remain unchanged.

[machine-checked] `C7_Final_Source_Freeze_v5.json` covers 1,355 source, contract and tool files. SHA-256: `0a5ec54771c04838c0a1b41a82e3adc4e91eae20c0daed8a16c3aec147c414f7`. Source/freeze commit: `a060509eb4146e06c2a9ecaca5c0c9f19c8558ee`. Every command's before/after guard and the final assessment matched it. The engine, baseline, contracts and tools also have no diff against the local frozen snapshot.

[source_defined] Commands: `python3 tools/run_c7_final_regression.py evidence/FB6.2/attempt1 --stage all`, followed by `python3 tools/verify_c7_final_regression.py evidence/FB6.2/attempt1`. The 47 mandatory commands, stdout, timestamps, exit codes, source guards, summary digests, 81 isolated worker outputs and assessment command are preserved in the archive. Measurements ran sequentially after the entire evaluation/probe pool stopped.

## Executed results

[machine-checked] On the unchanged R21B-based implementation: 732/732 distinct accepted method IDs passed (602 inherited and 130 additional), with exact prior-ID equality, no omissions, skips, failures or duplicate executions. The 512 scripted and 512 automatic workflow panels and their separate 32-control panels passed saved-world reconstruction. Workflow Shell prevention/interruption/development, five composition families, nesting, polarity faces, population, generated-content continuation, five continued families and the sustained 32-cell panel passed their implemented checks. The longitudinal panel reconstructed 29 worlds and two restore pairs, subject to the negative-control limitation below.

[machine-checked] Fresh canonical choice/type/responsiveness verification checked 583 worlds (551 valid and 32 deliberate ablations); canonical Shell checked 143 raw witnesses; canonical families checked 15 worlds and seven causal pairs; canonical population checked 12 final/intermediate worlds. Both probes passed: closure 10/10 and below-DCNH 17/17. The sealed 5.2.1 pyref was not supplied and its separate probe rerun remains owed.

[machine-checked] All 81 isolated cost workers passed unchanged thresholds. Native/reference median ratio: 1.282084 (limit 2). Native inactive-history ratio: 1.127849 (limit 3). Workflow unique/shared ratios: 1.066942 / 1.062025; population unique/shared ratios: 1.058579 / 1.129317 (all limit 3). These are measurements on this host, not optimization gains.

[machine-checked] The run retained 2,373 compressed raw files. The supplemental historical ledger verifier agreed with its implemented 32-row checks and verified 739 declared member hashes. It uses summaries for several gates, so this result does not establish the missing raw-denominator proof.

## Failures, corrections and evidence limits

[source_defined] No command exited with an evaluation failure; no counted source changed. A preliminary connector checkpoint errored before moving main; the prospective protocol was subsequently committed and verified before evaluation.

[open] The final review found three unsupported claims, detailed with exact instructions and source hashes in `Release_Evidence_Findings.json` and mapped to every affected cell in `Cell_Evidence_Failures.json`: (1) the final §9.8 ledger does not establish all 192 boundary/setting continuation comparisons from indexed raw pairs; (2) canonical §9.11 membership-change and withdrawal parent worlds are not separately indexed; (3) the longitudinal verifier counts a forged-completion rejection by unconditionally raising/catching an exception, without submitting a forged completion to the auditor. Its reported count of six is preserved, but does not prove all six declared tamper controls.

[source_defined] The unmodified command-level assessor's `attempt1/Acceptance.json` is preserved exactly. The reviewed root `Acceptance.json` has `passed: false` and `execution_passed: true`, preventing the older ledger builder from promoting unsupported full-release claims. Nothing is relabelled as an engine failure; nothing unsupported is relabelled as passed.

## What becomes possible and handoff

[derived] Batch 6.3 can package the verified source, execution evidence and precise open rows, then decide under the plan's explicit held-release option. All 32 full-release cells remain open. Phase 7 remains unauthorized and the goal remains incomplete. Evidence restoration uses `evidence/FB6.2/Raw_Evidence_Index.json`; the immutable archive contains 3,466 files and the complete raw SHA-256 manifest. The archive passed ZIP CRC/member-count checks and was durably saved. Its exact Library/file IDs are in the index. Archive SHA-256: `62a5a4852ad756b54ec62ca4e0b47c03a50017ec21f96c916333f6447cf47043`.
