# FB0.1 — Intake and reproduction: passed

[probe] All 1,714 delivered-source entries and all 161 source-freeze-v4 entries match. No inherited source, baseline, contract or evidence file was changed.

| Gate | Expected | Observed |
| --- | --- | --- |
| Distinct tests | 602 inherited + 23 workflow | 625 passing |
| Native workflow cases | 512 | 512 passing |
| Independent saved-world reconstruction | 512 ordinary; 32 controls | 512 pass; 32 rejected |
| Closure probes on R21B | 10/10 | 10/10 |
| Below-DCNH probes on R21B | 17/17 | 17/17 |
| Workflow inactive-history ratio | ≤3.0× | 1.193328× |
| Unchanged-native ratio | ≤2.0× | 0.959507× |
| Native inactive-history ratio | ≤3.0× | 1.052530× |

[probe] These counts reproduce the supplied bounded baseline; they do not close milestone C7 or make claims about people. No optimization claim is made.

## What changed, how, and what becomes possible

[probe] The project now has a persistent GitHub source tree, the supplied documents and readable transcriptions, a batch register, and a freshly reproduced intake evidence set. Original engine semantics remain unchanged. Each source file was checked before and after execution, and the saved workflow worlds were independently reconstructed. Batch 0.2 can now declare the final protocol against a verified baseline.

## Commands, freeze and evidence

[probe] The six commands in the release report and both supplied probes were run. Exact commands, exit codes, durations, source checks and all logs are in the evidence archive identified by `docs/FB0.1_Evidence_Index.json` → `FB0.1/commands.json`. The executed Python freeze is `FB0.1/execution_freeze.json`; full kernel hashes are in `FB0.1/kernel_hashes.json`. The archive digest and extraction command are in `FB0.1_Evidence_Index.json`. Expected and observed counts are in `FB0.1/acceptance_summary.json`.

## Failures and interruptions

[probe] The first native-cost measurement attempt lost its execution session after worker 12. Its incomplete output remains under `native-costs/` and is not counted as a pass. A fresh attempt under `native-costs-attempt-2/` completed all 33 workers on unchanged source. No baseline repair was made.

[probe] Direct shell push lacked GitHub credentials, so repository writes used the authorized GitHub connector. Large tree assembly timed out twice; smaller groups completed the same byte-preserved import. These were delivery failures, not engine test failures.

[derived] The supplied plan says 21 batches but explicitly enumerates 22 (18 through Release 1.0 and four gated Phase 7 batches). The register follows its numbered work orders without reordering or adding work.

[open] The sealed 5.2.1 pyref was not supplied; its rerun remains owed. Phase 7 remains unapproved. Next: batch 0.2, final prospective protocol. No theoretical register item has been closed by this run.
