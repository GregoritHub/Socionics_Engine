# FB5.1 development attempt 2

Command: `PYTHONPATH=baseline/HLE_Rebuild_R21B:. python -m unittest -v tests_workflow_population.test_population`

Result: 11 methods ran; ten passed and one errored.

The mixed scheduler fixture was repaired and passed. The forged decision-family case was rejected by a missing-record `KeyError` before the auditor converted it into its public `ValueError` rejection. The next amendment moves the explicit decision-family check before record resolution. No acceptance claim is based on this attempt.
