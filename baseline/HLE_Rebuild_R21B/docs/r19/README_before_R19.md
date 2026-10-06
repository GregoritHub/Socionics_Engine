# Holonic Living Engine — R18

R18 implements full individuation circuits within the declared finite workshop domain. The R12–R21 extension is 7/10 parent milestones complete; three remain: R19 clearance/recurrence, R20 recursive/shared closure and R21 sustained release evaluation.

The same continuing actor learns eight consequential work-order constraints, retains them through actual own practice, and uses them in two shared/system feedback circuits after helper withdrawal. All sixteen fixed types are covered under self-acquired, dual-supported and nondual-supported correction. Earlier source, frozen declarations, physical workshop behavior and historical assessments remain preserved.

Run with Python 3.12 and the standard library:

```bash
python tools/r18_validate.py --out /tmp/hle-r18-validation
python tools/r18_evidence.py --out /tmp/hle-r18-panel
```

Programmatic demonstration:

```python
from hle.individuation_demo import case
from hle.individuation import IndividuationWorld
from hle.individuation_reference import evaluate
world, setup = case(tim='sli', mode='self')
report = evaluate(world)
assert report['integrity_passed'] and all(report['gates'].values())
restored = IndividuationWorld.restore(world.checkpoint())
assert restored.checkpoint() == world.checkpoint()
```

`IndividuationWorld.import_r17(text, partners=...)` verifies an original R17 checkpoint and extends its journal. The 48-case comparison uses partner load capacity 5 and learner order budget 3 so that own overload and partner availability have separate consequences. Supply the same `WorkPartner` policies when reproducing that comparison with an imported checkpoint. An existing R18 checkpoint preserves those policies automatically.

The complete continued checkpoint is in `evidence/r18/panel/continued_r17.checkpoint.json.gz`. Decompress it with Python's `gzip` module before calling `restore`. It includes the exact original R17 prefix and the R18 continuation. Restoring validates and replays the whole journal; retained-history processing is appreciably heavier than ordinary active work.

See `docs/r18/Integration_R18.md`, `docs/r18/Step_R18_Report.md`, `docs/r18/Progress_After_R18.md` and `docs/r18/Test_Evolution_R18.md`. The new task grammar and complex operationalizations are declared implementation hypotheses. No permanent clearance, higher closure, unrestricted development or human psychological validity is claimed. The R21 480-case release panel remains unexecuted.
