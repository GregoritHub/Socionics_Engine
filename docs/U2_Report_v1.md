# HLE unified engine — U2 complete

21 September 2026 · Common versioned object structure

**Progress: 2/14 milestones complete. Twelve remain. Next: U3 — compact particulars and situated access.**

U2 implements the shared object and revision layer in a separate `hle_unified` namespace. All eight required acceptance cases are established. The final run passes **31 U2 tests and 71 distinct applicable legacy regressions: 102 tests, with no failures, errors, or skips.** The original R21B runtime remains unchanged.

## What changed

Material objects, concepts, procedures, observations, claims, commitments, and collective organizations can now use compatible identities and immutable revision rules. An instance's namespace and key remain distinct from its label, values, definition, and current revision. Definitions can be shared without merging instances or changing the meaning of historical references.

Relations can have their own addresses, participants, direction, context, time scope, terms, evidence, and revision histories. Definition changes, membership changes, transfers, division, combination, and replacement have explicit lineage. Optional memory, agency, material, and governance state allows ordinary tools to exist without a cognitive runtime.

Occurrence categories distinguish actual events, observations, remembered claims, hypothetical continuations, and interpretations. Personal endorsement/confidence and evaluator judgments are separate objects. A false prediction remains a hypothesis even when its holder fully endorses it. Revising an account cannot turn it into an actual event or rewrite prior actual history.

The native journal validates an entire transaction before publishing it. Stale revisions, conflicting writers, missing references, inconsistent lineage, and unsupported material changes reject atomically. The supported structural material law conserves owned quantities through split, merge, and replacement; consumed identities retire in the same transaction. A concurrent attempt cannot consume the same revision twice.

## Required acceptance cases

| Case | Result | Demonstrated behavior |
| --- | --- | --- |
| U2-01 — Separate instances | Established | Equal-looking bowls share a definition while preserving independent identities, custody and histories. |
| U2-02 — Nonmental material | Established | A material tool can transfer ownership/custody without memory, agency or governance state. |
| U2-03 — Relation identity | Established | Revising an obligation retains its participants, context, prior scope/terms, predecessor and causal evidence. |
| U2-04 — Hypothesis | Established | A false possible continuation is stored without creating a physical event; personal endorsement and failed assessment remain separate. |
| U2-05 — Historical revision | Established | A remembered account still resolves the old rule after the current definition changes. |
| U2-06 — Split/merge lineage | Established | Division, combination and replacement conserve owned material and retain consumed identities and exact provenance. |
| U2-07 — Finite cycle | Established | A delegate represents a group containing that delegate through finite references; membership revisions preserve the earlier arrangement. |
| U2-08 — Legacy adapter | Established | Legacy references, transactions and canonical checkpoints recover exactly, including partial paid work and continuation. |

These are deterministic structural cases. No artificial random seeds or held-out population claims are attached to them.

## Legacy migration and protected behavior

The bridge keeps the existing runtime as the authoritative writer and exposes detached common object views. Compatibility views cannot be written into the native store, so the same legacy state does not acquire competing writers. The bridge's participant input adapts only the existing permitted view; its offline inspector methods are separate interfaces.

The structural adapter preserves every inherited field, tuple, enum, scalar and exact reference in the frozen codec's 271 dataclass types and 14 enum types. This inventory establishes wire support; it is not a claim that every class has its own independently executed fixture. Explicit semantic roles are assigned only to the declared families; other records retain generic lossless views.

| Fresh validation | Result |
| --- | --- |
| U2 suite | 31/31 tests pass: the eight acceptance cases plus 23 additional controls/comparisons. |
| Selected inherited suite | 71/71 distinct tests pass, including all applicable U1 protection-index entries after deduplication. |
| Matched legacy action sequences | All 216 three-action sequences match through the adapter: 648 command steps per side, with observations, effects, costs, ownership and checkpoint recovery checked. This is one comparison test within the 31. |
| Partial legacy work | The unfinished unit survives U2 encoding and recovery; completion charges only the remaining unit under the declared R2 fixture supply. |
| Current v4 checkpoint | The existing IEE/12 zero-budget checkpoint round-trips exactly, preserves its three-event journal and absence of acquisition, and continues identically under a Tick. |
| Native replay | Exact checkpoint reconstruction, including finite cycles and historical definitions; malformed and rehashed inconsistent journals reject. |
| Source integrity | All 3,044 frozen baseline members preserved; all 98 runtime modules unchanged; U2 execution source unchanged during final validation. |

The 216 sequence comparison checks the legacy effects against the independently maintained history fold as well as the baseline execution. The negative controls include unauthorized transfers, conservation violations, mixed ownership/units, duplicate consumption, missing retirement, stale or skipped revisions, conflicting transaction keys, writer takeover, invalid occurrence promotion, malformed payloads, and hidden-data isolation.

Final execution used Python 3.12.14. The U2 suite took about 12.4 seconds and the selected inherited suite about 150.9 seconds in this environment. These durations are descriptive, not performance acceptance measurements.

## Inspectable evidence

The retained native witness contains 17 journal transactions, 31 object versions and two actual events. It includes equal-looking bowls, changed custody, an obligation revision, an old rule account, a false prediction, separate endorsement and assessment, conserved material transformations, and cyclic group references with a subsequent membership change. All twelve witness checks pass.

The evidence archive contains:

- The final per-test logs, results, frozen execution hashes, protocol hash and before/after baseline checks.
- A canonical native checkpoint and its complete transaction stream.
- Original and U2-encoded partial R2 and zero-budget v4 checkpoints, plus the completed R2 checkpoint.
- The completion summary, input-archive hashes, declared contracts, and reproduction source.
- Earlier development-run logs, retained separately from the final run. They are not added to the final test denominator. The first runner's `started_utc` was emitted at completion; the final run records separate correct start and completion timestamps.

## Scope and remaining work

U2 completes the common structure and the declared smallest legacy migration slice. Native material operations currently demonstrate simulator bookkeeping and conservation. Generalized participant views and paid, resumable native operations remain U3 and U4. Legacy participant work retains its existing prices, wallets, incomplete jobs, and failure behavior. The explicit supply used by the R2 partial-work fixture does not change R21B's whole-episode no-top-up contract.

Procedure and collective records are representational foundations. They do not by themselves confer executable physical powers, personal learning, consent, aggregate capacity or spontaneous institutions. Those behaviors retain their later milestone gates.

The transitional adapter prioritizes exact recovery and adds wire overhead: the retained R2 partial checkpoint grows from 22,916 to 59,583 raw bytes in the U2 representation; the small v4 checkpoint grows from 476,522 to 1,236,376 raw bytes. These are fixture sizes, not a matched performance evaluation. U13's frozen efficiency targets remain open. Storage interning, compact historical state and broader execution improvements are not claimed here.

The full 912-test U1 run, six candidate/witness pairs, two controls, performance workload, and large positive-budget v4 checkpoints remain historical U1 evidence. U2 does not rerun those complete panels or the reserved R21C release. No unified held-out seeds or legacy release seeds were used. The existing limits on broad developmental complexity and psychological validation remain unchanged.

## Reproduction and handoff

Extract `HLE_Unified_U2_Source_v1.zip`, enter `HLE_Unified_U2_v1`, and run:

    python tools/reproduce_u2.py --out /tmp/hle-u2-reproduction

Choose a new output directory. The command uses Python 3.12 and the standard library, records every stage's result, reproduces the tests and witnesses, and verifies source integrity. The complete frozen baseline and U1 reproduction tools remain included.

**Next: U3 — compact particulars and situated access.** Build the participant-view and indexed-particular interfaces on these exact references while preserving each actor's access, history, interpretation and acquired use. Keep hidden changes from altering a participant's pre-delivery information or decision, and retain the U2 structural and compatibility witnesses as regression gates.
