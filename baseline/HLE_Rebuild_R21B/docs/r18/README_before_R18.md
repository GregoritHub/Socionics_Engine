# Holonic Living Engine — R17

R17 implements conversion, practice and reownership in the declared workshop domain. The R12–R21 extension is 6/10 parent milestones complete; four remain. Next: R18 — full individuation circuits.

All earlier source, specifications and evidence are preserved. See `docs/r17/Integration_R17.md`, `docs/r17/Step_R17_Report.md` and `docs/r17/Progress_After_R17.md` for mechanisms, results and limits.

Run with Python 3.12 and the standard library:

```bash
python tools/r17_validate.py --out /tmp/hle-r17-validation
python tools/r17_evidence.py --out /tmp/hle-r17-panel
```

Programmatic demonstration:

```python
from hle.conversion_demo import case
from hle.conversion import ConversionWorld
from hle.conversion_reference import evaluate
world, setup = case()
report = evaluate(world)
restored = ConversionWorld.restore(world.checkpoint())
assert restored.checkpoint() == world.checkpoint()
```

`ConversionWorld.import_r16(text)` verifies and preserves an ordinary R16 journal. Conversion must still be opened over owned generated material and completed through paid context, real practice and retained use. `shell_report()` keeps the historical five-sign assessments visible; R17 does not issue an R19 clearance verdict.

The experiment offers an explicit conversion opportunity and a finite hypothesis grammar. Material, practice and retention controls establish consequential dependence in that domain. The full sixteen-type R18 circuits, R19 clearance/recurrence, R20 recursive/shared closure and R21 release panel remain open. Original R16 entry points and tests remain available unchanged.
