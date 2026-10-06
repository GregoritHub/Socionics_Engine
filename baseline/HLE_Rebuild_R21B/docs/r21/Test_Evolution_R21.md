# R21 evaluation and test evolution

- The seed-11 development pilot used a single allocation and no credits. The
  100,000-unit run exhausted resources during clearance, and 20,000 exhausted
  resources during development. These results remain in
  `evidence/r21/development/pilot_v1.log`.
- The evaluation environment was then frozen in `Protocol_R21_v1.json`; the
  original R12 acceptance file, prices, comparison law and success fractions
  were not changed.
- Initial evaluation output underreported unfinished workshop/decision jobs
  because the report inspected only `transaction.job`. The engine had kept
  them correctly in `workshop_job` / `decision_job`. The resource auditor now
  inspects these fields and physical action tasks. The preliminary output and
  interrupted run are retained in `panel_initial` and `panel_initial_run.log`.
  The complete 480-case final panel reruns the same frozen scenarios. The
  runner uses independent processes for independent episodes.
- The denominator checker additionally verifies the exact type/seed/regime
  grid, including substitutions as well as omissions and duplicates.
- Nine of ten new tests initially passed. One compatibility test incorrectly
  forbade the old R18 allocation already present in its inherited fixture.
  That fixture's historical credit is now explicitly allowed; the new strict
  budget tests still forbid credits. The focused recheck passes and does not
  increase the distinct test count.
- Increased-demand rows can execute successfully and still fail the frozen
  comparison: their actual remaining wallet differs from the equal-demand
  reference. Both live and independent evaluators agree on incomparability.
  R21 does not erase this finding, relabel it greater, or replenish the panel.

No participant capacities, success flags, resource prices, source claims or
R12 acceptance thresholds were changed to improve the release result.
