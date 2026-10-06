# FB1.2 — Read-only axes and integer decomposition: passed

[source_defined] What changed: `hle_unified/axes.py` adds the four Super-Ego axes, a type's DCNH core-pair cell on each axis, 2+1 formula positions and planes, integer load/tilt decomposition and recovery, and two-valued field signs and parity. `contracts/sources/Axis_Table_v1.json` transcribes all sixteen CT Table 11 rows. The formula attribution remains UMA §15 via CT; Gulenko's primary text was not reread.

[derived] How: axis cells follow CT §7.2's rationality/attitude bit rule; formula positions use the sealed Model A inverse frame. Loads are pole sums and tilts are pole differences. Recovery checks integer parity before dividing by two. Inputs reject floats and booleans. Two-valued fields may have tied axes: a tie produces a zero sign and makes pole parity undefined, so parity raises rather than silently classifying it.

[probe] What becomes possible: structural reports can compare exact axis loads and tilts without assigning participants a subtype. Neither new structural module is imported by execution, selection, pricing or scheduling code. No quaternion or order-128 group is shipped. No inherited engine, baseline or Model G module changed.

[probe] All 641 distinct methods passed on this freeze: 625 inherited methods, the eight Model G methods, and eight new axis methods. The axis tests reproduce 64 DCNH cells and 64 formula triples, check every formula's plane, check the grade and parity identities, and recover all 6,561 fields over {-1,0,1} plus sixteen signed large-integer basis fields. Zero failed, skipped or duplicate test methods. All 1,316 frozen files match after execution.

[probe] Commands and counts: `evidence/FB1.2/commands.json`. Source freeze: `evidence/FB1.2/source_freeze.json`. Raw logs, per-method outcomes and runner source manifests: `evidence/FB1.2/Raw_Evidence.zip`; hashes and extraction instructions are in its index and `Raw_SHA256.json`. The prospective protocol is the FB0.2 commit's `contracts/C7_Final_Protocol_v1.json`, SHA-256 c132e777e41e34221856ac71a02513168e42e8524c366114b0a430e8dcbe6baf. No new timing, pyref or release-completion claim is made.

[probe] Failures/fixes: no test or source-freeze failure in this batch. The required crossing regression ran to completion in about 474 seconds. Prior failed attempts remain preserved; FB1.1's transient GitHub delivery failure is separately recorded, with its digest now included in the evidence index.

[open] Next entry state: FB2.1, automatic workflow selection for the eight self-route cells, on the verified current source. Its phase protocol must be written and hashed before its new selector code. No selection implementation has started. Phase 1 is complete; Release 1.0 remains open. Phase 7 remains unauthorized, D-series assignments remain blank, pyref reruns remain owed, and no theoretical register item is closed.

[probe] Delivery: approval review initially rejected the source-freeze upload for unverified-destination/metadata concerns. Read-only checks confirmed the explicitly authorized repository and that only three entries were new. Review then timed out; the single permitted retry succeeded with the identical payload. Exact attempts and checks are in `evidence/FB1.2/delivery_attempts.json`. No protection was bypassed and no engine/evidence bytes were changed to obtain approval.
