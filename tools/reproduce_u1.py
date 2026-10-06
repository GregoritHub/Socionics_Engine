"""Create an isolated execution copy and run the declared U1 reproduction."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True,
                        help="New directory for execution copy and evidence; must not already exist.")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    verified = subprocess.run([sys.executable, str(ROOT / "tools/verify_baseline.py"),
                               "--out", str(out / "frozen_baseline.json")])
    if verified.returncode:
        return verified.returncode
    engine = out / "engine"
    shutil.copytree(ROOT / "baseline/HLE_Rebuild_R21B", engine)
    rows = []
    # Sequential execution prevents task-owned validation work from contaminating timing.
    for stage in ("validation", "behavior", "performance", "checkpoints"):
        target = out / "evidence" / stage
        argv = [sys.executable, str(ROOT / "tools/u1_evaluate.py"), "--engine", str(engine),
                "--out", str(target), "--stage", stage]
        row = {"stage": stage, "argv": argv, "started_utc": datetime.now(timezone.utc).isoformat()}
        result = subprocess.run(argv, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        row["exit_code"] = result.returncode
        rows.append(row)
        (out / "reproduction_progress.json").write_text(json.dumps({"rows": rows}, indent=2) + "\n")
        if stage == "behavior":
            audit_argv = [sys.executable, str(ROOT / "tools/check_zero_traces.py"),
                          "--traces", str(target), "--out", str(out / "evidence/zero_budget_raw_check.json")]
            audit = subprocess.run(audit_argv)
            rows.append({"stage": "zero_budget_raw_check", "argv": audit_argv, "exit_code": audit.returncode})
    result = {"schema": "u1-reproduction-v1", "rows": rows,
              "passed": all(row["exit_code"] == 0 for row in rows)}
    (out / "reproduction_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
