# Socionics Research Lab — continuous build instructions

The user authorized completing the supplied Final Build Plan through Release 1.0 without per-batch prompts on 2026-10-06.

Read project_sources/HLE_Final_Build_Plan_v1_0.txt, its companion theory and closure ledger, then docs/FB_Job_Register.md and docs/FB_Run_State.json. Original DOCX files are authoritative if the text transcription is ambiguous. The existing README and Build Specification v10 describe the delivered baseline.

Proceed through batches 0.1–6.3 in order. A batch handoff is a saved checkpoint, not a request for permission. Continue to the next eligible batch once its gate passes. Do not start Phase 7 without the author's explicit R5 ruling.

Preserve every standing rule in the plan: baseline/ is sealed; Python standard library and exact integer structures; protocols hashed before implementation; freezes before evaluation; failed and source-changed attempts retained; independent auditors; matched controls; bounded claims; no changes to inherited meanings. Stop and report for the plan's explicit blocker conditions. Batch 0.1 mismatches are findings, not invitations to repair the supplied baseline. No theoretical register item is closed by the assistant.

Save each completed batch with its record, changed source, tests, raw evidence hashes and updated register/state in a Git commit. Never mark a batch complete from a summary alone. Never force-push. Preserve unrelated user changes.

Continuation must read current GitHub state, not rely on chat history or ephemeral paths. Use a unique run ID and an atomic expected-head update of docs/FB_Run_State.json to claim a lease before working. A fresh active lease belongs to its current worker: exit without overlapping. Refresh a 30-minute lease while active. After expiry, inspect committed evidence and recover from the last verified checkpoint. A terminal state of blocked, held or complete means stop; notify the user and disable the continuation automation. A held release is not a completed release.

Use main for the authorized build in this newly initialized repository, with a commit per batch/checkpoint. Preserve failures even when a process crashes. Notify the user of meaningful completion or blockers; do not ask for “next batch.”

The original evidence archive remains an immutable Library attachment; its ID and digest are recorded in docs/FB_Input_Inventory.json. It must be materialized when needed rather than silently omitted or represented as new evidence.
