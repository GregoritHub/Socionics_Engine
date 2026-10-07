# FB5.1 development attempt 1

Command: `PYTHONPATH=baseline/HLE_Rebuild_R21B:. python -m unittest -v tests_workflow_population.test_population`

Result: 11 methods ran; nine passed and two errored.

- The fabricated-summary test selected the first scheduler row, which was still a paid partial row and therefore had no decision field. The implementation had not accepted forged data; the test mutation was aimed at the wrong row.
- The mixed legacy/workflow fixture attempted to expose the inherited Shell trigger before declaring that fixture object in the workflow world.

Both are local test-fixture defects. This failed attempt is retained; no acceptance claim is based on it.
