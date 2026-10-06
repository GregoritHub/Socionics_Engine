"""Reproduce U2 acceptance, selected legacy regressions and raw witnesses."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def source_manifest():
    files = list((ROOT / "hle_unified").glob("*.py")) + list((ROOT / "tests_u2").glob("*.py"))
    files += [ROOT / "tools" / p for p in ("evaluate_u2.py", "u2_witness.py", "reproduce_u2.py")]
    files += [ROOT / "contracts" / p for p in ("U2_Protocol_v1.json", "U2_Protocol_v1.sha256", "Legacy_Adapter_Scope_v1.json")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = source_manifest()
    (out / "execution_source.json").write_text(json.dumps(before, indent=2) + "\n")
    rows = []
    jobs = [
        ("baseline_before", [sys.executable, str(ROOT / "tools/verify_baseline.py"), "--out", str(out / "baseline_before.json")]),
        ("u2", [sys.executable, str(ROOT / "tools/evaluate_u2.py"), "--stage", "u2", "--out", str(out / "u2")]),
        ("legacy", [sys.executable, str(ROOT / "tools/evaluate_u2.py"), "--stage", "legacy", "--out", str(out / "legacy")]),
        ("witnesses", [sys.executable, str(ROOT / "tools/u2_witness.py"), "--out", str(out / "witnesses")]),
        ("baseline_after", [sys.executable, str(ROOT / "tools/verify_baseline.py"), "--out", str(out / "baseline_after.json")]),
    ]
    for name, argv in jobs:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
        (out / (name + ".log")).write_text(result.stdout + result.stderr)
        rows.append({"stage": name, "exit_code": result.returncode})
        (out / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(rows[-1]), flush=True)
    unchanged = source_manifest() == before
    result = {"schema": "hle-unified-u2-reproduction-v1", "rows": rows,
              "execution_source_unchanged": unchanged,
              "passed": unchanged and all(row["exit_code"] == 0 for row in rows)}
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
