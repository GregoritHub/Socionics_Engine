"""Resume a frozen-source evaluation from explicitly recorded per-method passes.

This does not relabel a partial run as a clean single process. Prefix methods
have log evidence but no retained individual timing. Remaining results are
written after every method so a runner disconnect cannot lose completed work.
"""
import argparse,hashlib,json,re,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from evaluate_u2 import EvidenceResult,flatten


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    manifest=json.loads((a.out/'execution_source.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items()),'source changed since initial run'
    dirs=[ROOT/'tests_c4',ROOT/'tests_c3',ROOT/'tests_c2',ROOT/'tests_c1',*[ROOT/f'tests_u{i}' for i in range(2,15)]]
    cases={}
    for directory in dirs:
        for t in flatten(unittest.defaultTestLoader.discover(str(directory),top_level_dir=str(ROOT))):cases[t.id()]=t
    prior={m.group(1):dict(test_id=m.group(1),status='passed',seconds=None,evidence='tests.log')
           for line in (a.out/'tests.log').read_text().splitlines()
           if (m:=re.fullmatch(r'test\w+ \(([^)]+)\) \.\.\. ok',line))}
    assert set(prior)<=set(cases)
    continuing=a.out/'continuation_rows.json'
    if continuing.exists():prior.update({r['test_id']:r for r in json.loads(continuing.read_text())})
    original_count=len(prior)
    script_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (a.out/'continuation_source.json').write_text(json.dumps({'tools/resume_c4_evaluation.py':script_hash},indent=2)+'\n')
    print(f'Retained {original_count} recorded methods; {len(cases)-original_count} remain.',flush=True)
    start=time.perf_counter()
    with (a.out/'continuation.log').open('a') as log:
        for name,test in cases.items():
            if name in prior:continue
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite([test]))
            log.flush();assert len(result.rows)==1
            row=dict(result.rows[0],evidence='continuation.log');prior[name]=row
            continuing.write_text(json.dumps(list(prior.values()),indent=2)+'\n')
            print(f'{len(prior)}/{len(cases)} {row["status"]}: {name}',flush=True)
    rows=[prior[name] for name in cases]
    unchanged=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    summary=dict(tests=len(rows),failures=sum(r['status']=='failed' for r in rows),errors=sum(r['status']=='error' for r in rows),
        skipped=sum(r['status']=='skipped' for r in rows),rows=rows,source_unchanged=unchanged,
        passed=unchanged and all(r['status']=='passed' for r in rows),seconds=None,continuation_seconds=time.perf_counter()-start,
        run_form='Interrupted frozen-source run plus explicitly recorded continuation; not one uninterrupted process',
        prefix_recorded_methods=original_count,continuation_methods=len(rows)-original_count)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
    if not summary['passed']:raise SystemExit(1)

if __name__=='__main__':main()
