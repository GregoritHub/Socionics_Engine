"""Freeze execution hashes; reproduce U5, U3, U2 and the protected legacy gates."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
from evaluate_u5 import source_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = source_manifest()
    (out / "execution_source.json").write_text(json.dumps(before, indent=2) + "\n")
    rows = []
    jobs = [
        ("baseline_before", ["verify_baseline.py", "--out", str(out / "baseline_before.json")]),
        ("u5", ["evaluate_u5.py", "--out", str(out / "u5")]),
        ("u4", ["evaluate_u4.py", "--out", str(out / "u4")]),
        ("u3", ["evaluate_u3.py", "--out", str(out / "u3")]),
        ("u2", ["evaluate_u2.py", "--stage", "u2", "--out", str(out / "u2")]),
        ("legacy", ["evaluate_u5_legacy.py", "--stage", "legacy", "--out", str(out / "legacy")]),
        ("u2_witnesses", ["u2_witness.py", "--out", str(out / "u2_witnesses")]),
        ("u3_witnesses", ["u3_witness.py", "--out", str(out / "u3_witnesses"), "--u2-checkpoint", str(out / "u2_witnesses/native.checkpoint.json")]),
        ("u4_witnesses", ["u4_witness.py", "--out", str(out / "u4_witnesses")]),
        ("u5_witnesses", ["u5_witness.py", "--out", str(out / "u5_witnesses")]),
        ("baseline_after", ["verify_baseline.py", "--out", str(out / "baseline_after.json")]),
    ]
    for name, args in jobs:
        command = [sys.executable, str(ROOT / "tools" / args[0]), *args[1:]]
        started = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
        (out / (name + ".log")).write_text(result.stdout + result.stderr)
        rows.append({"stage": name, "command": command, "started_utc": started,
            "completed_utc": datetime.now(timezone.utc).isoformat(), "seconds": time.perf_counter() - start, "exit_code": result.returncode})
        (out / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps({k: rows[-1][k] for k in ("stage", "seconds", "exit_code")}), flush=True)
    unchanged = before == source_manifest()
    summary = {"schema": "hle-unified-u5-reproduction-v1", "rows": rows,
        "execution_source_unchanged": unchanged, "passed": unchanged and all(r["exit_code"] == 0 for r in rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
