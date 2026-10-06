"""Run the predeclared U2 suite or protected inherited regressions with evidence."""
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
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []

    def startTest(self, test):
        self.started = time.perf_counter()
        self.status = "passed"
        super().startTest(test)

    def addFailure(self, test, err):
        self.status = "failed"
        super().addFailure(test, err)

    def addError(self, test, err):
        self.status = "error"
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.status = "unassessed"
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.status = "failed"
        super().addSubTest(test, subtest, err)

    def stopTest(self, test):
        self.rows.append({"test_id": test.id(), "status": self.status,
                          "seconds": time.perf_counter() - self.started})
        super().stopTest(test)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("legacy",), required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    loader = unittest.TestLoader()
    if args.stage == "legacy":
        protocol = json.loads((ROOT / "contracts/U2_Protocol_v1.json").read_text())
        suite = loader.loadTestsFromNames(protocol["legacy_regressions"]["full_modules"])
        index = json.loads((ROOT / protocol["legacy_regressions"]["index"]).read_text())
        names = [r["test_id"] for row in index["properties"] for r in row["selected_baseline_regressions"]]
        tests = list(flatten(suite)) + list(flatten(loader.loadTestsFromNames(names)))
        inherited_ids = {test.id() for test in tests}
        extra = ["tests.test_math", "tests.test_crux", "tests.test_metabolism", "tests_r145.test_integration", "tests_r14.test_choices", "tests_r14.test_isolation", "tests_r14.test_generation", "tests_r14.test_continuation", "tests.test_assessment", "tests_r15.test_compensation", "tests_r18.test_individuation", "tests_r19.test_clearance"]
        tests += list(flatten(loader.loadTestsFromNames(extra)))
    else:
        tests = list(flatten(loader.discover(str(ROOT / "tests_u2"), top_level_dir=str(ROOT))))
    tests = list({test.id(): test for test in tests}.values())
    source = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
              for parent in (ROOT / "hle_unified", ROOT / "tests_u2", BASE / "hle")
              for f in sorted(parent.glob("*.py"))}
    (args.out / "execution_source.json").write_text(json.dumps(source, indent=2) + "\n")
    start = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()
    with (args.out / "tests.log").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    summary = {"stage": args.stage, "started_utc": started_utc,
               "completed_utc": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "seconds": time.perf_counter() - start,
               "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skipped": len(result.skipped), "passed": result.wasSuccessful() and not result.skipped,
               "rows": result.rows,
               "inherited_71": len(inherited_ids), "additional_unique": len(tests)-len(inherited_ids)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
