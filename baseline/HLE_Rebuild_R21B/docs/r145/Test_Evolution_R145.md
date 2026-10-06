# R14.5 verification history

The input R14 package and the acceptance declaration are pinned in Protocol_R145_v1.json. Historical tests, sources, documentation and evidence remain present.

During implementation:

- The first conceptual interception marked an unperformed return as attempted. It caused repeated inspection and search exhaustion. The interceptor now preserves the previous attempt history when it substitutes the exploratory inspection.
- A classroom fixture initially used `channels` instead of the existing `message_links` configuration field. The fixture and authenticated conceptual delivery now use the actual field.
- Two early new tests used an unsupported multi-argument Tick constructor. They now issue actual individual ticks; the original failure log remains.
- The first inherited run passed its behavioral checks and failed two byte-preservation assertions after the intentional memory implementation changes. The original test sources and old runtime bytes are retained under `reference/r14_preserved/`. The amended assertions check both the preserved old bytes and declared new bytes. No behavioral assertion was removed.
- The first panel reached all-prefix replay and the cost comparisons, then failed in a reporting helper that used `granted`/`spent` instead of `credited`/`charged`. That failed run is preserved. The final runner independently reconciles the actual fields and sequential balances.
- An aggregate runner loaded an expected count of 26 before a newly added resource test increased its observed count to 27. It correctly rejected the aggregate despite the tests passing. That result is preserved as a count mismatch, not a behavioral failure. The final fixed suite contains 28 tests.
- Final review strengthened practice acquisition: taught relations plus a clean return cannot bypass the learner's own actual care work. The dedicated counterexample passes. Raw ordinary testimony is also rejected as an authenticated conceptual lesson.

Complete logs, deterministic panels and checkpoint snapshots accompany the release. The final fresh-extraction results are provided separately in the evidence package so that verification does not mutate the tested source archive.
