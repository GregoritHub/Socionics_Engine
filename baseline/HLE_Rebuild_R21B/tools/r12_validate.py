"""Run the delivered R11 regression suite plus the new R12 acceptance checks."""
import json
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "evidence/r12/final"
    out.mkdir(parents=True, exist_ok=True)
    results = []
    jobs = [
        ("r11_regression", ["-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]),
        ("r12_contracts", ["-m", "unittest", "discover", "-s", "tests_r12", "-t", ".", "-v"]),
        ("oig_reference", ["tools/r12_oig_reference.py"]),
        ("specification", ["tools/r12_specification.py"]),
    ]
    for name, args in jobs:
        start = time.perf_counter()
        # Publish the complete captured log only after the child has finished.
        # A success exit code alone must not hide an incomplete evidence file.
        run = subprocess.run([sys.executable] + args, cwd=ROOT, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log_path = out / (name + ".log")
        log_path.with_suffix(".tmp").write_text(run.stdout)
        log_path.with_suffix(".tmp").replace(log_path)
        expected_count = {"r11_regression": 353, "r12_contracts": 34}.get(name)
        count = re.search(r"Ran (\d+) tests?", run.stdout)
        log_complete = (expected_count is None or (count is not None
            and int(count.group(1)) == expected_count and run.stdout.rstrip().endswith("OK")))
        row = {"name": name, "command": ["python"] + args,
               "exit_code": run.returncode, "log_complete": log_complete,
               "seconds": round(time.perf_counter() - start, 6)}
        results.append(row)
        print(json.dumps(row), flush=True)
    report = {"schema": "r12-validation-v1", "jobs": results,
              "passed": all(row["exit_code"] == 0 and row["log_complete"] for row in results)}
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
