# HLE unified object engine — U3

Compact particulars and situated access · 21 September 2026

This cumulative source package contains the frozen R21B baseline, unchanged U1/U2 contracts and execution source, and the U3 storage/access implementation. See `docs/U3_Compact_Particulars_and_Situated_Access_v1.md` for the versioned contract and `docs/U3_Report_v1.md` for final evidence and limits.

Run the full U3 milestone gates with Python 3.12 and the standard library:

    python tools/reproduce_u3.py --out /tmp/hle-u3-reproduction

Choose a new output directory. The command records all results, including failures, and runs the U3 suite, all 31 U2 tests, 71 selected inherited regressions, native and legacy witnesses, and before/after baseline checks. Runtime and evaluation source hashes must remain unchanged throughout the final run.

Inspect a retained actor view:

    python tools/inspect_u3.py /tmp/hle-u3-reproduction/u3_witnesses/situated.completed.checkpoint.json --actor alice

The public additions are in `hle_unified.u3`: `CompactStore`, `AccessLedger`, `ParticipantView`, `Grant`, `Selector`, and `DetailAddress`. Put this directory and `baseline/HLE_Rebuild_R21B` on `PYTHONPATH` when importing them directly. U2 APIs and wire formats remain available unchanged; their original README is preserved as `docs/U2_README.md`.

U3 imports actor-owned processing evidence through a checked adapter. It does not supply U4's native paid operation executor. Contextual binding access does not complete U5's integrated Model A/Fool's Memory circuit. Physical execution, general learning, efficiency acceptance and release claims retain their later gates.

The baseline makes this archive large: it deliberately includes the complete preserved source, historical evidence and original artifacts for reproducibility.
