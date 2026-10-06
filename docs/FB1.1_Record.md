# FB1.1 — Read-only Model G layer: passed

[source_defined] What changed: `hle_unified/model_g.py` exposes G↔A positions, source names and blocks, three polarities, exact grades and grade names, signs, block/grade partners, and the source's two-link spine. `contracts/sources/Model_G_Table_v1.json` retains CT Tables 9/10, the two source citations, and `transcribed_not_reread: true`.

[derived] How: the module derives fields from the sealed Model A, the CT reindexing and bit formulas. It does not load its test oracle. Names remain distinct: G Creative is A8; G Demonstrative is A2. Only A6→A1→A8 is exposed as the directed source spine; no internal-plane direction is chosen. No existing engine file imports the new module.

[probe] What becomes possible: later structural reports can inspect Model G attributes without changing participant behavior. No pricing, selection, competence, subtype, source ruling, or theoretical register closure is introduced.

[probe] Eight new tests passed, including 128 source-table element/sign cells, position attributes across all 16 types, both grade formulas, partner identities and all 40,320 reindexing permutations (one fit). All 625 inherited methods passed: 602 package methods plus 23 workflow methods. No test failed or was skipped. All 1,313 frozen files match after evaluation; no inherited source file changed relative to the FB0.2 checkpoint. Original delivered files remain unchanged except the explicitly authorized manifest append recorded in FB0.2.

[probe] Exact commands and counts are in `evidence/FB1.1/commands.json`; per-method outcomes, raw logs and test-run source manifests are in `evidence/FB1.1/Raw_Evidence.zip`, with `Raw_SHA256.json` and `Raw_Evidence_Index.json`. The evaluation freeze is `evidence/FB1.1/source_freeze.json`; protocol is the previously committed `contracts/C7_Final_Protocol_v1.json`. Its SHA-256 is c132e777e41e34221856ac71a02513168e42e8524c366114b0a430e8dcbe6baf. No new theory-probe run or timing gain is claimed.

[probe] Failures/fixes: none in this batch. Required regression tests ran to completion on unchanged source; the crossing package took about 476 seconds.

[open] Next: FB1.2, read-only axes, DCNH formula positions, and integer load/tilt decomposition. The sealed pyref rerun and primary-source rereading remain owed. Release 1.0 remains open.
