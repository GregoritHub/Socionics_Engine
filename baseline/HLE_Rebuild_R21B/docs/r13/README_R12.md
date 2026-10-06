# Holonic Living Engine rebuild R12

Developmental contracts and frozen baseline · 17 September 2026

**R12 complete. Individuation and Shell-clearance extension: 1/10 milestones complete; nine remain. Next: R13 — integrated content and developmental memory.**

This release continues the runnable R11 engine and defines the contracts and acceptance tests for R13–R21. The 42 inherited runtime modules are unchanged. New modules specify developmental state, demands and opportunities, material treatment, paid work, capacity revisions, Shell evidence, closure evidence, and assessment protocols. They do not yet drive a developmental controller.

The recovered full R11 regression suite, the supplied crossing experiment, and the three earlier memory experiments are included. The useful holon-meaning mechanism is preserved for integration: stable cues acquire contextual associations from a holon's own consequences and change later recall and action. The manual does not prescribe universal personal meanings or a mandatory Sun/Judgement/World processing sequence.

## Run

Python 3.12 or later, standard library only, from this directory:

```bash
python -m hle
python tools/r12_validate.py
python tools/r12_baseline.py
python tools/validate_release.py
```

`r12_validate.py` runs the 353 original tests and 34 new contract/structural tests, checks 9,216 OIG quotient values against the pinned historical definition, and executes the frozen specification. `r12_baseline.py` reruns the original suite, crossing and R10/R11 study panels, 26 study/crossing tests, and 46 recovered probe fidelity tests. These suites overlap; the release contains **459 distinct passing unit tests**, not the sum of every repeated execution.

The default R11 demonstration remains available through `python -m hle`. Run the separate content-crossing experiment with:

```bash
python baseline/crossing/run_crossing.py --out evidence/r12/crossing_rerun.json
```

## What is frozen

- `docs/r12/acceptance_v1.json`: demand families, return identities, negative controls, twelve held-out challenges, and the 480-case future individual evaluation grid.
- `docs/r12/source_ledger_v1.json`: 28 source decisions with epistemic status and implementation gates.
- `docs/r12/operator_registry_v1.json`: 31 existing or proposed operator/detector contracts, with domains and failure conditions.
- `docs/r12/declaration_lock_v1.json`: hashes of those three declarations.
- `docs/r12/Contracts_R12.md`: contract fields, reference semantics, and integration requirements.
- `docs/r12/Source_Decisions.md`: recovery findings and theory/implementation distinctions.

`python tools/r12_specification.py` checks the declaration hashes and materializes the planned grid. Its **480 cases are unexecuted**. It reports all R13–R21 gates as **unassessed**. A fixture pass cannot complete a generated-runtime gate. Revisions to a frozen identity, threshold, operator or acceptance rule require a new declaration version and preservation of the earlier results.

## Source and evidence layout

| Path | Contents |
| --- | --- |
| `hle/` | Runnable inherited engine plus three new contract/structure/protocol modules. |
| `tests/`, `tests_r12/` | Recovered full regression suite and new R12 checks. |
| `baseline/crossing/` | Supplied crossing package, original R10/R11 module pins, fresh study outputs and historical snapshots. |
| `recovered_probes/` | Recurrence, developmental-coupling and holon-meaning source, declarations, reports, reference material and historical summary evidence. Full historical trajectory/checkpoint ledgers are not duplicated; their runners can regenerate them. |
| `reference/` | Unmodified source documents, recovered source material, pinned original archives and original R11 manifest. |
| `evidence/r12/` | This release's commands, logs, fresh outputs, reference comparison and exact declaration digest. |
| `docs/r12/Step_R12_Report.md` | Results, limits and completion gate. |
| `docs/r12/Progress_After_R12.md` | Remaining nine numbered milestones. |

The original R11 README is retained at `docs/r12/README_R11.md`; original documents under `docs/` describe their own historical release stages.

## Integration boundary

R12 performs local shape/consistency checks and exact bounded structural comparisons. It does not resolve every new reference against the live journal, serialize these records through the main runtime checkpoint codec, implement the five-sign detector, or confer individuation/clearance/altitude. Those are explicit later gates. The experimental content adapter still rejects checkpoint/restore; R13 must remove that limitation through actual integration.

Fresh crossing and R10 study output match their historical snapshots byte for byte. R11 output has one environment-dependent difference: the absolute script filename in the expected original-probe traceback. Raw files and hashes are retained; only that filename is normalized for comparison. No behavioral or accounting field differs.
