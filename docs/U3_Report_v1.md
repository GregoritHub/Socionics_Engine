# HLE unified engine — U3 complete

21 September 2026 · Compact particulars and situated access

**Progress: 3/14 milestones complete. Eleven remain. Next: U4 — common operation lifecycle and material interactions.**

U3 implements compact native history, indexed exact particulars, and explicit participant access. All three frozen U3 acceptance cases are established. The final run passes **32 U3 tests, 31 U2 tests, and 71 distinct applicable inherited regressions: 134 tests, with no failures, errors or skips.** All twelve U2 witness checks and fifteen U3 witness checks also pass; these checks are not added to the test denominator.

## What changed

Immutable definitions and repeated structures can now share physical storage while object identities, exact revisions, and each actor's access and acquired-use evidence remain separate. Native history stores field differences and a reference journal, with exact reconstruction of the original full-snapshot representation. Dependency indexes support internal cache invalidation.

A participant receives a detached view assembled from explicit, revision-specific rights, deliveries and completed processing evidence. Its indexes cover names, dates, ownership, event references, typed values and processing receipts. Exact detail lookup remains separate from contextual conceptual traversal. References do not automatically disclose their targets, and a new world revision does not replace an actor's retained historical account.

Conceptual bindings retain their actor, exact target, cue and context, interpretation, endorsement, confidence, detail evidence, links and processing receipt. Different actors can hold incompatible accounts of the same tool. Shared definitions and another actor's acquisition do not confer knowledge, confidence or use evidence.

## Acceptance results

| Case | Result | Demonstrated behavior |
| --- | --- | --- |
| U3-01 — Private difference | Established | Eight deterministic hidden-state variants leave pre-delivery views byte-identical and preserve the policy probe's choices and reasons. Completed processing of a permitted new observation can then change the decision. |
| U3-02 — Shared definition | Established | Two actors use one physically shared definition value while retaining separate interpretations, confidence, recall, receipts and acquired use. Reading a procedure alone grants no use evidence. |
| U3-03 — Detail and concept | Established | Direct indexed ownership retrieval and a separate contextual binding walk cite the same exact tool and source revisions. A detail query invokes no conceptual traversal. |

Additional controls establish exact historical reconstruction across 24 revisions; distinction between boolean and integer values; separate identities for equal-looking objects; finite cyclic binding traversal; contextual restrictions; exact partial-read continuation; revocation without erasing memory; rejection of private/evaluator access; and rejection of mismatched, replayed or incomplete processing evidence.

An actor's earlier view reconstructs from its own history position, independent of other actors' event counts. Hidden changes invalidate a real cached view in the test and still produce the same participant-visible bytes. No invalidation reason, global counter or freshness signal enters that view.

## Processing and behavioral scope

U3 supplies a checked **processing-evidence adapter**, not U4's native paid executor. The U3 fixtures explicitly import actor-owned receipts with required, completed and spent units. The adapter enforces owner, work key, exact input dependencies, completion and monotonic progress; incomplete reads retain pending content across restoration.

The new contextual acquisition query reports retained evidence for a procedure/context pair. It does not execute the procedure, establish present physical feasibility, or supply missing physical affordances. The U3 binding walk is an access primitive; integrated paid Fool's Memory–Model A–Crux realization remains U5. Existing legacy paid work, resource prices and partial-job behavior remain unchanged and are exercised by the inherited gates.

The policy comparison is a declared deterministic request-selection probe receiving only `ParticipantView`. The workshop histories and interpretations are explicit inputs. These results establish information separation under that interface; they do not establish autonomous personality development, generated Shells, natural-language understanding or psychological validity.

## Fresh validation and preserved source

| Final gate | Result |
| --- | --- |
| U3 tests | 32/32 pass. |
| U2 tests | 31/31 pass, including the existing comparison of all 216 three-action legacy sequences. |
| Selected inherited regressions | 71/71 distinct tests pass. |
| U2 raw witnesses | 12/12 checks pass, including native replay, partial legacy paid continuation and the zero-budget v4 checkpoint. |
| U3 raw witnesses | 15/15 checks pass, including hidden-view equality, separate acquisition, exact historical views, partial processing, full-snapshot agreement and compact reconstruction of the complete U2 native witness. |
| Frozen baseline | All 3,044 members and all 98 runtime modules unchanged. |
| U2 source preservation | All 3,089 supplied source members preserved; the original root README is retained as `docs/U2_README.md`. No U2 runtime, test, tool or contract file changed. |
| Final execution identity | All frozen runtime/test/tool/protocol hashes unchanged during the final run. |

Python 3.12.14 executed the final run. U3 tests took about 0.7 seconds, U2 tests 12.7 seconds, and the selected inherited tests 139.3 seconds in this environment. These durations describe this run; they are not performance acceptance results.

The canonical execution-source manifest digest is:

`1abf46b04785b872eda4a7048e62dacd2b7eda0f1987caeec1c7ad002a8fd168`

The complete mapping is retained in `final/execution_source.json`. The evidence archive also records the final source archive's byte count and SHA-256.

## Storage measurements and limits

The retained workshop's **native portion** contains 28 object versions. Both representations below reconstruct the same native records and journal; the separate access ledger is not included in this size comparison.

| Encoding | Full-snapshot reference | U3 compact |
| --- | ---: | ---: |
| Raw bytes | 41,846 | 23,087 |
| gzip bytes | 2,317 | 2,974 |
| Stored version state fields | 224 | 204 |

Raw native checkpoint size is about 44.8% smaller, while gzip size is about 28.4% larger. The U3 runtime also establishes physical sharing of repeated immutable structures. **U13 efficiency acceptance remains open.** This fixture does not establish lower total live memory, faster execution, faster restore, bounded archival growth, or an advantage over the compressed R21B baseline. Predecessor-chain reconstruction and broader segmentation remain further work.

The access service is serial. It is a trusted simulator boundary, not a hostile-code sandbox. Native concurrent operations, resource reservation, paid routes and active-operation dependency checks remain U4 work.

## Evidence and reproducibility

The evidence archive contains the frozen protocol, progress ledger, exact source identities, final per-test results and commands, baseline/source-preservation checks, actor snapshots and decisions, native transaction streams, complete and partial situated checkpoints, original U2 witnesses and their compact re-encoding, and the versioned architecture specification.

Development runs remain separate from the final denominator. One initial witness-export attempt failed because its script omitted a `codec` import. Its failure record, failed script and partial outputs are retained under `development/witness_attempt_1`. The import was corrected; later development and final witnesses passed. No failed behavioral result was excluded from the final run.

Extract `HLE_Unified_U3_Source_v1.zip`, enter `HLE_Unified_U3_v1`, and run:

    python tools/reproduce_u3.py --out /tmp/hle-u3-reproduction

Use a new output directory. Python 3.12 and the standard library are sufficient. The U1/U2 reproduction tools and complete frozen baseline remain included.

Inspect the completed actor view with:

    python tools/inspect_u3.py /tmp/hle-u3-reproduction/u3_witnesses/situated.completed.checkpoint.json --actor alice

The full 912-test U1 run, its candidate/witness panel and prior performance measurements remain historical evidence. No unified held-out seeds or R21C release seeds were used. Their acceptance gates remain distinct.

**Next: U4 — common operation lifecycle and material interactions.** Connect the exact references, permitted inputs and receipt boundary to actual paid, resumable native operations; enforce dependencies and resource constraints before effects; preserve spent work and already-performed consequences.
