# Holonic Living Engine R16A

Joint Shell assessment infrastructure, version 1.6.0a1. **R16 remains open.**

The five independent sign detectors, ordinary controls, twelve OIG lenses, and a live journal adapter are implemented. The unchanged R15 generated workshop supports a forced-placement assessment. The other four runtime signs remain explicitly unassessed; their current positive examples are detector fixtures.

```bash
python -m hle
python tools/r16a_validate.py
python tools/r16a_evidence.py
python tools/validate_release.py
```

Python 3.12+, standard library only. Run from this directory. Full inherited validation and checkpoint replay take several minutes.

```python
from hle.shell_demo import case
from hle.shell_runtime import ShellAssessmentWorld
from hle.shell_reference import reference
from hle.shell_demo import signatures

simulation, setup = case()
report = simulation.shell_report()
assert signatures(simulation) == reference(simulation)
restored = ShellAssessmentWorld.restore(simulation.checkpoint())
assert restored.shell_report() == report
```

`ShellAssessmentWorld` extends `CompensationWorld` with an isolated, read-only evaluator. Participant selection, exact particulars, conceptual memory, resource charges and checkpoint bytes retain their R15 behavior. The monitor is derived from committed transactions and rebuilt on restore. No verdict is inserted into participant memory, and reporting does not spend or refund simulated resources. Evaluator traversal counts are separate from actor work.

The primary generated case establishes maintained forced placement across three eligible renewals with three correct physical returns. The ordinary-history and zero-revision-cost controls have no positive placement observations. Carrier refusal yields one positive engagement, followed by local revision; retries cannot manufacture three renewals. This is neither full individuation nor Shell clearance.

Read `docs/r16a/Integration_R16A.md`, `docs/r16a/Step_R16A_Report.md`, and `docs/r16a/Progress_After_R16A.md`. `Protocol_R16A_v1.json` declares the finite projection and experiment. Earlier source, tests, frozen acceptance criteria and evidence remain preserved. The paired evidence archive includes release verification.

**Parent progress R12–R21 remains 4/10; six remain. R14.5 is a separate completed prerequisite. Next: R16B — the four missing runtime sign channels and post-increase defensive-structure evidence.**
