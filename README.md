# HLE Full Crux — C7 second-setting update

Second-setting content coverage: **32/32 cells**. Full release remains held, progress **6/7**.

Read `docs/HLE_Full_Crux_C7_Release_Candidate_Report_v2.md` and `docs/C7_Second_Setting_Contract_v1.md`. Python 3 and standard library suffice.

```sh
python tools/test_c6.py new-workflow-tests tests_c7_workflow
python tools/evaluate_c7_settings.py new-setting-matrix
python tools/verify_c7_settings.py new-setting-matrix
python tools/regress_c7_parallel.py new-regression
python tools/measure_c7_settings.py new-workflow-costs
python tools/measure_c6.py new-native-costs
```

`WorkflowEngine` and `WorkflowRequest` add the timed workflow domain; existing `SelectionEngine` APIs remain available. Restore each checkpoint with its corresponding engine. New-domain automatic selection, Shell integration and sustained assessment are not claimed complete. The protocol, four source freezes, independent audit, raw worlds and all earlier failed/source-changed attempts are preserved.
