# R16A test evolution

The first detector-only run passed all 34 tests. The first complete new suite passed all 50 tests, including runtime controls, independent replay and partial-work continuation.

The first inherited validation found one failure: `tests.test_isolation.Isolation.test_runtime_imports_only_explicit_stdlib_or_new_modules`. The new assessor had imported `copy.deepcopy`, outside the preexisting explicit import allowlist. No participant behavior test failed in that batch. The implementation was changed to use its existing recursive JSON-safe report copier. The allowlist and inherited tests were not changed. A targeted rerun of the isolation test and report-mutation test passed. The full first-run logs are retained under `evidence/r16a/`.

Subsequent review replaced whole-fact and active-builder scans at loan closure with addressed lookups, and rejected unknown assessment/projection versions. These do not change the sign definitions or parent criteria. Final delivered-source validation is recorded in the paired evidence archive. No frozen acceptance condition or inherited behavioral assertion was weakened.

A final timing audit found that late interpretation could be reported as a negative observation instead of unassessed. The opportunity now carries its exact engagement time; delivery and interpretation must already be usable at that time. Missing or future engagement times cannot qualify. The temporal-control assertion was strengthened from negative to unassessed, with no change to the frozen criterion. `Timing_Repair.patch` preserves the exact change. The first packaged candidate passed all 686 tests before this repair; that complete result is retained separately. The repaired candidate is independently packaged and verified again.
