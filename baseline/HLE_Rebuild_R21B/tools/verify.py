#!/usr/bin/env python3
"""Run rebuild tests and retain every per-test outcome; standard library only."""
import argparse
import hashlib
import json
import platform
import sys
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle import MILESTONE


class Results(unittest.TextTestResult):
    def startTest(self,test):
        self.began=time.perf_counter()
        super().startTest(test)

    def record(self,test,status,detail=None):
        self.records.append({"test":test.id(),"status":status,
            "rules":list(getattr(getattr(test,test._testMethodName),"rule_ids",())),
            "seconds":time.perf_counter()-self.began,"detail":detail})

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.records=[]

    def addSuccess(self,test):
        self.record(test,"passed");super().addSuccess(test)

    def addFailure(self,test,error):
        self.record(test,"failed",self._exc_info_to_string(error,test));super().addFailure(test,error)

    def addError(self,test,error):
        self.record(test,"error",self._exc_info_to_string(error,test));super().addError(test,error)

    def addSkip(self,test,reason):
        self.record(test,"skipped",reason);super().addSkip(test,reason)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"),top_level_dir=str(ROOT))
    started=time.perf_counter()
    with (args.output/"tests.log").open("w") as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Results).run(suite)
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for folder in ('hle','tests','tools','docs') for p in sorted((ROOT/folder).rglob('*'))
                   if p.is_file() and '__pycache__' not in p.parts}
    payload={"milestone":MILESTONE,"python":sys.version,"platform":platform.platform(),
             "machine":platform.machine(),"command":sys.argv,"isolated":bool(sys.flags.isolated),
             "acceptance_plan_sha256":hashlib.sha256((ROOT/"docs/acceptance_plan.json").read_bytes()).hexdigest(),
             "seconds":time.perf_counter()-started,"tests_run":result.testsRun,
             "failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),
             "successful":result.wasSuccessful() and not result.skipped,"source_hashes":source_hashes,"tests":result.records}
    (args.output/"results.json").write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps({k:v for k,v in payload.items() if k not in ("tests","command","python","source_hashes")}))
    return 0 if payload["successful"] else 1


if __name__=="__main__":raise SystemExit(main())
