# HLE unified engine — U4 complete

21 September 2026 · Common operation lifecycle and material interactions

**Progress: 4/14 milestones complete. Ten remain. Next: U5 — integrated Fool's Memory, Model A, and Crux.**

U4 supplies native paid, resumable execution over the common object structure. All four frozen U4 acceptance cases are established. The final run passes **45 U4 tests, 32 U3 tests, 31 U2 tests and 71 distinct inherited regressions: 179 tests, with no failures, errors or skips.** The U2, U3 and U4 raw witnesses also pass all 12, 15 and 22 checks respectively; those checks are not added to the test denominator.

## What changed

One lifecycle now handles native material work, observation reading, interpretation binding and acquired-use retention. Each operation retains its actor, participants, accessible evidence, exact input revisions, physical dependencies, registered transformation, affected obligation, paid route stages, required/completed/spent work, result and causal history.

Work can stop and resume across a checkpoint. Finishing its work budget produces a ready job; the physical effect still requires a separate commitment. That commitment checks live dependencies, custody, ownership, condition and resource availability. Failed continuation preserves spent energy and time. A later failed job or changed interpretation cannot undo an earlier completed effect.

The native workshop implements **transfer, inspection, use, care and return**, plus declared damage, repair and consumption affordances. Repair restores a damaged target, wears its repair tool and consumes compatible stock in one atomic transaction. Return changes custody and fulfills its exact addressable obligation together. Whole-instance reservations and serialized commitments prevent competing jobs from double spending a tool or stock container.

Material stock has an explicit irreversible consumption counter: available plus consumed equals its lifetime quantity. This finite world contract has no regeneration or replenishment. Native prices and physical rules are declared engineering choices; legacy episodes retain their original prices and contracts.

Physical execution, delivery, reading, interpretation and retention can happen at separate times. Native processing receipts are produced by actual paid work. An observation pins the historical event it describes. Receiving or reading a procedure does not confer acquired use; named execution requires a supported registered executor and the actor's own acquired-use evidence. An unsupported action cannot become physical merely by receiving a procedure name.

## Acceptance results

| Case | Result | Demonstrated behavior |
| --- | --- | --- |
| U4-01 — Partial commitment | Established | Repair pauses after two of six paid units, restores exactly, resumes and commits once. No early repair or consumption occurs. |
| U4-02 — Stale basis | Established | Changed dependencies invalidate unfinished effects while preserving charges and prior completed effects. Controls isolate stale targets, tools, stock, definitions, procedures, relation terms and interpretation drafts. |
| U4-03 — Resource conflict | Established | Both contender orders and real concurrent threads prevent duplicate reservation, charging or consumption. Waiting attempts are retained; cancellation releases reservations without refunds. |
| U4-04 — Delayed delivery | Established | Two actors receive the same actual event at different times. Reading, binding and retained use each require their own paid work; another actor's acquisition grants nothing automatically. |

Additional controls cover zero energy, limited time despite spare energy, wrong custody, incompatible/exhausted stock, irreversible wear, exact return-obligation revision, malformed requests, command retries, terminal jobs, unsupported procedures, private-event access, hidden-state isolation, historical actor views, forged checkpoints and independent audit rejection of forged charges or material outputs.

## Raw workshop witness

The retained witness has **85 native transactions, 26 operation attempts and 62 energy/time units charged**. It includes one successful repair, one competing attempt that becomes stale and retains six paid units, delayed reading, an explicitly authored interpretation and retained procedure use. Its single repair quantum is consumed exactly once; the separate care stock remains untouched.

The independent audit reloads the exported transaction stream, reconstructs charges, reservations, physical effects and stock balances, and checks their causal lineage. It does not use the executor's material-transform function, job/wallet/reservation indexes or assessment flags. Its scope is U4 bookkeeping and the declared material rules; it does not replace the wider U14 release evaluation.

The final evidence includes the interrupted material checkpoint, interrupted read checkpoint, completed engine checkpoint, separately restorable native/access checkpoints, raw transactions and before/after actor views. Exact engine continuation, native replay, access replay and historical participant views all reconstruct.

## Fresh validation and source preservation

| Final gate | Result |
| --- | --- |
| U4 tests | 45/45 pass. |
| U3 tests | 32/32 pass. |
| U2 tests | 31/31 pass, including the inherited comparison of 216 three-action legacy sequences. |
| Selected inherited regressions | 71/71 distinct tests pass. |
| U2 / U3 / U4 witnesses | 12/12, 15/15 and 22/22 checks pass. |
| Frozen R21B baseline | All 3,044 members and 98 runtime modules unchanged before and after the run. |
| U3 source preservation | 3,105 of 3,109 supplied members unchanged; three modules extended and the root README updated. The prior README is preserved as `docs/U3_README.md`. No source member is missing. |
| Final execution identity | All frozen execution source and protocol hashes unchanged during the run. |

The three inherited module changes are explicit extension points: `records.py` adds paid-material lineage; `store.py` allows a specialized validator while the base store still rejects unsupported effects; and `particulars.py` supports a selected backend/receipt authority. Existing U2/U3 tests and witnesses retain their original meanings. The preserved U3 witness still tests its imported-receipt adapter; the new U4 witness tests native paid receipts.

Python 3.12.14 executed the final run. Test-body times were approximately 7.4 seconds for U4, 0.6 seconds for U3, 12.5 seconds for U2 and 156.4 seconds for the inherited panel. These timings describe this execution and are not performance acceptance results.

The canonical final execution-source manifest SHA-256 is:

`199146c562360e08ebc43b1aaffc306f99c52e5a6c8e1e9b0e10509cf212ec50`

The full file mapping is `final/execution_source.json`. The evidence package records the final source archive's byte count and SHA-256.

## Boundaries and remaining work

The native operation route currently has explicit prepare/execution stages. Integrated Model A routing, Fool's Memory contextual realization and Crux transformations remain **U5**. Interpretation drafts in this milestone are explicitly supplied; tests establish paid retention and causal linkage, not autonomous production of realistic personality or developmental change. Acquired use records the declared supported practice/context pair; generalized retained competence remains U8.

The legacy runtime remains its authoritative writer and is not silently converted into native jobs. The common native executor supplies the new workshop operation families while the protected legacy paths continue to pass. General procedure composition remains U9.

Reservations cover whole material instances, including stock containers. Dependency validation happens at effect commitment, so a stale attempt can spend its remaining work before failing. Automatic replanning, waiting policy and resource recovery are not supplied by U4. The service is a trusted simulator boundary; policies receive detached participant views.

The complete operation checkpoint retains redundant command and state evidence for exact replay. No storage, memory, throughput or bounded-history improvement is claimed here. **U13 efficiency and U14 release acceptance remain open.** The full 912-test U1 run and earlier development/performance panels remain historical evidence. No unified held-out or R21C release seeds were used.

## Reproduction and retained development history

Extract `HLE_Unified_U4_Source_v1.zip`, enter `HLE_Unified_U4_v1`, and run:

    python tools/reproduce_u4.py --out /tmp/hle-u4-reproduction

Use a fresh output directory. Python 3.12 and the standard library are sufficient. The U1/U2/U3 reproduction tools and complete frozen baseline remain included.

Inspect native accounting with:

    python tools/inspect_u4.py /tmp/hle-u4-reproduction/u4_witnesses/workshop.completed.checkpoint.json

Append `--actor alice` to inspect Alice's detached participant view.

Development runs remain separate from final results. The first run passed four core tests. The expanded second run had five test errors caused by one missing `available` helper import; its full log, source snapshot and result manifest are retained. The import was corrected, then all 45 tests passed. The development raw witness passed all 22 checks. The final frozen run re-executed all declared gates with no failures, errors or skips.

**Next: U5 — integrated Fool's Memory, Model A, and Crux.** Connect these paid native effects and observations to one traceable conceptual-processing circuit that changes a later participant action.
