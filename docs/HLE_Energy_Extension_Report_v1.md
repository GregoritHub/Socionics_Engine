# HLE Energy Extension Report v1

[source_defined] Authorized Phase 7 / Release 1.1 candidate, 2026-10-12 UTC. Authority: [R5](FB7_R5_Authorization.md), [Energy Contract v1](../contracts/Energy_Contract_v1.md), and the prospectively hashed [Energy Protocol v1](../contracts/Energy_Protocol_v1.json). Release 1.0 acceptance remains unchanged. The default remains `legacy-r4`.

## Decision

[machine-checked] P1, P2 and P3 held on the complete declared panel. All 751 regression methods passed, including every exact one of the 742 required legacy IDs. All 68 sequential isolated cost samples completed, and every inherited performance guard passed. The candidate is evaluated successfully; the final clean-package receipt governs delivery: [current delivery decision](https://github.com/GregoritHub/Socionics_Engine/blob/main/evidence/FB7.4/Delivery_Decision.json).

[derived] `grade-v1` is available only through creation-time opt-in. The model identity is immutable and retained in checkpoints. Time, route construction and support rules are unchanged. Full Model A step energy is charged once on the first paid time unit; subsequent time quanta can finish a prepaid step with zero remaining energy. Cancellation does not refund spending. Other work retains equal energy/time charging. The auditor independently uses the literal CT price table.

## Predictions

[machine-checked] The same 1,398-file executable/contract freeze governed accepted generation, regression, independent auditing and measurement. Manifest SHA-256: `03ad3ddc069b501aae7da0f700d234499dfd3bbc9ae504b5a2be89334004da8e`. Evaluators/auditors were part of that freeze; no source, price, funding or tolerance changed during accepted execution.

| Prediction | Result | Declared evidence |
|---|---|---|
| P1: ample invariance | Held | All 548 ample pairs matched: 512 automatic (32 cells × 16 types), four core populations and 32 extension populations. Full normalized transactions, access nodes/events, population events and actual outputs were compared. Only model metadata and the recorded energy components were exempt. |
| P2: exact accounting | Held | Raw reconstruction passed for all 1,240 paired engine histories and 64 withheld-child controls. Independent time/energy reconstruction and ordinary semantic audits agreed; all 64 missing-native-child controls were rejected. Nine new tests include exact prices/offsets, restoration, cancellation, zero-energy prepaid continuation and tamper rejection. |
| P3: scarcity divergence | Held | One of the 72 registered scarce pairs qualified: `core-diagnostic-17-tight-energy`. All other scarce pairs remain in the denominator; no wallet tuning followed the result. |

[machine-checked] In the qualifying pair, the synthetic SLI actor Bob began with energy 2,000 and time 200,000 under both models. Legacy stops at episode index 21, native work 31/45; grade-v1 stops at episode index 19, native work 21/39. Both energy balances are zero and the next paid unit requires one energy. Remaining time is 198,000 versus 198,190. Independent sums over the actually traversed positions account for both currencies; the full per-position debit table, raw hashes and outcomes are in [Scarcity_Witnesses.json](../evidence/FB7.4/Scarcity_Witnesses.json).

## Conditioning observations

[machine-checked] [The complete population table](Phase7_Population_Conditioning_Tables.md) contains 648 actor rows from all 216 current population histories, including inactive profiles and their all-zero ties. Axis-load winners, ties and separate formula sums are shown as observations only.

[machine-checked] Historical reconstruction additionally verified all 394 source aliases (225 original Phase 5 inputs plus 169 accepted corrective aliases), deduplicated to 153 byte-distinct engine histories. No execution module was imported by the standalone reader. Held, uncredited, interrupted and control cases remain separately labeled; one forged transaction-only negative control is explicitly excluded from the engine-envelope set, not silently discarded. Exact input identities and outcomes are in [FB7.3](FB7.3_Record.md).

[source_defined] A completed Model A hop or seat-content block contributes one element use; unfinished and non-Model-A work contribute zero. Greatest-load cells are not subtypes. The UMA section 15 formula-attribution caveat remains unresolved. No engine, selector, scheduler, price rule or Shell rule reads the conditioning ledger.

## Measured costs

[machine-checked] Median seconds below exclude one warmup and use three measured isolated subprocesses per world/model, after other evaluation workers finished. Checkpoint, restore and raw-audit costs are separate. Every measured restore was byte-exact and independently audited. Timings were untraced on Python 3.12.14 / the recorded shared Linux host. All samples, including warmups, are retained.

| Core world | Model | Execute s | Checkpoint s | Restore s | Raw audit s | Native completions |
|---|---|---:|---:|---:|---:|---:|
| default-17 | legacy-r4 | 1.704 | 0.093 | 2.249 | 1.728 | 4 |
| default-43 | legacy-r4 | 1.737 | 0.090 | 2.241 | 1.705 | 4 |
| default-89 | legacy-r4 | 1.739 | 0.107 | 2.350 | 1.819 | 4 |
| diagnostic-17 | legacy-r4 | 19.840 | 0.378 | 21.271 | 18.651 | 48 |
| default-17 | grade-v1 | 1.864 | 0.075 | 2.493 | 1.870 | 4 |
| default-43 | grade-v1 | 1.797 | 0.086 | 2.301 | 1.826 | 4 |
| default-89 | grade-v1 | 1.737 | 0.083 | 2.332 | 1.802 | 4 |
| diagnostic-17 | grade-v1 | 19.577 | 0.322 | 20.698 | 17.694 | 48 |

[machine-checked] All four matched legacy checkpoints also equal the pre-extension reference bytes across runs. The largest candidate/reference active-time ratio was 1.0201× (limit 2×). Unique/shared inactive-history ratios were 1.0433× and 1.0165× (limit 3×), for 0/100/1,000 inactive records. [All 68 samples and guards](../evidence/FB7.4/costs1/summary.json) remain available. These are bounded engineering measurements; no optimization or memory-improvement claim is made.

## Reproduction and preserved failures

[derived] Use [Phase7_Reproduce.md](Phase7_Reproduce.md) for the model switch, exact commands and historical input recovery. [Panel verification](../evidence/FB7.4/Panel_Verification_Summary.json), [the 751-method inventory](../evidence/FB7.4/Accepted_Method_Inventory.json), [FB7.4 record](FB7.4_Record.md), and [raw archive index](../evidence/FB7.4/Raw_Evidence_Index.json) bind the reports to their executable and raw evidence. The archive is private; an index does not grant unauthenticated access.

[derived] The first evaluation harness attempted to serialize a request object as a summary value; corrected summaries retain actual consequences while requests remain in raw records. Initial generation and regression eventually failed their source-unchanged gates and receive no acceptance credit. A nested energy-charge comparison was corrected during development. The incomplete serial audit exited130; four disjoint 155-pair invocations of the unchanged auditor provide the accepted union. Failures, controls, exact partition membership and original logs are retained.

## Limits

[source_defined] This is the authorized engineering hypothesis, not a model of biological energy, psychological calibration or subtype identification. There is no energy regeneration, energy-based route optimization, conditioning feedback, new goal generation or default promotion. The sealed baseline and unrelated Shell research are preserved. Existing finite-world/workflow bounds and the separately owed, nonblocking sealed 5.2.1 reference-kernel rerun are unchanged. No theoretical ledger item is closed by this implementation.

## Final delivery

[machine-checked] The [final decision](../evidence/FB7.4/Delivery_Decision.json) accepts the candidate and completes batches 7.1–7.4. Clean extraction verified all 1,398 frozen files, 1,093 sealed-baseline files, both contract hashes and four focused restoration/conditioning checks. All eight measured model/core checkpoints exactly match their saved panel counterparts across all four cost samples. The immutable [candidate source snapshot](https://github.com/GregoritHub/Socionics_Engine/archive/689aabde7927cfb993245e35265bb9ad72b5d210.zip) is pinned to commit 689aabde7927cfb993245e35265bb9ad72b5d210. The separately verified local ZIP's identity is recorded in the receipt; GitHub's archive packaging may produce a different compressed-file hash from the same tree. The candidate contains assembly-era administrative state; this later receipt governs completion without changing executable source. The legacy default is retained and continuation remains disabled.
