# Continuous build

The user authorized the existing public GitHub repository and automatic batch continuation on 2026-10-06. Repository: https://github.com/GregoritHub/Socionics_Engine .

The hosted automation **Continue Socionics build** checks hourly and executes eligible work. It reads AGENTS.md and the current repository state, claims a lease, implements and verifies batches, and saves the next checkpoint. It stops and disables itself on a blocker, a held final decision, or completion of the revised goal (accepted 5.3–5.6 and original 6.1–6.3). Phase 7 is not authorized.

This is a scheduled hosted continuation, not a separately provisioned Codex Cloud environment. No custom Codex Cloud environment has been created. A scheduled run must verify that its execution tools are available; missing tools are a reportable blocker, never an excuse to claim work was performed.

## Retrieval and recovery

Clone the repository or fetch its current main branch. Never assume the scratch filesystem from an earlier run survived. Read docs/FB_Run_State.json and the latest batch record. Original source bytes remain in the Git history and supplied manifest. Original large evidence is identified in docs/FB_Input_Inventory.json; new raw intake evidence is identified in docs/FB0.1_Evidence_Index.json. Read the Library skill and materialize those exact stored files when needed. Verify their SHA-256 values before extracting. No user download/upload cycle is required.

## Saving

Shell reads/clones are available in the bootstrap environment, but shell push had no credential. The GitHub plugin provides authorized writes. Use create_blob/create_tree/create_commit/update_ref with an expected branch head. GitHub tree assembly worked in groups of 150 path/SHA entries after a full 1,731-entry tree call timed out. Binary blobs are uploaded with base64. Do not request a personal token or weaken access rules.

For new very large raw evidence, save one immutable archive through Library and commit its exact identity, SHA-256, extraction instructions, and summary to GitHub. Code and repository documents stay in Git. Do not lose or duplicate evidence merely to make a commit smaller.

## Run ownership

A fresh active lease prevents another worker from editing. Claim and renew the lease using an expected-head ref update. Inspect current head on conflict. Preserve user changes. Release the lease into ready state at a verified resumable checkpoint. Do not steal a live lease. Expired leases require inspection of actual committed evidence before recovery. Never infer a pass from an absent process or a missing log.

## Approved extension (2026-10-07)

Read `FB_Sustained_Development_Amendment_v1.md` before selecting work. After accepted FB5.2, execute discrete prospective batches 5.3, 5.4, 5.5 and 5.6, then 6.1–6.3. Original packaging is insufficient. Require 32/32 sustained coverage across the declared panel, generated-content chains, retained causal changes and longitudinal Shell correction. Do not force routes or credit duplicates as development. Read the latest state and respect its lease; the completed earlier conversation is not the owner. All inherited stop rules and the separate R5 requirement remain.
