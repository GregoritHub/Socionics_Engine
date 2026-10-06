# Holon-owned contextual cue meanings — experimental build v1

This follow-up to R11 makes contextual card associations depend on the holon's
own action consequences. The Sun, Judgement and World are stable addresses;
their learned expectations are independent of Theorize, Apply and Embody.

The package includes the unchanged accepted R11 engine, a bounded experimental
controller, its declared acceptance criteria, the full run ledger, selected
replayable journals, and source references. It is an experiment, not a new
production release or an unrestricted concept-generation system.

## Run

Use Python 3.12 or later from this directory. No third-party package is needed.

```bash
python3 -m unittest meaningprobe.test_engine -v
python3 -m meaningprobe.run
python3 -m meaningprobe.audit
```

The panel runs 92 trajectories, including selected controller and independent
R11 journal replays. It can take several minutes, primarily serializing and
replaying the complete journals. It rewrites the generated evidence. For a
quick check of the existing ledger without full journal replay:

```bash
python3 -m meaningprobe.audit --no-replay
```

A single run is available directly:

```python
from meaningprobe.engine import Session

s = Session(history="east_reliable", policy="learned").run()
print(s.result()["episodes"][13])
checkpoint = s.checkpoint()
restored = Session.restore(checkpoint)
assert restored.checkpoint() == checkpoint
```

`Session.step(chunk=1)` exposes partial work. `credit(energy, time)` supplies
explicit continuation resources. Zero energy or zero time prevents paid
progress. Checkpoints reproduce the controller history against the R11 journal;
an edited and rehashed invented state is rejected.

## What is learned

Four supplied scene labels share three card cues. The first experience in a
scene acquires a least-used address, with a seeded tie order. A tentative owned
meaning retains the last three observed availability discrepancies and exact
links to embodied memories. A majority predicts that checking is useful. When
that association calls for checking, a paid binding and recall can bring an
actually acquired R4 capability into the next account. Thus the association
changes physical action selection. Successful transfer is learned from its
receipt, not misclassified from the recipient's ownership afterward.

Context allocation, the three-sample window, majority threshold, and available
checking procedure are supplied engineering rules. The resulting association,
expectation, historical links and updates come from the holon's own experience.
All four labels are known at setup; the holon discovers their consequences.
The fixture supplies the transfer demands and later reverses the conditions.

R3 charges recall, tentative retention, decision publication and exact binding.
R4 charges actual Model A routing, processing, action and embodiment. Bounded
controller calculations are not given a separately validated cognitive price.
All costs and scarce-resource stops are disclosed; acquisition and use need
not beat the fixed always-inspect policy on efficiency.

## Files

- `docs/Report.md`: outcomes, limitations and control comparison.
- `docs/Progress.md`: completed steps and remaining scope.
- `docs/acceptance.json`: criteria fixed before implementation/evaluation.
- `meaningprobe/learning.py`: pure owned-input association calculations.
- `meaningprobe/engine.py`: controller, paid publication and developmental use.
- `meaningprobe/test_engine.py`: 18 fidelity tests.
- `meaningprobe/run.py`: declared panel and receipt aggregation.
- `meaningprobe/audit.py`: independent completeness, cost and replay audit.
- `evidence/trials.jsonl`: every run and every completed demand.
- `evidence/aggregates.json`: full, retained, transitional and adapted windows.
- `evidence/checkpoints/`: 13 full controller/world checkpoints, compressed.
- `evidence/runtime_identity.json`: hashes of the 42 unchanged R11 modules.
- `reference/`: preserved source documents and extracted paragraph references.

The 9/3 phase counter remains an experimental grouping of the funded
developmental circuit. It does not independently transform Ego/Super-Ego
content, establish source-unique timing, or demonstrate higher developmental
altitude. R5 reports remain separate from association-learning success.
