# HLE unified engine — U1 baseline and migration contract

U1 freezes the supplied R21B implementation and establishes the migration contract for U2. The 98 runtime modules are unchanged. This package contains the complete frozen source tree, inherited fixtures and packaged evidence, U1 reproduction tools, and prospective requirements for the unified object engine.

Read docs/U1_Report_v1.md for results and limits. The original R21B release handoff remains historical evidence; U1 does not renew R21C release acceptance.

## Contents

| Path | Contents |
| --- | --- |
| baseline/HLE_Rebuild_R21B | Complete frozen supplied archive contents, including all 3,044 files. |
| contracts/Input_Manifest.json | Input archive/source hashes and every baseline member's identity. |
| contracts/Original_Evidence_Inventory.json | Member hashes for the two separately supplied R21B evidence archives. |
| contracts/U1_Protocol_v1.json | Protocol frozen before the U1 evaluation. |
| contracts/Migration_Contract_v1.md | Protected properties, comparison rules, access boundaries, and U2 interfaces. |
| contracts/Module_Migration_Map_v1.json | All 98 runtime modules, 338 classes, record fields, and intended migration treatment. |
| contracts/Protection_Regression_Index_v1.json | 33 selected inherited regression references covering the 16 protected properties within their baseline scopes. |
| contracts/New_Engine_Acceptance_v1.json | 45 prospective conformance cases for U2–U14; eight specifically define U2. |
| contracts/Efficiency_Acceptance_v1.json | Quantitative future targets, frozen after measuring baseline and before optimization. |
| contracts/Scope_Ledger_v1.json | Historical results, fresh U1 findings, and open claims. |
| contracts/Target_Conception_v1.md | Unchanged supplied architectural destination. |
| contracts/Roadmap_at_U1_Start.md | Roadmap before U1, retained for progress history. |
| tools | Verification and reproduction commands. |

Fresh U1 logs, traces, summaries, and measurements are delivered in the separate evidence archive. Original R21B evidence parts remain separately identified inputs; their 140 expected external trace members were checked during U1. The U1 evaluation commands below generate new traces and do not require those old external traces to be unpacked.

## Reproduction

Use Python 3.12 and its standard library. Run from this package's root. The paths below are examples; choose a new output directory.

Verify the complete frozen source:

    python tools/verify_baseline.py

Run the declared validation, paired behavioral cases, controls, performance workload, and checkpoint measurements:

    python tools/reproduce_u1.py --out /tmp/hle-u1-reproduction

The output directory must not already exist. The command creates a separate execution copy and writes fresh evidence there. It retains failures and exit codes. Performance measurements run after the other compute jobs finish. Reproduction takes substantial time because it includes all 912 inherited tests and complete developmental episodes.

For an individual stage, use an isolated execution copy and a fresh evidence directory:

    python tools/u1_evaluate.py --engine /tmp/hle-u1-reproduction/engine --out /tmp/hle-u1-checkpoints --stage checkpoints

The supported stages are validation, behavior, performance, and checkpoints. The checkpoint-one mode is used internally to isolate memory measurements.

## Scope

The paired U1 panel uses IEE/12 and SLI/11 in adequate, constrained-feasible, and zero-budget regimes. Two IEE/12 controls reproduce no-reuse and legacy-cost behavior. Repeated controls and audits are not counted as additional population evidence.

The active/inactive-history benchmark continues the inherited R20 performance world on the R21B runtime, with its separately declared performance allocation. The current v4 continuing checkpoints have separate storage, restore, and live-allocation measurements. Neither measurement substitutes for R21C's complete release panel.

All future conformance cases are requirements, not new runtime passes. U2 begins with common identities, versioned object roles, first-class relations, and exact legacy adapters.

