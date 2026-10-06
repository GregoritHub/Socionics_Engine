# HLE unified object engine — U4

This source package extends the verified U3 source with a native paid operation lifecycle and declared workshop material interactions. It preserves the frozen R21B baseline and all earlier protocols, tests, tools and reports; the previous root README is `docs/U3_README.md`.

Read `docs/U4_Report_v1.md`, `docs/U4_Operation_Lifecycle_and_Material_Interactions_v1.md`, and `docs/Implementation_Roadmap_After_U4.md` for results, scope and next work.

Python 3.12 and the standard library are sufficient. From this directory:

    python tools/reproduce_u4.py --out /tmp/hle-u4-reproduction

Use a new output directory. This runs U4, U3, U2, selected inherited regressions, all three native/legacy witness sets and baseline preservation checks. The complete 912-test U1 run remains historical evidence.

For imports, place this directory and `baseline/HLE_Rebuild_R21B` on `PYTHONPATH`. Use `hle_unified.u4` for `OperationEngine`, `OperationRequest`, `OperationStore`, `NativeAccess` and `audit_transactions`. Existing U2 and U3 imports keep their original roles.

All native costs, condition/wear rules, resource sinks and reservation choices belong to `u4.finite-workshop-v1`. U5 integration, U13 efficiency and U14 release acceptance remain open. No external package, API key, network service or model inference is required to reproduce this deterministic milestone.
