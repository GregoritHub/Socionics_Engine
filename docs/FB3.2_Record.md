# FB3.2 — Workflow active interruption: blocked after second failed gate

[open] Current disposition: blocked. Neither attempt passed the new-test gate. Batch 3.1 remains the latest accepted checkpoint; earlier statements below are chronological development history.

[source_defined] Batch 3.2 follows the unchanged Phase 3 protocol and CT §10. The separate prospective clarification `C7_Workflow_Shell_FB3.2_Amendment_v1.json` specifies the matched paid prefix, the zero-cost cancellation intervention, 32 exact checkpoint pairs, effect assignment and one-attempt preservation. SHA-256: `9bcd49e3e71ed8709c1b92cb0f16be793d539775f6b968fc7903be9ceaa332ba`.

[open] Implementation and all gates remain pending. Accepted batch 3.1 and its admission-only schema remain unchanged; Phase 7 requires explicit R5.

[derived] Added three new interruption modules with a separate schema and namespace. They start the ordinary workflow, stop exactly after its first semantic step, preserve cancellation spending and the retained intermediate, and keep the substituted personal intention separate from the requested destination. The accepted admission-only layer and all previously frozen files remain byte-identical.

[open] Attempt1 freeze `2d3bce8dd37a219cb97d6f970ddbad94db5ff6a0397f53e4a539907efb00f2ad` covers 1260 files. New tests, exhaustive 32-cell panel, exact restoration pairs, independent reconstruction and existing regression are next.

[probe] Attempt1 failed the new-test gate (nine methods, one assertion failure and ten error entries). The new auditor and one test incorrectly treated the inherited cancellation receipt as a completed workflow result: `OperationEngine._cancel` legitimately stores an actual event with outcome `cancelled` in `job.result`. The runtime preserved the expected intermediate and spending. Logs, frozen files and a separately labelled unchanged-source three-world reproduction are retained under `evidence/FB3.2/attempt1/`. The correction will validate the cancellation receipt and keep completion/material-output prohibitions, without changing native runtime or inherited semantics.

[derived] The first correction left native execution unchanged and required a real cancellation event with the original actor, context and primitive, no retained/public output, and no material result. It also incorrectly assumed the event Account contained only the immediately prior job as source.

[probe] Attempt2 failed: nine methods, zero assertion failures and 12 error entries, all `workflow cancellation receipt claims completion or changed material`. The inherited `_event` source list contains the prior job plus the job's indexed inputs, with a changed target only when applicable. The new audit's exact-one-source assumption therefore rejects legitimate cancellation provenance. Source freeze SHA-256 `affba60fe237c45422c396cd1d82e9027e769c4d0b52036510c23cb29d311ff4`; all 1,260 frozen files stayed unchanged. There was no third attempt and no repair after this failure.

[source_defined] Exact stop instruction, Final Build Plan §1: “Stop and report to the author, without working around it, when: a gate fails twice after a correction”. This stop applies to the new interruption test gate. The earlier authorization released FB2.4 and retained all other stop rules. The defect is in the new audit/test assumptions; this is not evidence against Model G or a contradiction of the companion theory.

[open] Proposed recovery, only after author release: reconstruct cancellation provenance from the prior operation and its exact input lineage, retaining checks against false destination completion, material effects, altered spending and lost intermediates. Do not change the inherited event contract. Re-freeze and run the nine new tests, all 667 existing methods, the 32-cell active panel and its independent verifier, including every exact continuation pair. None of those full-panel/regression gates was run on this failed attempt.

[machine-checked] Both failures, exact commands, test logs, source snapshots/freezes and a separately labelled unchanged-runtime reproduction are durably preserved in the 28-member archive, SHA-256 `59dda409593ee5459e0408923f787cc78dc91db4044bb45d24fa6dc853a5446b`. Exact IDs and restore instructions are in `evidence/FB3.2/Evidence_Index.json`. Original baseline files and all accepted FB3.1 source files remain unchanged.

[machine-checked] The continuation task was successfully disabled at 2026-10-07T12:51:55.713905Z under the required stop. The run state is blocked and the lease released. Release 1.0 remains incomplete; Phase 7 remains unauthorized.
