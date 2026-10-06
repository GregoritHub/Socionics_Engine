# HLE full Crux — C3

C3 implements both faces of the twelve crossing routes in the inherited paid engine. Together with C2, all sixteen formal route names now have bounded realizations under both polarities. The full 32-cell release remains open: composition/nesting, route-wide Shell development, autonomous selection/transfer and sustained release gates are C4–C7.

Python 3.12 and the standard library are sufficient. No network, API key, model service or installation is required. Run from this directory with the package and preserved core on the import path:

```sh
export PYTHONPATH=.:baseline/HLE_Rebuild_R21B
python -c 'from hle_unified.crossing_execution import CrossingEngine'
```

```python
from hle_unified.crossing_execution import CrossingEngine
from hle_unified.crossing_records import CrossingRequest, CROSSING_RECIPES
```

`tests_c3/fixtures.py` demonstrates generated source content, exact exchange, voting, paid processing, actual material effects and later consumers. These are fixtures, not autonomous participant route selection. `CrossingEngine.from_c2(text)` upgrades an exact C2 checkpoint by replay. `from_c1`, `from_u14` and `restore` remain available. Legacy `CognitiveRequest(purpose="integrate")` still means Embody (IT → I).

## Reproduce

Use new output directories so earlier failures remain intact:

```sh
python tools/evaluate_c3.py --inherited --out /tmp/hle-c3-tests
python tools/export_crossing_witnesses.py --out /tmp/hle-c3-witnesses
python tools/evaluate_source_transfer.py --out /tmp/hle-c3-source-transfer
```

After tests and profiling finish, measure sequential isolated workers:

```sh
python tools/measure_c3.py --out /tmp/hle-c3-measurements
```

This runs 24 timing workers and six separately traced workers. Each worker starts a fresh Python process; restore creates fresh engine instances by replay within that worker. The 24-cell panels include separately paid setup content, exchanges, native actions and downstream consumers. Initial engine construction is excluded. Checkpoint creation, restore and independent audit are reported separately. The full measurement run takes several minutes.

Extract the evidence archive, then reconstruct the delivered acceptance decision:

```sh
python tools/verify_delivery.py --evidence /path/to/HLE_Full_Crux_C3_Evidence_v1
```

The verifier checks raw transactions and access archives for all 48 main and 12 supplementary healthy/control witnesses, source identities, recorded test populations, sample counts, cost invariants and inherited preservation. It does not call the participant selector. The supplementary social cases preserve a receiver’s prior usable limit while removing the received constraint; healthy learning changes its earlier choice. Failed development and evaluation attempts remain separate from accepted evidence. The report states which stages supply each current test population.

## Scope and compatibility

Read `docs/C3_Architecture_and_Scope_v1.md`, the milestone report and the updated full-Crux specification. C3 adds a finite allocation/stock-observation language with conditional models and a two-member voluntary-rule protocol. It does not replace U12 institutional lifecycle logic, establish practiced skill from communication, or supply arbitrary language understanding.

Two shared files receive extension hooks: `crux_execution.py` dispatches C3 paid steps and installs generated material amounts only after the semantic step; `self_audit.py` accepts an optional extent/audit extension. Default C1/C2 behavior remains covered by inherited regression and the matched original-C2 comparison. C2 source snapshots at `reference/c2_crux_execution.py` and `reference/c2_self_execution.py` supply that reference, with only an import redirection in the benchmark loader. All other inherited native runtime and frozen baseline files remain unchanged.

Exact history is retained; no bounded-total-memory or unbounded scaling claim is made. The source archive includes the historical baseline and evidence needed to continue development. C3's evidence archive contains the current raw witnesses and measured acceptance record.
