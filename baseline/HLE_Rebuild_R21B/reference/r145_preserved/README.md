# Holonic Living Engine R14.5

Particulars and contextual conceptual integration, version 1.4.5.

The workshop now retains exact particulars through paid direct lookup and keeps conceptual relationships, tensions and acquired practice in a separate personal structure. Both use one journal, the existing Model A machinery, actual workshop actions and replayable checkpoints.

```bash
python -m hle
python tools/r145_validate.py
python tools/r145_evidence.py
python tools/validate_release.py
```

Python 3.12+, standard library only. Run commands from this directory. Validation and evidence generation take several minutes.

```python
from hle.concept_demo import world
from hle.autonomy_demo import run
from hle.conceptual import ConceptualWorld

simulation = world(tim="iee")
run(simulation)
restored = ConceptualWorld.restore(simulation.checkpoint())
```

`hle.autonomy.AutonomousWorld` preserves the R14 comparison. Use `ConceptualWorld.import_r14(text)` for an explicit R14 checkpoint migration. Legacy detail and symbolic APIs remain available; the new default workshop does not create card bindings for particulars.

Read `docs/r145/Integration_R145.md` for the source definitions, experimental choices, interfaces and limits, and `docs/r145/Progress_After_R145.md` for the handoff. The source package preserves earlier implementations, tests and evidence. New logs and panels are under `evidence/r145/`; fresh-extraction verification is in the paired evidence archive.

The demonstration learns the relation between accepted use, care and release. Static content, live guidance and independently retained practice have different effects. It is one finite conceptual domain, with declared learning and exploration rules. It does not prove a complete theory of archetypes, complete semantics for every rank, generated Shells, full individuation or clearance.

**Parent progress: R12–R21 remains 3/10. R14.5 is an additional completed integration prerequisite. Seven parent milestones remain; R15 is next.**
