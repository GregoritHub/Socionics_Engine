# HLE unified engine — U1 complete

21 September 2026 · Baseline and migration contract

**Progress: 1/14 milestones complete. Thirteen remain. Next: U2 — common versioned object substrate.**

U1 establishes a reproducible starting point and a concrete migration contract. The supplied R21B runtime is unchanged. All 912 inherited tests pass; six candidate/witness pairs and two controls reproduce their retained raw transaction histories; the declared baseline measurements are complete.

## Results

| Gate | Fresh U1 result |
| --- | --- |
| Inherited validation | 912/912 distinct tests pass: 893 through R21A plus 19 R21B tests. |
| Paired developmental cases | Six candidates and six independently constructed witnesses executed from genesis. |
| Positive budgets | All four candidates and all four witnesses complete 13 challenges and 100 later paid opportunities with two changes; no unfinished work. |
| Zero budgets | Two candidates and two witnesses defer; their three-event journals contain no acquisition records. |
| Historical equivalence | All 14 fresh raw transaction-stream digests match the stored same-case digests, including both controls. |
| Performance workload | All six active/inactive-history configurations complete, restore exactly, and pass independent accounting and the inherited benchmark gates. |
| Current v4 checkpoints | IEE/12 and SLI/11 reconstruct byte-exactly, pass paid-work audit, and continue identically under the declared Tick. |
| Frozen source | All 3,044 baseline members preserved; all 98 runtime modules unchanged. |
| Original evidence | 724 members in the two supplied evidence archives checked; all 140 expected external trace members match. |
| Attached source documents | All nine attached foundation/source files match their packaged counterparts. |

The paired panel is deliberately bounded: IEE/12 and SLI/11, each under adequate, constrained-feasible, and zero-budget regimes. Its twelve executions are separate from the two controls. Rechecks, raw audits, and unit-test fixtures are not counted as additional experimental cases. The eight positive executions contain 800 later paid opportunities in total.

## Resource controls

All three controls below use IEE/12 with the same 150,000-unit whole-episode allocation per actor for each of energy and time. Worker spending is the same numerical amount in each resource ledger.

| Work policy | Worker units spent | Later opportunities completed | Outcome |
| --- | ---: | ---: | --- |
| Paid predicate reuse | 70,498 | 100 | Full episode |
| No predicate reuse | 87,026 | 100 | Full episode |
| Legacy blanket extents | 150,000 | 50 | Budget exhausted; partial work retained |

Paid reuse saves 16,528 worker units relative to the no-reuse control under the same newer phase extents. The legacy policy still exhausts the allocation after 50 later opportunities. No wallet is reset, credited, pooled, or refunded to obtain these results. These are modeled work measurements, not wall-clock speed claims.

## Baseline performance

The inherited benchmark runs the R20 continuing performance world on the current R21B runtime, with a separately declared performance allocation. It schedules 32 circuit choices per batch, with two warmups and nine measured repetitions at each size. All 32 choices are published and their orders completed between batches. Existing unread autonomous observations remain recorded; this is not a claim that the entire autonomous scheduler backlog has been processed.

| Inactive history | Kind | Median total time for 32 choices (ms) | Record visits | Raw checkpoint (MB) | Gzip checkpoint (MB) | Restore (s) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 100 | tick | 62.25 | 87,744 | 74.96 | 2.66 | 16.70 |
| 1,000 | tick | 60.99 | 87,744 | 75.64 | 2.67 | 18.60 |
| 10,000 | tick | 65.99 | 87,744 | 82.46 | 2.76 | 27.17 |
| 100 | completed inspection | 62.20 | 87,744 | 75.76 | 2.67 | 19.42 |
| 1,000 | completed inspection | 68.23 | 87,744 | 83.67 | 2.77 | 20.70 |
| 10,000 | completed inspection | 64.45 | 87,744 | 162.76 | 3.76 | 50.77 |

From 100 to 10,000 inactive entries, median active-batch time changes by 1.060× for tick history and 1.036× for completed-inspection history. Affected record visits remain exactly constant. These are results for the declared workload; the broader shared/population release remains outside U1.

The current v4 checkpoints were measured separately. Timed restoration excludes memory-profiler overhead. Each memory measurement runs in its own child process after equivalent warm imports.

| Current checkpoint | Raw (MB) | Gzip (MB) | Restore (s) | Retained traced allocation (MB) | Peak traced restore allocation (MB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| IEE / seed 12 | 90.91 | 3.08 | 24.20 | 39.78 | 776.08 |
| SLI / seed 11 | 110.70 | 3.78 | 39.06 | 44.95 | 947.69 |

MB means 1,000,000 bytes. Traced allocation counts Python allocations made during restoration and still retained afterward, or their peak during that pass. The checkpoint text is allocated before tracing. This differs from whole-process RSS, which is also retained in the evidence as a high-water mark. The measurements expose a substantial temporary reconstruction cost; they do not show that every live engine instance consumes the reported restoration peak.

The additional v4 continuation check uses one identical explicit Tick on both reconstructed worlds and verifies unchanged wallets. Meaningful paid partial-job continuation, invalidation, and byte-exact reload are covered by the inherited test suite. No new full development episode is claimed for the Tick check.

## Migration contract delivered

- All 98 modules classified: 6 preserve, 24 adapt, 14 assessor adapters, 35 generalize, and 19 compatibility witnesses. The inventory records 338 classes and locally declared fields; inherited fields remain part of the source hierarchy and must be resolved by adapters.
- Sixteen protected properties cover identity, history, observation isolation, exact particulars, conceptual tension, structural routing, paid work, partial completion, dependent invalidation, Shell evidence, retained capacity, collective obligations, and honest assessment.
- Thirty-three selected inherited regression references connect those properties to existing tests within their current scopes. They are part of the 912, not additional tests.
- Forty-five prospective conformance cases define the transition through U14. They are explicitly unimplemented and unassessed; eight define the U2 handoff.
- Development seeds 3101–3105 and unified evaluation seeds 50001–50010 are separated. The new evaluation also requires withheld object/relation and composition combinations. Legacy R21C seeds 2001–2010 were not executed.
- Source and claim statuses remain explicit. The numerical 4D geometry, a general arbitrary-domain Shell detector, and broad aggregation/closure guarantees remain open research.

## Efficiency targets frozen for the migration

These are prospective engineering targets selected after the baseline measurements and before U2 implementation or optimization. They are not observed improvements or theoretical laws.

- At least 15% lower geometric-mean participant execution time across matched legacy workloads.
- At least 15% lower geometric-mean retained Python allocation across the two matched v4 checkpoints.
- No individual active-time or live-allocation case may regress by more than 10%; compressed checkpoint bytes may grow by at most 10%; restore time by at most 25%; traced restoration peak may not increase.
- Preserve the declared active/inactive-history bounds and every protected semantic, access, replay, and resource-accounting property.
- Re-run both sides on the same environment and workload. New features require a same-feature reference comparison and prospectively frozen additional workloads.

Failure to meet a required efficiency target leaves U13 open. A later amendment must retain the original result and use a new version and appropriately independent evaluation.

## Scope and source identity

The original 60-candidate/60-witness R21B development panel remains historical evidence; U1 freshly reproduces the six specified pairs and two controls. U1 does not rerun the 480-case R21C release panel and does not renew its shared/population acceptance. No broader realism, universal developmental complexity, or human psychological validation is claimed.

The source is the supplied HolonicLivingEngine_Rebuild_R21B_v1(2).zip. Its release-manifest runtime digest is:

    671c400c5e31b401c0b52b66a433ab3ff894fc936211bc479f4647ea954f25f0

The U1 protocol additionally hashes a compact sorted mapping of module paths to hashes. That digest uses a different encoding from the legacy aggregate; all individual module hashes and both aggregate constructions are checked.

Environment: Python 3.12.14 on Linux x86-64; AMD EPYC 9V74; nine logical CPUs visible. Validation took about 20.1 minutes. Timing observations are descriptive and require matched remeasurement for future acceptance.

## Reproduction and handoff

Extract HLE_Unified_U1_Source_v1.zip and run from its HLE_Unified_U1_v1 directory:

    python tools/verify_baseline.py
    python tools/reproduce_u1.py --out /tmp/hle-u1-reproduction

The output directory must be new. The reproduction creates an isolated execution copy and fresh evidence. Original source files remain frozen. Full commands, logs, case metadata, transaction streams, protocol hashes, and measurements are in HLE_Unified_U1_Evidence_v1.zip.

**U2 is ready to begin:** implement common identities and versions, optional object roles, addressable relations, occurrence status, finite composition references, and exact legacy adapters. Complete the eight specified U2 cases and applicable inherited checks before extending the object system.
