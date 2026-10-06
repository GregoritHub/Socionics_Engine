"""Run declared U8 tests and retain every result, including development failures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "baseline/HLE_Rebuild_R21B"
sys.path[:0] = [str(ROOT), str(BASE)]
sys.dont_write_bytecode = True
from evaluate_u2 import EvidenceResult, flatten


def source_manifest():
    paths = [p for directory in ("hle_unified", "tests_u8", "tests_u7", "tests_u6", "tests_u5", "tests_u4", "tests_u3", "tests_u2", "tools")
             for p in (ROOT / directory).glob("*.py")]
    paths += list((BASE / "hle").glob("*.py"))
    paths += [p for d in BASE.glob("tests*") for p in d.glob("*.py")]
    for stage in ("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"):
        paths += list((ROOT / "contracts").glob(stage + "_Protocol_v1.*"))
    paths += [ROOT / "contracts/U7_Regression_Panel_v1.json", ROOT / "contracts/U8_Regression_Panel_v1.json"]
    paths += [ROOT / "contracts/Protection_Regression_Index_v1.json", ROOT / "contracts/New_Engine_Acceptance_v1.json"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    before = source_manifest()
    (out / "execution_source.json").write_text(json.dumps(before, indent=2) + "\n")
    tests = list(flatten(unittest.TestLoader().discover(str(ROOT / "tests_u8"), top_level_dir=str(ROOT))))
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    with (out / "tests.log").open("w") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    protocol = ROOT / "contracts/U8_Protocol_v1.json"
    protocol_ok = hashlib.sha256(protocol.read_bytes()).hexdigest() == (ROOT / "contracts/U8_Protocol_v1.sha256").read_text().strip()
    summary = {"schema": "hle-unified-u8-tests-v1", "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "command": [sys.executable, *sys.argv], "seconds": time.perf_counter() - start,
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "protocol_hash_matches": protocol_ok,
        "execution_source_unchanged": before == source_manifest(), "rows": result.rows}
    summary["passed"] = result.wasSuccessful() and not result.skipped and protocol_ok and summary["execution_source_unchanged"]
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
