"""Prospective stronger maintenance-exhaustion controls; original failures remain."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from u14_support import digest,write_json,save_gzip,verify_freeze,time


def verify_supplement():
    verify_freeze()
    manifest=json.loads((ROOT/'U14_Supplement_Manifest_v1.json').read_text())
    if any(digest((ROOT/k).read_bytes())!=v for k,v in manifest.items()):raise ValueError('supplement changed after freeze')
    return digest(json.dumps(manifest,sort_keys=True))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--case',type=int);p.add_argument('--jobs',type=int,default=2,choices=range(1,7))
    a=p.parse_args();identity=verify_supplement()
    protocol=json.loads((ROOT/'supplement/protocol_v2.json').read_text());cases=protocol['cases']
    if a.case is not None:
        from population_exhaustion import run_case
        case=cases[a.case];start=time.perf_counter()
        try:
            result=run_case(case,a.out);verify_supplement()
            result.update(source_identity=identity,seconds=time.perf_counter()-start)
            write_json(a.out/'summary.json',result);return 0 if result['passed'] else 1
        except Exception as exc:
            a.out.mkdir(parents=True,exist_ok=True)
            (a.out/'exception.txt').write_text(traceback.format_exc())
            tb=exc.__traceback__;engine=None
            while tb:
                candidate=tb.tb_frame.f_locals.get('e')
                if candidate is not None and hasattr(candidate,'checkpoint'):engine=candidate
                tb=tb.tb_next
            if engine is not None:save_gzip(a.out/'failed.checkpoint.json.gz',engine.checkpoint())
            write_json(a.out/'summary.json',dict(case=case,passed=False,exception=repr(exc),source_identity=identity))
            traceback.print_exc();return 1
    a.out.mkdir(parents=True,exist_ok=False)
    write_json(a.out/'protocol.json',protocol)
    def execute(i):
        case=cases[i];path=a.out/case['id']
        command=[sys.executable,str(Path(__file__).resolve()),'--out',str(path),'--case',str(i)]
        with (a.out/(case['id']+'.log')).open('w') as log:run=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result=json.loads((path/'summary.json').read_text())
        return dict(id=case['id'],passed=result['passed'] and run.returncode==0,exit_code=run.returncode,
                    successes=result.get('successes'),seconds=result.get('seconds'))
    done={}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures={pool.submit(execute,i):i for i in range(len(cases))}
        for future in as_completed(futures):
            done[futures[future]]=future.result();rows=[done[i] for i in sorted(done)]
            write_json(a.out/'progress.json',rows);print(json.dumps(future.result()),flush=True)
    result=dict(passed=len(done)==len(cases) and all(r['passed'] for r in done.values()),
        source_identity=identity,source_unchanged=verify_supplement()==identity,rows=[done[i] for i in sorted(done)],planned=len(cases),executed=len(done))
    write_json(a.out/'summary.json',result);return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
