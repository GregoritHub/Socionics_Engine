"""Execute and save the four prospectively frozen FB5.2 population worlds."""
import gzip
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.material import attrs
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads
from tests_workflow_population.sustained_fixtures import sustained_population
from tools.evaluate_workflow_selection import manifest

NAMES = ("Contemplate", "Act", "Express", "Embody", "Share", "Coordinate",
         "Theorize", "Understand", "Identify", "Mobilize", "Institutionalize",
         "Educate", "Apply", "Organize", "Commune", "Integrate")


def save(folder, key, population):
    engine = folder / (key + "-engine.json.gz")
    state = folder / (key + "-population.json.gz")
    engine.write_bytes(gzip.compress(population.engine.checkpoint().encode(), mtime=0))
    state.write_bytes(gzip.compress(population.checkpoint().encode(), mtime=0))
    return {"engine_file": engine.name, "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
            "population_file": state.name, "population_sha256": hashlib.sha256(state.read_bytes()).hexdigest()}


def actor_types(population):
    wanted = {r.actor for r in population.requests}
    rows = []
    for ref in population.engine._profiles.values():
        value = attrs(population.engine.world.resolve(ref))
        if value["actor"] in wanted:
            rows.append((value["actor"].key, value["tim"]))
    return dict(sorted(rows))


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / "source_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    cases = [("default-17", 17, 2), ("default-43", 43, 2),
             ("default-89", 89, 2), ("diagnostic-17", 17, None)]
    rows = []
    for key, seed_value, repeat_limit in cases:
        population = None
        try:
            population = sustained_population(seed_value, repeat_limit=repeat_limit)
            result = population.run(20000)
            if not result["done"]:
                raise AssertionError("population did not reach the declared bound")
            state = loads(population.checkpoint())
            report = audit_population(population.engine.world.journal(), state)
            row = dict(case=key, seed=seed_value, repeat_limit=repeat_limit,
                       types=actor_types(population), counts=population.counts,
                       stops=population.stopped, turns=population.turn,
                       audit=report, raw=save(out, key, population))
            rows.append(row)
            (out / "rows.json").write_text(json.dumps(rows, indent=2, default=str) + "\n")
            print("PASS", key, report["native_completions"], report["repeated_outputs"], flush=True)
        except Exception:
            (out / (key + "-failure.txt")).write_text(traceback.format_exc())
            if population is not None:
                save(out, key + "-failed", population)
            raise
    coverage = []
    for number, name in enumerate(NAMES):
        for face in ("accumulation", "expenditure"):
            recipe = "workflow-" + name.lower() + "-" + face + "-v1"
            by_world = {row["case"]: row["audit"]["successful_recipes"].get(recipe, 0) for row in rows}
            coverage.append(dict(cell=number * 2 + (face == "expenditure"), name=name,
                                 face=face, recipe=recipe, by_world=by_world,
                                 total=sum(by_world.values())))
    unchanged = manifest() == freeze
    summary = dict(passed=unchanged and len(rows) == 4,
                   source_unchanged=unchanged, raw_worlds=4,
                   native_completions=sum(r["audit"]["native_completions"] for r in rows),
                   repeated_outputs=sum(r["audit"]["repeated_outputs"] for r in rows),
                   covered_cells=sum(x["total"] > 0 for x in coverage),
                   claim="Repeated outputs remain repeats; no new-capacity or route-wide sustained-development claim.")
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert summary["passed"]


if __name__ == "__main__":
    main(Path(sys.argv[1]))
