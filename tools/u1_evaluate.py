"""Reproduce U1 baseline checks without modifying the frozen runtime."""
import argparse
from datetime import datetime, timezone
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def check_engine(engine, spec):
    actual = {name: sha(engine / name) for name in spec["runtime_files"]}
    if actual != spec["runtime_files"]:
        raise ValueError("runtime differs from frozen baseline")

def validation(engine, out, spec):
    jobs = [
        ("inherited", [sys.executable, "tools/r21a_validate.py", "--out", str(out / "inherited")], 893),
        ("r21b", [sys.executable, "-m", "unittest", "discover", "-s", "tests_r21b", "-t", ".", "-v"], 19),
    ]
    rows = []
    for name, argv, expected in jobs:
        row = {"name": name, "argv": argv, "expected": expected, "started_utc": datetime.now(timezone.utc).isoformat()}
        save(out / (name + ".invocation.json"), row)
        start = time.perf_counter()
        with (out / (name + ".log")).open("w") as stream:
            result = subprocess.run(argv, cwd=engine, stdout=stream, stderr=subprocess.STDOUT,
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        text = (out / (name + ".log")).read_text()
        if name == "inherited":
            inner = json.loads((out / "inherited/summary.json").read_text())
            observed, passed = inner["total"], inner["passed"]
        else:
            match = re.search(r"Ran (\d+) tests", text)
            observed = int(match.group(1)) if match else 0
            passed = text.rstrip().endswith("OK")
        row.update(exit_code=result.returncode, observed=observed,
                   passed=result.returncode == 0 and passed and observed == expected,
                   seconds=time.perf_counter() - start, log_sha256=sha(out / (name + ".log")))
        rows.append(row)
        save(out / "progress.json", {"rows": rows})
        print(json.dumps(row), flush=True)
    result = {"schema": "u1-validation-v1", "rows": rows, "distinct_tests": sum(r["observed"] for r in rows),
              "passed": len(rows) == 2 and all(r["passed"] for r in rows)}
    save(out / "summary.json", result)
    return result

def behavior(engine, out, spec):
    from r21b_evidence import execute_case
    rows = []
    matches = []
    for case in spec["paired_cases"] + spec["controls"]:
        independent = case.get("mode", "reuse") == "reuse"
        row = execute_case((case, str(out), independent))
        original = engine / "evidence/r21b/development" / (row["name"] + ".json")
        fresh = json.loads((out / (row["name"] + ".json")).read_text())
        if not original.is_file() and not independent:
            original = engine / "evidence/r21b/controls" / (row["name"] + ".json")
        if original.is_file():
            retained = json.loads(original.read_text())
            for side, trace in fresh["traces"].items():
                old = retained["traces"].get(side)
                matches.append({"case": row["name"], "side": side,
                                "retained_path": str(original.relative_to(engine)),
                                "fresh_sha256": trace["sha256"],
                                "retained_sha256": None if old is None else old["sha256"],
                                "equal": old is not None and trace["sha256"] == old["sha256"]})
        elif independent:
            matches.append({"case": row["name"], "side": "missing", "equal": False})
        if row["regime"] == "inadequate":
            # Audit both actual retained constructions, not just a completion flag.
            for side in ("assessment", "independent_assessment"):
                audit = fresh[side]
                row[side + "_integrity"] = audit["integrity_passed"]
        rows.append(row)
        save(out / "progress.json", {"rows": rows, "trace_matches": matches})
        print(json.dumps({k: v for k, v in row.items() if k not in ("work", "paid_reuse")}), flush=True)
        gc.collect()
    paired = [r for r in rows if r["independent_executed"]]
    positive = [r for r in paired if r["regime"] != "inadequate"]
    zero = [r for r in paired if r["regime"] == "inadequate"]
    controls = {r["mode"]: r for r in rows if not r["independent_executed"]}
    normal = next(r for r in paired if r["name"] == "iee_12_constrained_feasible")
    def worker_cost(row):
        worker = next(key for key in row["work"] if key.endswith(":worker"))
        return next(iter(row["work"][worker].values()))
    control_ok = (controls["no_reuse"]["candidate_success"]
                  and not controls["legacy_cost"]["candidate_success"]
                  and controls["legacy_cost"]["resource_stop"] is not None
                  and all(r["integrity_passed"] for r in controls.values())
                  and worker_cost(controls["no_reuse"]) > worker_cost(normal))
    paired_matches = [r for r in matches if not any(r["case"].endswith("." + m) for m in controls)]
    result = {"schema": "u1-behavior-v1", "release_evaluation": False,
              "planned_candidates": 6, "executed_candidates": len(paired),
              "independent_executions": len(paired), "positive_per_side": len(positive),
              "zero_per_side": len(zero), "controls": len(controls), "rows": rows,
              "trace_matches": matches, "reserved_release_seeds_used": [],
              "worker_cost_controls": {m: worker_cost(r) for m, r in controls.items()} | {"reuse": worker_cost(normal)},
              "passed": len(paired) == 6 and len(positive) == 4 and len(zero) == 2
              and all(r["integrity_passed"] and r["independent_integrity_passed"] and r["same_scope"] and not r["error"] for r in paired)
              and all(r["feasibility_passed"] and r["clearance_passed"] == 13 and r["opportunities"] == 100 and r["unfinished"] == 0 for r in positive)
              and all(not r["candidate_success"] and not r["independent_success"] and r["opportunities"] == 0 for r in zero)
              and len(paired_matches) == 12 and all(r["equal"] for r in paired_matches)
              and control_ok}
    save(out / "summary.json", result)
    return result

def checkpoint_case(engine, out, name):
    from hle.closure import ClosureWorld
    from hle.world_records import Tick
    from r21b_work_audit import audit_paid_work
    path = engine / "evidence/r21b/development" / (name + ".checkpoint.json.gz")
    with gzip.open(path, "rt") as stream:
        original = stream.read()
    before = time.perf_counter()
    world = ClosureWorld.restore(original)
    restore_seconds = time.perf_counter() - before
    before = time.perf_counter()
    encoded = world.checkpoint()
    serialization_seconds = time.perf_counter() - before
    before = time.perf_counter()
    compressed = gzip.compress(encoded.encode(), mtime=0)
    compression_seconds = time.perf_counter() - before
    audit = audit_paid_work(world)
    contract = world._journal[1].command
    before_wallets = {a.key: {"energy": w.energy, "time": w.time} for a, w in world._wallets.items()}
    expected_world = ClosureWorld.restore(encoded)
    command = Tick("u1:checkpoint-continuation:" + name)
    world.execute(command)
    expected_world.execute(command)
    continuation_equal = world.checkpoint() == expected_world.checkpoint()
    after_wallets = {a.key: {"energy": w.energy, "time": w.time} for a, w in world._wallets.items()}
    del world, expected_world
    gc.collect()
    # Isolate memory measurement from timed restoration and from the checkpoint text.
    tracemalloc.start()
    measured_world = ClosureWorld.restore(encoded)
    live, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {"schema": "u1-v4-checkpoint-v1", "name": name,
              "source_path": str(path.relative_to(engine)), "source_sha256": sha(path),
              "original_exact_roundtrip": original == encoded,
              "serialized_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
              "raw_bytes": len(encoded.encode()), "gzip_bytes": len(compressed),
              "gzip_level": 9, "serialization_seconds": serialization_seconds,
              "restore_seconds": restore_seconds, "compression_seconds": compression_seconds,
              "traced_restored_world_live_bytes": live, "traced_restore_peak_bytes": peak,
              "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "memory_scope": "Python allocations since immediately before restoration; checkpoint text allocated beforehand; RSS is process high-water mark",
              "protocol_id": contract.protocol_id, "protocol_sha256": contract.protocol_sha256,
              "wallets_before": before_wallets, "wallets_after_tick": after_wallets,
              "continuation_equal": continuation_equal, "paid_work_audit": audit,
              "continuation_scope": "identical explicit Tick on both restored worlds; paid partial-job continuation is separately covered by the inherited tests",
              "passed": original == encoded and continuation_equal and audit["passed"] and before_wallets == after_wallets}
    save(out / (name + ".json"), result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("paid_work_audit", "wallets_before", "wallets_after_tick")}), flush=True)
    return result

def checkpoints(engine, out, spec):
    rows = []
    for name in ("iee_12_constrained_feasible", "sli_11_constrained_feasible"):
        # Each memory/CPU observation gets a separate process.
        argv = [sys.executable, str(Path(__file__).resolve()), "--engine", str(engine),
                "--out", str(out), "--stage", "checkpoint-one", "--name", name]
        run = subprocess.run(argv, cwd=ROOT)
        path = out / (name + ".json")
        rows.append({"name": name, "exit_code": run.returncode,
                     "result": json.loads(path.read_text()) if path.exists() else None})
    result = {"schema": "u1-checkpoints-v1", "rows": rows,
              "passed": all(r["exit_code"] == 0 and r["result"] and r["result"]["passed"] for r in rows)}
    save(out / "summary.json", result)
    return result

def performance(engine, out, spec):
    argv = [sys.executable, "tools/r21_performance.py", "--out", str(out)]
    save(out / "invocation.json", {"argv": argv, "scope": spec["performance_measurements"]["legacy_active_inactive"]})
    with (out / "run.log").open("w") as stream:
        run = subprocess.run(argv, cwd=engine, stdout=stream, stderr=subprocess.STDOUT)
    path = out / "summary.json"
    report = json.loads(path.read_text()) if path.is_file() else None
    valid = (report is not None and len(report["rows"]) == 6
             and all(r["exact_restore"] and r["reference_passed"] and r["resources"]["passed"] for r in report["rows"]))
    result = {"schema": "u1-performance-measurement-v1", "exit_code": run.returncode,
              "inherited_performance_gate_passed": None if report is None else report["passed"],
              "measurement_valid": valid, "passed": valid,
              "scope": spec["performance_measurements"]["legacy_active_inactive"],
              "renewed_r21c_acceptance": False}
    save(out / "u1_measurement_status.json", result)
    print(json.dumps(result), flush=True)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stage", choices=("validation", "behavior", "performance", "checkpoints", "checkpoint-one"), required=True)
    parser.add_argument("--name")
    args = parser.parse_args()
    engine, out = args.engine.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / "contracts/U1_Protocol_v1.json").read_text())
    check_engine(engine, spec)
    sys.path[:0] = [str(engine / "tools"), str(engine)]
    if args.stage == "checkpoint-one":
        result = checkpoint_case(engine, out, args.name)
    else:
        save(out / "execution_source.json", {"runtime_sha256": spec["runtime_sha256"],
            "wrapper_sha256": sha(Path(__file__)), "protocol_sha256": sha(ROOT / "contracts/U1_Protocol_v1.json"),
            "python": sys.version, "platform": platform.platform(),
            "started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv})
        result = globals()[args.stage](engine, out, spec)
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

