# R17 test evolution

The frozen R12 declaration was not amended. All 718 inherited tests passed.
The final R17 suite contains 33 additional tests, for 751 total.

The first 29-test candidate had one error in the failed-practice retry case.
A real intervening tool use made the tool dirty after a provisional return
selection. R16 account scheduling attempted to consume that stale opportunity
and rejected it. The original error log is preserved in the paired evidence.

Filtering out the stale opportunity prevented the invalid account operation,
but exposed the inherited finite attempt cache: the actor could exhaust its
ordinary alternatives after reencountering the same dirty state. The unchanged
retry assertion still failed. That intermediate failure is also preserved.

The conversion procedure now retains the unsuccessful physical consequence,
adds a fresh-own-inspection precondition, and can execute paid native cleaning,
inspection and a new return attempt. This is operational revision from feedback,
not a cleared attempt counter. The failure remains in the candidate's lineage;
it gives no successful-practice credit. The restored procedure retains and uses
its new inspection guard after later acquisition.

The final suite also checks material deletion as a fault, observation-matched
hidden physical changes, and rejection of foreign capacity use. No failing
acceptance assertion was removed or weakened. Initial and intermediate logs
remain historical, separate from final verification.

A stricter independent-use test then exposed a subtler remaining dependency:
R15 returned directly, but the earlier R16 account workflow still awaited a
peer's acceptance. Its failing test and the earlier candidate sources are
preserved. A valid paid provisional or retained application now supplies the
source distinction itself, so it does not reenter that peer-account workflow.
Required accepted terms still invoke real paid confirmation. The final panel
checks absence of peer-account substitution explicitly, in addition to the
physical return and R15 carrier checks.
