"""Versioned C1 evaluation; does not amend or reuse the frozen U14 decision."""
import argparse
import hashlib
import json
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from evaluate_u2 import EvidenceResult, flatten


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--inherited", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    paths = list((ROOT / "hle_unified").glob("*.py")) + list((ROOT / "tests_c1").glob("*.py"))
    paths += [ROOT / "contracts/C1_Protocol_v1.json"]
    manifest = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(paths)}
    (args.out / "execution_source.json").write_text(json.dumps(manifest, indent=2) + "\n")
    directories = [ROOT / "tests_c1"]
    if args.inherited:
        directories += [ROOT / f"tests_u{i}" for i in range(2, 15)]
    tests = []
    for directory in directories:
        tests.extend(flatten(unittest.defaultTestLoader.discover(str(directory), top_level_dir=str(ROOT))))
    tests = list({t.id(): t for t in tests}.values())
    start = time.perf_counter()
    with (args.out / "tests.log").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    unchanged = all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == digest for f, digest in manifest.items())
    summary = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), seconds=time.perf_counter()-start, source_unchanged=unchanged,
        rows=result.rows, passed=result.wasSuccessful() and not result.skipped and unchanged)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k:v for k,v in summary.items() if k != "rows"}), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
