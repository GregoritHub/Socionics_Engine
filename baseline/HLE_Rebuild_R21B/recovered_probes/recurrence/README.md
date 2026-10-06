# HLE Id/Identity recurrence probe after R11

This is a runnable experiment on the Fool's Memory recurrence. The accepted R11
runtime is bundled unchanged in `hle/`. Experimental schedules, fixtures, the
common decision adapter, and the runner are isolated in `probe/`.

The source specifies three Id cycles per Ego cycle with Ego and Super-Ego in
parallel. It explicitly leaves the traversal and the relationship between the
labels Id and Identity open. This experiment provisionally connects the three
Identity cards to a three-phase Id clock. It does not amend the source manual.

Read `docs/Report.md` for the measured outcome and `docs/Progress.md` for status.
The original declaration is `docs/acceptance.json`; its SHA-256 was recorded
before implementation and evaluation:

`b1158d6b9251a44045b2808b7679136e90bef193e5920c9403e7d10e169c045e`

## Reproduce

Use Python 3.12 or later. No third-party packages are required. From this folder:

```bash
python3 -m unittest probe.test_recurrence -v
python3 -m probe.run
python3 -m probe.audit
```

The second command reruns the fixed panel and replaces its generated evidence
files. Each trajectory uses a fresh copy of the same declared initial history.
No fitted parameters or optimized seeds are loaded from previous results.

`evidence/trials.jsonl` contains every trajectory, every budgeted answer, actual
action outcomes, prices, and state hashes. `evidence/aggregates.json` and
`evidence/summary.json` contain the aggregates. Selected full checkpoints before
and after actions are compressed JSON in `evidence/checkpoints/`; the runner
replays each selected journal and checks exact state equality.

The participant adapter receives only published recall hits and the exact owned
memory revisions those hits name. Current observations, incomplete search
frontiers, and evaluator ownership are excluded. The adapter itself is a
supplied, uncharged rule, common to every policy. It is not claimed as a learned
decision process or an integration with language/organization routing.

The recall budgets are equal energy/time work allowances. Each attempted recall
step is genuinely charged by R3 inside R11 OrganizationWorld. The panel limits
recall attempts to the declared allowance; separate tests exhaust each physical
wallet resource and resume the unfinished work. Setup and external update costs
are recorded separately. Dynamic update slots are experiment opportunities,
not psychological time constants.

The bundled source documents remain in `reference/`. Runtime byte identity with
R11 is recorded in `evidence/runtime_identity.json`. The baseline R11 archive had
SHA-256 `54e832df695d4576441aebede8ddb5fbbf773c8b66401cc3ea9610a5494c7e36`.
