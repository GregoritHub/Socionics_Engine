# R19 implementation findings

All original R12 gates, thresholds, family names and held-out variations remain unchanged. Initial diagnostic runs and their logs are preserved under `evidence/r19`.

1. The first smoke run used the wrong event-field name while locating the original tool. `WorldEvent.objects` is the correct field. No trial outcome or acceptance rule changed.
2. The first full suite incorrectly expected every simultaneous commitment to take load one. With two commitments, using one then two fits the shared budget three. The corrected assertion checks this actual valid allocation, and one each for three commitments. The original load-budget requirement is unchanged.
3. The initial displacement runner stopped after a refusal without continuing its retry. That did not establish a move to the other carrier. The runner now follows the generated retry, second selection, request, response and assimilation. The displacement control then verifies the actual second carrier and the reopened verdict. The initial runner and failing tests are retained.
4. Inspection of validity dependencies exposed the need to follow originating events as well as direct evidence references. Native world corrections and withdrawals of practice events now invalidate their dependent capacity or claim. Unrelated evidence withdrawals remain harmless controls.
5. The old R16 adapter flagged legitimate R17 conditional views as concept mismatches. The new adapter authenticates the actual paid conditional use and the retained fallback. It preserves the old sign predicates and removes those false diagnostics in R19.
6. Repeated nested serialization made checkpoint checks expensive. R19 now assembles the same typed nested value once and shares R18's typed restoration entry point. Exact replay, partial-work continuation and recomputed-checksum forgery rejection verify this path.

The final validation log is authoritative for pass counts. Focused reruns and the initial failing log are kept separately and are not added to the number of distinct tests.

7. The complete regression run exposed imports outside the frozen runtime allowlist: new `copy`/`zlib` use and an inherited R18 `zlib` import. The restriction was preserved. R19 now uses the existing detached JSON-value copier and an equivalent dependency-free CRC-32 identifier. The isolation suite passes; 1,003 identifier comparisons, an identical full SLI journal/report and exact delivered-checkpoint restoration establish compatibility. The main failing run and focused corrective checks are retained separately.
