# Holonic Living Engine — R16

R16 completes joint runtime assessment of all five Shell signs in the declared workshop domain. The R12–R21 extension is 5/10 parent milestones complete; five remain. Next: R17 — conversion, practice and reownership.

Recovered R16A and all earlier source, specifications and evidence are preserved. See `docs/r16b/Integration_R16.md`, `docs/r16b/Step_R16_Report.md` and `docs/r16b/Progress_After_R16.md` for mechanisms, results and limits.

Run with Python 3.12 and the standard library:

```bash
python tools/r16_validate.py --out /tmp/hle-r16-validation
python tools/r16_evidence.py --out /tmp/hle-r16-panel
```

Programmatic demonstration:

```python
from hle.reconciliation_demo import case
from hle.reconciliation import ReconciliationWorld
world, setup = case()
report = world.shell_report()
restored = ReconciliationWorld.restore(world.checkpoint())
assert restored.checkpoint() == world.checkpoint()
```

`ReconciliationWorld.import_r15(text)` preserves ordinary R15/R16A journals and enables the new workflow for future opportunities. `placement_report()` retains the older bounded observer. Frozen sources and acceptance gates are unchanged. This release does not complete R17 conversion, full individuation or Shell clearance.
