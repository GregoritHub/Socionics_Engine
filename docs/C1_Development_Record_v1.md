# C1 development record

All items below are retained development outcomes, not rewritten passes.

1. The first smoke inspection attempted to ask `plan_request` to authorize an earlier superseded plan. The existing guard correctly rejected it. Historical comparison now reads that plan’s immutable propositions; execution still requires a current plan.
2. The first independent access auditor read a bind event as a single binding. The established access format stores `(binding, receipt)`. The auditor now explicitly checks and unpacks both.
3. The first semantic comparison attempted to serialize a dictionary with the strict native codec. That codec accepts typed tuples and records. Audit comparisons now serialize sorted typed item tuples.
4. `development/first_test_run` contains the complete first 18-test run: 17 methods passed, one errored. The exhaustion fixture supplied 26 units while preparing the actor required 27, so it failed during setup rather than during the new movement. The corrected fixture supplies 28 units: one remains for the movement, which then exhausts during its paid work. The resource gate was not weakened.
5. The complete 474-test run (20 C1 and 454 inherited methods) passed on its recorded source. Additional review constructed a paired corruption of an observation and its delivery fields before comparison work. The early independent auditor accepted that corruption because it checked the event link but not the complete observation projection. The runtime had not emitted an incorrect observation. `C1_Audit_Review_Amendment_v1.json` adds direct comparison with the actual event; a new corruption test and the affected C1 suite are rerun. The earlier successful run and the demonstrated audit gap remain in evidence.

The protocol and every test-run source manifest are retained in the evidence. Subsequent results are separate files and do not replace the failed first run.
