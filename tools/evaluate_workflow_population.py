"""Save the prospective FB5.1 workflow-population panel."""
import gzip
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.population import Population
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads
from tests_workflow_population.fixtures import (
    workflow_population, material_population, mixed_population,
)
from tools.evaluate_workflow_selection import manifest


CASES = ("fair", "interrupted", "material-feedback", "repetition", "exhaustion", "mixed")


def save_population(folder, name, population):
    engine_path = folder / (name + "-engine.json.gz")
    state_path = folder / (name + "-population.json.gz")
    engine_path.write_bytes(gzip.compress(population.engine.checkpoint().encode(), mtime=0))
    state_path.write_bytes(gzip.compress(population.checkpoint().encode(), mtime=0))
    return dict(
        engine_file=engine_path.name,
        engine_sha256=hashlib.sha256(engine_path.read_bytes()).hexdigest(),
        population_file=state_path.name,
        population_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest(),
    )


def build(name):
    if name == "fair":
        p, _ = workflow_population(2, 3, 17, repeat_limit=None); p.run(2000)
    elif name == "interrupted":
        p, _ = workflow_population(2, 3, 7, repeat_limit=None); p.run(5)
        p = Population.restore(p.checkpoint()); p.run(2000)
    elif name == "material-feedback":
        p, _ = material_population(); p.run(2000)
    elif name == "repetition":
        p, _ = workflow_population(2, 24, 32, repeat_limit=2); p.run(2000)
    elif name == "exhaustion":
        p, _ = workflow_population(2, 100, 32, budget=90); p.run(10000)
    elif name == "mixed":
        p = mixed_population(2, 32); p.run(2000)
    else:
        raise ValueError(name)
    if not p.done:
        raise AssertionError("population did not reach its declared bound")
    return p


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest(); (out / "source_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    rows = []
    for name in CASES:
        p = None
        try:
            p = build(name)
            state = loads(p.checkpoint())
            report = audit_population(p.engine.world.journal(), state)
            rows.append(dict(case=name, done=p.done, turns=p.turn, counts=p.counts,
                             stops=p.stopped, audit=report,
                             charged_energy=sum(x["charged"][0] for x in p.events),
                             raw=save_population(out, name, p)))
            (out / "rows.json").write_text(json.dumps(rows, indent=2, default=str) + "\n")
            print("PASS", name, flush=True)
        except Exception:
            (out / (name + "-failure.txt")).write_text(traceback.format_exc())
            if p is not None:
                save_population(out, name + "-failed", p)
            raise
    unchanged = manifest() == freeze
    summary = dict(passed=unchanged and len(rows) == len(CASES), raw_worlds=len(rows),
                   total_turns=sum(x["turns"] for x in rows),
                   modeled_energy=sum(x["audit"]["modeled_energy"] for x in rows),
                   native_completions=sum(x["audit"]["native_completions"] for x in rows),
                   source_unchanged=unchanged)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert summary["passed"]


if __name__ == "__main__":
    main(Path(sys.argv[1]))
