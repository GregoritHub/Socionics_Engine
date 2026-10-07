"""Prospectively frozen FB5.2 isolated workflow-population cost workers."""
import gzip
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from tools.evaluate_workflow_selection import manifest


def worker(history, shared, task_count, traced):
    from hle_unified.population import Population
    from hle_unified.population_audit import audit_population
    from hle_unified.selection_records import loads
    from hle_unified.workflow_selection_audit import audit as selection_audit
    from tests_c7_workflow.fixtures import DEVICE, request, work
    from tests_workflow_population.sustained_fixtures import sustained_population

    start = time.perf_counter()
    population = sustained_population(17, inactive=history, shared=shared,
                                      task_count=task_count)
    setup_seconds = time.perf_counter() - start
    before = sum(population.engine.wallet(r.actor)["energy"] for r in population.requests)
    if traced:
        tracemalloc.start()
    start = time.perf_counter(); cpu = time.process_time()
    result = population.run(20000)
    active_cpu = time.process_time() - cpu; active = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] if traced else None
    if traced:
        tracemalloc.stop()
    if not result["done"]:
        raise AssertionError("population did not finish")
    successful = [row for row in population.events if row.get("native_status") == "succeeded"]
    if len(successful) != 4:
        raise AssertionError("fixed active workload differs")
    selected = successful[-1]
    start = time.perf_counter()
    work(population.engine, request(population.engine, "fb52-cost-query", "use-personal", None,
                                   (selected["output"],), actor=selected["actor"], target=DEVICE,
                                   completed=("task-0",), clock=1))
    query_seconds = time.perf_counter() - start
    start = time.perf_counter(); checkpoint = population.checkpoint()
    checkpoint_seconds = time.perf_counter() - start
    start = time.perf_counter(); restored = Population.restore(checkpoint)
    restore_seconds = time.perf_counter() - start
    if restored.checkpoint() != checkpoint:
        raise AssertionError("cold restore differs")
    start = time.perf_counter()
    population_report = audit_population(population.engine.world.journal(), loads(checkpoint))
    native_report = selection_audit(population.engine.world.journal(), population.engine.access.checkpoint())
    audit_seconds = time.perf_counter() - start
    after = sum(population.engine.wallet(r.actor)["energy"] for r in population.requests)
    print(json.dumps(dict(history=history, history_kind="shared" if shared else "unique",
        tasks=task_count, traced=traced, setup_seconds=setup_seconds,
        active_wall_seconds=active, active_cpu_seconds=active_cpu,
        downstream_query_seconds=query_seconds, checkpoint_seconds=checkpoint_seconds,
        cold_restore_seconds=restore_seconds, raw_audit_seconds=audit_seconds,
        traced_peak_bytes=peak, checkpoint_bytes=len(checkpoint.encode()),
        gzip_bytes=len(gzip.compress(checkpoint.encode(), mtime=0)),
        modeled_actor_spending=before-after, transactions=len(population.engine.world.journal()),
        native_completions=population_report["native_completions"],
        repeated_outputs=population_report["repeated_outputs"],
        workflow_selections=native_report["workflow_selections"],
        exact_restore=True, raw_audit=True, passed=True)))


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    source = manifest()
    (out / "source_freeze.json").write_text(json.dumps(source, indent=2) + "\n")
    configs = [(n, shared, 2) for shared in (False, True) for n in (0, 100, 1000)]
    configs += [(0, False, n) for n in (4, 8)]
    rows = []
    for history, shared, task_count in configs:
        for sample, traced in ((0, False), (1, False), (2, True)):
            key = f"h{history}-k{'shared' if shared else 'unique'}-t{task_count}-r{sample}"
            proc = subprocess.run([sys.executable, __file__, "--worker", str(history),
                                   str(int(shared)), str(task_count), str(int(traced))],
                                  cwd=ROOT, capture_output=True, text=True)
            (out / (key + ".stdout.json")).write_text(proc.stdout)
            (out / (key + ".stderr.log")).write_text(proc.stderr)
            if proc.returncode:
                raise RuntimeError(key + " worker failed: " + proc.stderr)
            row = json.loads(proc.stdout); row.update(sample=sample, key=key)
            rows.append(row)
            print(key, round(row["active_wall_seconds"], 4), flush=True)
    history_panel = {}
    for kind in ("unique", "shared"):
        medians = [statistics.median(r["active_wall_seconds"] for r in rows
                   if r["history"] == n and r["history_kind"] == kind
                   and r["tasks"] == 2 and not r["traced"])
                   for n in (0, 100, 1000)]
        ratio = max(medians) / min(medians)
        history_panel[kind] = dict(records=[0, 100, 1000], medians=medians,
                                   largest_smallest_ratio=ratio, tolerance=3.0,
                                   passed=ratio <= 3.0)
    task_panel = {}
    for count in (2, 4, 8):
        values = [r["active_wall_seconds"] for r in rows if r["history"] == 0
                  and r["history_kind"] == "unique" and r["tasks"] == count
                  and not r["traced"]]
        task_panel[str(count)] = dict(samples=values, median=statistics.median(values))
    unchanged = source == manifest()
    summary = dict(passed=unchanged and all(x["passed"] for x in history_panel.values()),
        source_unchanged=unchanged, workers=len(rows), history_panel=history_panel,
        task_panel=task_panel, host=platform.platform(), python=sys.version,
        rows=rows, limitation="Shared-host isolated processes; traced workers excluded from timing medians. No optimization, constant-time or new-capacity claim.")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("measurement complete", summary["passed"], flush=True)
    assert summary["passed"]


if __name__ == "__main__":
    if sys.argv[1] == "--worker":
        worker(int(sys.argv[2]), bool(int(sys.argv[3])), int(sys.argv[4]), bool(int(sys.argv[5])))
    else:
        main(Path(sys.argv[1]))
