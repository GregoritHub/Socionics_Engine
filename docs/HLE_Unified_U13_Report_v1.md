# HLE unified object engine — U13 report v1

21 September 2026 · **U13 complete · 13/14 milestones complete · one remains: U14.**

U13 meets the unchanged U1 efficiency targets and the prospective same-feature U13 targets. All 95 measurement gates, 1,357 distinct tests, 31 inherited institutional witness checks and 5 archive/witness comparisons pass. No protected semantic mismatch or modeled price change was accepted. The earlier candidate that failed the active-time target is retained in full.

## Measured result

Ratios are candidate/reference; lower is better. Primary ratios use geometric means of per-case medians. A ratio of 0.85 was the frozen maximum for each primary target.

| Scope | Ratio | Reduction | Gate |
| --- | --- | --- | --- |
| Legacy participant time, six cases | 0.4631 | 53.7% | Pass |
| Legacy restored live Python allocation, two checkpoints | 0.6398 | 36.0% | Pass |
| Native participant time, nine cases | 0.5747 | 42.5% | Pass |
| Native restored live Python allocation, three cases | 0.8114 | 18.9% | Pass |
| Complete institutional episode time, two contexts | 0.6561 | 34.4% | Pass |

These are engineering measurements of declared workloads, not claims about all workloads or psychological validity. The episode timing includes initialization and paid acquisition, whereas the primary active timing excludes setup and assessment.

## Changes and preservation

- Compiled record schemas retain every original strict type and local consistency check.
- Typed structural hash buckets verify equality before sharing, with compact integer addresses and unchanged canonical wire order. Separate identities and bool/int values cannot merge.
- Revision anchors bound historical object lookup to at most 32 rows without adding wire records. Identity checks use existing indexes rather than copying all inactive heads.
- Exact typed keys remove repeated serialization in participant-particular lookups.
- The explicit legacy adapter shares equal immutable values only after original restoration validates them. Its temporary tables are discarded; mutable worlds remain separate.
- Actor-specific root, capacity and signature checks are cached within one synchronous circuit command. Every commit disables the cache through all publication layers, then clears it; completion, nesting and exceptions also clear it. Paid work and decisions execute normally.
- Checksummed chronological gzip segments retain exact transaction history and support one-segment inspection and full validated reconstruction. They are an offline history projection, not a substitute for a live engine checkpoint.

The existing actor-owned receipt, acquisition, dependency invalidation and event dispatch contracts remain authoritative. No new free learning, work scheduling policy or participant power is introduced. All 3,044 frozen R21B members and its 98 runtime modules remain byte-identical. The unchanged U12 reference retains all 92 supplied native/fixture Python members.

## Frozen comparison and provenance

`contracts/Efficiency_Acceptance_v1.json` is unchanged from U1. `contracts/U13_Protocol_v1.json` was frozen before runtime tuning; the supplemental interaction protocol was declared before its first execution. No budgets were weakened after failure.

The legacy panel uses the unchanged R21B 32-choice workload: two warmups and nine measured repetitions for each history/workload pair, with scheduled orders drained. Its two v4 checkpoints use three timed restores and separate traced restores. The same-feature native panel uses the exact U12 reference, eight paid reads per batch, one warmup, three measurements, and three timed restores. Retained-allocation comparisons use 1,000 inactive objects for each native shape. Memory tracing starts after checkpoint text allocation and follows equal warm imports.

All measurement workers run sequentially, with other task-owned tests and profiling stopped. Following the failed first candidate, the six completed legacy reference cases were reused from that run after exact reference source, fixture, worker, protocol, Python and platform checks. These were the first completed samples, not selected by timing. Every candidate and every other reference case ran afresh. Original commands, samples and reuse provenance are retained. Default reproduction measures both sides afresh.

Python: `3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]`. Platform: `Linux-6.18.44-x86_64-with-glibc2.39`. Process maximum RSS is descriptive and is not substituted for retained Python allocations or traced restoration peak.

Runtime manifest SHA-256: `75c3f8a147878224706939b511b5f6311f9a3cd0458c4f948d519a7b61d0816d`. Final tests and measurements record their complete execution manifests and confirm no source mutation during each run. Completion metadata is added after execution; runtime and executed inputs match the final stages exactly. The external 72 fidelity tests ran against unchanged independent baseline/probe files and do not exercise the new adapter.

## Legacy measurements

Milliseconds per 32-choice batch. Assessment is reported separately and excluded from the primary target. The median of the total is measured directly and need not equal the sum of component medians.

| History kind | Records | Ref active ms | U13 active ms | Ratio | Ref / U13 assessor ms | Ref / U13 total ms |
| --- | --- | --- | --- | --- | --- | --- |
| tick | 100 | 41.280 | 19.021 | 0.4608 | 22.085 / 21.296 | 63.150 / 40.320 |
| tick | 1,000 | 41.223 | 20.121 | 0.4881 | 21.762 / 22.029 | 63.154 / 41.419 |
| tick | 10,000 | 41.287 | 19.435 | 0.4707 | 21.893 / 21.950 | 62.838 / 40.623 |
| completed_inspection | 100 | 40.943 | 18.709 | 0.4569 | 21.802 / 21.675 | 62.745 / 40.261 |
| completed_inspection | 1,000 | 40.797 | 18.364 | 0.4501 | 21.725 / 20.665 | 63.073 / 39.006 |
| completed_inspection | 10,000 | 41.991 | 19.021 | 0.4530 | 22.318 / 21.165 | 64.112 / 40.165 |

Affected-record visits in the tick/100 case fall from 87,744 to 51,136. Every scheduled circuit order is drained. Unread notifications remain explicitly reported; they are not counted as completed processing. Resource audits, wallets, original transactions, queues and final canonical checkpoint digests match.

Restored allocation and peak are bytes; restoration is seconds; gzip counts are deterministic level-9 bytes.

| Checkpoint | Ref live | U13 live | Live ratio | Ref / U13 peak | Ref / U13 restore s | Ref / U13 gzip |
| --- | --- | --- | --- | --- | --- | --- |
| IEE | 37,018,057 | 23,792,411 | 0.6427 | 776,083,932 / 776,083,932 | 23.850 / 21.201 | 3,079,133 / 3,079,133 |
| SLI | 42,372,088 | 26,982,610 | 0.6368 | 947,689,660 / 947,689,660 | 28.304 / 24.605 | 3,779,923 / 3,779,923 |

## Native and interaction measurements

Each native case begins with the full U12 setup. Shared objects repeat equal structures, unique objects retain individual values, and dense objects link to the preceding eight objects. Separate institutional episodes exercise negotiation, public delay, dispute, independent correction, rejected unilateral change, collective revision and actual work.

| Shape | Inactive objects | Ref active ms | U13 active ms | Ratio | Ref / U13 live bytes | Ref / U13 restore s |
| --- | --- | --- | --- | --- | --- | --- |
| shared | 100 | 131.292 | 74.359 | 0.5664 | — | 4.049 / 2.523 |
| shared | 1,000 | 126.524 | 77.147 | 0.6097 | 29,912,955 / 24,065,637 | 5.068 / 3.295 |
| shared | 10,000 | 141.273 | 72.090 | 0.5103 | — | 22.781 / 13.293 |
| unique | 100 | 132.561 | 78.518 | 0.5923 | — | 3.956 / 2.530 |
| unique | 1,000 | 136.023 | 71.846 | 0.5282 | 31,765,288 / 26,431,684 | 5.428 / 3.470 |
| unique | 10,000 | 142.833 | 72.521 | 0.5077 | — | 22.953 / 14.364 |
| dense | 100 | 124.840 | 105.995 | 0.8490 | — | 3.907 / 2.663 |
| dense | 1,000 | 126.878 | 75.319 | 0.5936 | 35,720,461 / 28,504,207 | 6.421 / 3.992 |
| dense | 10,000 | 152.876 | 74.079 | 0.4846 | — | 32.936 / 19.187 |

Native memory is measured only in the declared 1,000-object cases. Every compared checkpoint, transaction stream, actor view, wallet and queue is exact. Raw results separately retain serialization, compression, evaluator, restoration and memory measurements.

| Institutional context | Ref episode s | U13 episode s | Ratio | Protected samples |
| --- | --- | --- | --- | --- |
| tool | 10.785 | 6.997 | 0.6488 | Exact |
| pump | 12.295 | 8.156 | 0.6634 | Exact |

## Regression guards and history growth

Across applicable cases, the largest active-time ratio is 0.8490 (limit 1.10), live-allocation ratio 0.8321 (1.10), restore-time ratio 1.0161 (1.25), and traced-peak ratio 1.0000 (1.00). All deterministic compressed checkpoints remain within 1.10; exact canonical checkpoint parity is also required, so compressed encoding alone cannot establish acceptance.

The following ratios compare U13 at 10,000 versus 100 inactive records, while active work stays fixed. Both limits are 2.00.

| Panel | History kind | Active-time growth | Affected-visit growth |
| --- | --- | --- | --- |
| common | tick | 1.0217 | 1.0000 |
| common | completed_inspection | 1.0167 | 1.0000 |
| native | shared | 0.9695 | 1.0000 |
| native | unique | 0.9236 | 1.0000 |
| native | dense | 0.6989 | 1.0000 |

## Reconstruction and complete institutional witness

The unchanged U12 witness reproduces all 31 checks and every retained checkpoint and transaction digest, including succession, newcomer teaching, public correction, dissolution and unfinished duty. It runs the delivered native implementation; no old result is substituted for the fresh witness.

Its 1,010 transactions occupy 4 independently checksummed segments. The archive including manifest is 740,749 bytes versus 18,682,169 bytes for the same canonical transaction history. Writing took 1.860 seconds. A single historical lookup read exactly 1 segment in 0.735526 seconds. Complete validated historical reconstruction took 6.863 seconds and reproduced the exact world checkpoint. These archive timings were collected during functional validation and are descriptive, not isolated comparative performance claims. The archive is not compared with a full live-engine checkpoint as if their contents were interchangeable.

## Validation and preserved failures

| Panel | Distinct tests | Result |
| --- | --- | --- |
| U2–U12 native regressions | 428 | Pass |
| New U13 preservation tests | 17 | Pass |
| Full legacy runtime with U13 adapter | 840 | Pass |
| Unchanged external fidelity suites | 72 | Pass |
| Total | 1357 | No failures, errors or skips |

The new controls include independent query-state transitions, commit/nesting/exception cleanup, strict types, forced hash collisions, separate actors/worlds, 4,097 historical revisions against an independent full store, atomic missing-reference rejection, hidden-state view isolation, archive corruption and reordering. Existing regressions retain partial work, rights, Model A accounting and all native capabilities.

Two inherited U3 failures first exposed an incorrect bool/int equality shortcut. It was corrected with exact recursive type comparison; the failing log remains. A supplemental collector initially failed to encode a view string before hashing; its error is retained. The first complete six-case legacy comparison then failed the active target at ratio **0.913676** against **0.85**, despite exact behavior. That candidate, every sample and raw checkpoint, its source identity and the explicit failed gate remain under `development/measurement_attempt2`. The final command-scoped cache addresses the measured redundant queries without changing the contract.

## Deliverables and reproduction

The source package includes the runtime, unchanged baseline, exact U12 reference, tests, frozen contracts, versioned architecture, source authority, progress ledger and this report. The evidence package includes all final results, source manifests, commands, raw compressed checkpoints, full institutional witness, archives, profiles and failed development runs. Earlier reports are retained as historical records, not refreshed claims.

From the source root on Python 3.12/Linux, use fresh output directories:

```sh
python tools/evaluate_u13.py --stage native --out /tmp/hle-u13/native
python tools/evaluate_u13.py --stage legacy --out /tmp/hle-u13/legacy
python tools/evaluate_u13_fidelity.py --out /tmp/hle-u13/fidelity
python tools/measure_u13.py --out /tmp/hle-u13/measurements
python tools/u13_witness.py --out /tmp/hle-u13/witness
python tools/verify_baseline.py --out /tmp/hle-u13/baseline.json
```

Do not run other task-owned computation during the measurement command. The README documents explicit legacy activation and the existing workshop inspector. The standard library is sufficient.

## Remaining scope

**U14 is the sole remaining unified-engine milestone:** freeze the release source and run sustained held-out combinations and all required release gates, then deliver the inspectable engine with precise limits. No U14 held-out cases or reserved release seeds were used in U13 tuning. The separate old R21C release contract is also unexecuted and open. These finite workloads establish no unrestricted scaling, natural-language fluency, unlimited institutional or developmental complexity, or broader empirical psychological validity.
