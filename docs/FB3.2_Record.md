# FB3.2 — Workflow active interruption: complete after authorized recovery

[machine-checked] Current disposition: complete on attempt3 after explicit author release. The chronology below preserves both failed attempts. Neither attempt passed the new-test gate. Batch 3.1 remains the latest accepted checkpoint; earlier statements below are chronological development history.

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

[source_defined] Author release: “I approve the batch 3.2 fix and resumption”. This authorizes the scoped new-auditor repair and continued Release 1.0 work. The separate prospective recovery protocol `C7_Workflow_Shell_FB3.2_Recovery_v1.json` is hashed as `b373046185e52a421b61a097791722a787381954dd95f75b871d67ce47d28972` before source changes. Previous failures remain failed; no inherited contract or accepted source is changed. All other stop gates remain.

[derived] Authorized repair reconstructs the cancellation Account from the raw prior operation and its ordered, deduplicated input lineage. It validates the full Account, participant scope and event reference; negative controls omit, add, reverse or replace provenance. Only the new auditor and its test changed. All accepted FB3.1 frozen files are byte-identical.

[open] Attempt3 freeze `8bc14dc3420735d9784bc3f692c9f41a7d5737221367ac5ec30988bc07817f35` covers 1262 files. Nine new methods and 667 existing methods, the 32-cell panel and independent 192-world continuation reconstruction are pending.

[machine-checked] Continuation was re-enabled after the explicit author release.

[machine-checked] Attempt3 new-test gate passed: nine distinct methods, zero failures/errors, unchanged source. Native cancellation Account provenance and four forged-source controls are verified. Remaining regression and panel gates are still running; batch not yet accepted.

[machine-checked] Accepted attempt3: 676 distinct passing methods (667 existing + nine interruption), zero skipped/failures/errors. All 32 interruption/control pairs passed, all 32 invalid continuations were rejected, and the independent verifier reconstructed 96 panel worlds plus 96 continuation worlds with 32 exact original/restored paid progressions. Five command groups exited zero on freeze `8bc14dc3420735d9784bc3f692c9f41a7d5737221367ac5ec30988bc07817f35`; all 1,250 accepted FB3.1 frozen files stayed unchanged.

[machine-checked] The 296-member accepted archive has SHA-256 `78a25d3d9357493152bc72e4be1c06b8d808b18fd50b2069e8e27f3ca4c855f6`. Exact identity and clean extraction instructions: `evidence/FB3.2/attempt3/Raw_Evidence_Index.json`. The earlier blocked archive and both failed attempts remain immutable. The correction changes only the new auditor and its test; inherited cancellation meaning and execution are unchanged.

[derived] What becomes possible: every declared workflow cell can now be stopped after its first paid semantic intermediate, keeping expenditure and one-attempt allowances while refusing destination completion; the same checkpoint resumes subsequent paid work exactly. Batch 3.3 is next, for effect/sign coverage, scoped correction, recurrence and refused clearance. Release 1.0 remains incomplete; Phase 7 is unauthorized.
