# C4 development record

All successful claims use the final source and recorded verification. Earlier failures remain failures.

- `evidence_c4/smoke_01.log`: an import failed because the proposed `composition_records.py` filename collided with the preserved U9 module. No simulation ran. The original U9 records and auditor were restored byte for byte from the attached C3 archive. New modules and request types use the distinct `crux_composition_` / `CruxComposition` names.
- `evidence_c4/smoke_02.log`: the first parent commit exposed a missing `primitive="bind"` field in its new operation constructor. The constructor was corrected. The failed probe is retained.
- `evidence_c4/smoke_03.log`: all five circuits and the nested release example ran, passed independent audit and restored exactly.
- `evidence_c4/tests_01`: the initial 22-method C4 evaluation recorded two failures and no errors. Both asserted that `binding` was absent after noncompletion; the inherited operation schema includes `binding=None`. The engine retained no output in either case. The assertions were corrected to check the value. This run is not counted as passing.
- `evidence_c4/fixture_recheck.log`: both corrected assertions passed, including every recipe cancellation and a real retained withdrawal of assent, separately from a membership change.
- The final full regression, causal export and measurements use unchanged runtime/test source within each recorded run. Their source manifests identify the evaluated files. No failed timing run is silently relabeled or excluded from an accepted sample.

The prospective protocol is `contracts/C4_Protocol_v1.json`. No tolerance has been relaxed after observing a measurement. Interpretation and reporting distinguish a completed parent review from completion of the parent outcome it examines.

## Review amendment

`renewal_review_probe.log` exposed another authorization from the same renewed offer/reply under a new operation key. The C4 engine and independent auditor now retain a one-attempt exchange index, reconstructed by replay. The added test checks completed and cancelled attempts before and after restoration. `contracts/C4_Review_Amendment_v1.json` records this semantic guard; performance tolerances are unchanged. The earlier 15 witness exports remain in `witnesses_initial`; accepted witnesses are rerun against the final source.

An initial full regression launch is retained under `tests_interrupted`. The process became unavailable before producing a summary. Its partial log is not an accepted test population. The full run is restarted after review; no partial progress is reported as a completed regression run.

The subsequent frozen-source full regression also lost its runner transport before writing a summary. Its explicit `... ok` method results are retained, with individual timings unavailable for that prefix. `tools/resume_c4_evaluation.py` verifies the original source hashes, records exactly which methods have passed, and runs only the remaining methods. It saves every continuation result immediately. The final summary identifies this combined execution rather than claiming one uninterrupted run.

## Accepted regression continuation

On 23 September, the user resumed the interrupted turn. The runner retained 316 recorded method results and completed the remaining 238 against the same 135-file execution manifest. The final combined population contains 554 distinct passes with zero failures, errors or skips. Every method has an explicit raw-log pass; prefix timings and a single uninterrupted-run duration are unavailable. The final witness export retained seven healthy/control pairs and one lawful cancelled-child outcome against the guarded source. Performance workers started after both regression and witness export finished.
