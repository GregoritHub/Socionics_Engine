"""Reproduce the recovered R11 and crossing baseline; keep historical data separate."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def compare_snapshots(out):
    comparisons = []
    for name, fresh in [("crossing", out / "crossing.json"),
                        ("r10", ROOT / "baseline/crossing/results/r10.json"),
                        ("r11", ROOT / "baseline/crossing/results/r11.json")]:
        snapshot = ROOT / ("baseline/crossing/results/" + name + ".json.gz")
        before = gzip.decompress(snapshot.read_bytes())
        after = fresh.read_bytes()
        old, new = json.loads(before), json.loads(after)
        raw_equal = old == new
        normalized_fields = []
        if name == "r11":
            # The intentionally failing historical probe includes its absolute
            # script filename. Preserve raw bytes; normalize only that filename.
            pattern = r'(?m)^  File "[^"\n]*/sources/active_element_probe_original\.py"'
            for data in (old, new):
                data["active_probe"]["unmodified_stderr"] = re.sub(pattern,
                    '  File "<source_root>/sources/active_element_probe_original.py"',
                    data["active_probe"]["unmodified_stderr"])
            normalized_fields = ["active_probe.unmodified_stderr: absolute script path only"]
        comparisons.append({"name": name, "byte_identical": after == before,
            "json_identical": raw_equal, "relocation_normalized_identical": old == new,
            "normalization": normalized_fields,
            "fresh_sha256": hashlib.sha256(after).hexdigest(),
            "historical_sha256": hashlib.sha256(before).hexdigest()})
    return comparisons


def main():
    out = ROOT / "evidence/r12/baseline"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("r11_regression", ROOT, ["-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]),
        ("source_verification", ROOT / "baseline/crossing", ["verify_sources.py"]),
        ("crossing_panel", ROOT / "baseline/crossing", ["run_crossing.py", "--out", str(out / "crossing.json")]),
        ("study_panel", ROOT / "baseline/crossing", ["run_studies.py", "--out", "results"]),
        ("crossing_and_study_tests", ROOT / "baseline/crossing", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("recurrence_fidelity", ROOT / "recovered_probes/recurrence", ["-m", "unittest", "probe.test_recurrence", "-v"]),
        ("developmental_fidelity", ROOT / "recovered_probes/developmental", ["-m", "unittest", "devprobe.test_engine", "-v"]),
        ("meaning_fidelity", ROOT / "recovered_probes/meaning", ["-m", "unittest", "meaningprobe.test_engine", "-v"]),
    ]
    results = []
    for name, cwd, args in jobs:
        start = time.perf_counter()
        result = subprocess.run([sys.executable] + args, cwd=cwd, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        log_path = out / (name + ".log")
        log_path.with_suffix(".tmp").write_text(result.stdout)
        log_path.with_suffix(".tmp").replace(log_path)
        expected = {"r11_regression": 353, "crossing_and_study_tests": 26,
                    "recurrence_fidelity": 14, "developmental_fidelity": 14,
                    "meaning_fidelity": 18}.get(name)
        count = re.search(r"Ran (\d+) tests?", result.stdout)
        log_complete = expected is None or (count is not None
            and int(count.group(1)) == expected and result.stdout.rstrip().endswith("OK"))
        row = {"name": name, "cwd": str(cwd.relative_to(ROOT)) or ".",
               "command": ["python"] + args, "exit_code": result.returncode, "log_complete": log_complete,
               "seconds": round(time.perf_counter() - start, 6)}
        results.append(row)
        print(json.dumps(row), flush=True)
    comparisons = compare_snapshots(out)
    summary = {"schema": "r12-baseline-v1", "python": sys.version,
               "platform": platform.platform(), "jobs": results, "snapshot_comparisons": comparisons,
               "passed": all(r["exit_code"] == 0 and r["log_complete"] for r in results)
                         and all(c["relocation_normalized_identical"] for c in comparisons)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
