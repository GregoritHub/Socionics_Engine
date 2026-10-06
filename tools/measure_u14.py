"""Sequential release timing confirmation. Start after all other work is idle."""
import argparse
import math
import subprocess
from u14_support import *


def gm(values):return math.exp(sum(math.log(v) for v in values)/len(values))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    identity=verify_freeze();a.out.mkdir(parents=True,exist_ok=a.resume)
    if a.resume:
        if json.loads((a.out/'execution_source.json').read_text())!=source_manifest():raise ValueError('measurement source changed')
    else:write_json(a.out/'execution_source.json',source_manifest())
    cases=[('interaction','tool',0),('interaction','pump',0),('common','tick',1000),('common','completed_inspection',1000),
           ('native','shared',100),('native','shared',1000),('native','shared',10000),('native','unique',1000),('native','dense',1000)]
    rows=[];gates={};active={'common':[],'native':[],'interaction':[]};live=[];shared=[]
    for suite,kind,n in cases:
        pair=[]
        for mode in ('reference','candidate'):
            directory=a.out/f'{suite}_{kind}_{n}_{mode}'
            result=directory/'result.json'
            if not (a.resume and result.exists()):
                directory.mkdir(exist_ok=False)
                command=[sys.executable,str(ROOT/'tools/u13_benchmark.py'),'--suite',suite,'--mode',mode,'--kind',kind,'--history',str(n),'--out',str(result)]
                if suite=='interaction':command=[sys.executable,str(ROOT/'tools/u13_interaction_benchmark.py'),'--mode',mode,'--domain',kind,'--out',str(result)]
                start=time.perf_counter()
                with (directory/'execution.log').open('w') as log:proc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                write_json(directory/'command.json',dict(command=command,seconds=time.perf_counter()-start,exit_code=proc.returncode))
                if proc.returncode:raise RuntimeError('measurement worker failed: '+directory.name)
            pair.append(json.loads(result.read_text()))
        r,c=pair;key=f'{suite}:{kind}:{n}'
        if suite=='interaction':
            ratio=c['median_episode_seconds']/r['median_episode_seconds']
            gates[key+':semantic']=r['passed'] and c['passed'] and [s['protected'] for s in r['samples']]==[s['protected'] for s in c['samples']]
            ratios={'active':ratio}
        else:
            ratio=c['median_participant_seconds']/r['median_participant_seconds']
            ratios={'active':ratio,'restore':c['restore_seconds']/r['restore_seconds']}
            gates[key+':semantic']=r['protected']==c['protected'] and c['exact_restore']
            if suite=='native':
                gates[key+':audit']=c['assessment_passed'] and r['assessment_passed']
                ratios['gzip']=c['gzip_bytes']/r['gzip_bytes']
                if c['memory']:
                    ratios['live']=c['memory']['live_bytes']/r['memory']['live_bytes']
                    ratios['peak']=c['memory']['peak_bytes']/r['memory']['peak_bytes']
                    live.append(ratios['live']);gates[key+':live']=ratios['live']<=1.10;gates[key+':peak']=ratios['peak']<=1.0
                if kind=='shared':shared.append(c)
            else:
                gates[key+':audit']=c['resources']['passed'] and c['reference_passed']
                ratios['gzip']=c['archive_bytes']/r['archive_bytes']
            gates[key+':restore']=ratios['restore']<=1.25;gates[key+':gzip']=ratios['gzip']<=1.10
        gates[key+':active']=ratio<=1.10;active[suite].append(ratio)
        rows.append(dict(suite=suite,kind=kind,history=n,ratios=ratios))
        write_json(a.out/'progress.json',rows);print(json.dumps(rows[-1]),flush=True)
    means={k:gm(v) for k,v in active.items()};means['native_live']=gm(live)
    for k,v in means.items():gates[k+':geomean']=v<=.85
    gates['shared:inactive_time_growth']=shared[-1]['median_participant_seconds']/shared[0]['median_participant_seconds']<=2
    gates['shared:inactive_visits_growth']=shared[-1]['median_affected_record_visits']/shared[0]['median_affected_record_visits']<=2
    same=verify_freeze()==identity
    result=dict(passed=all(gates.values()) and same,gates=gates,rows=rows,geomeans=means,source_identity=identity,source_unchanged=same,
        scope='Fresh bounded confirmation; full U13 measurement panel retained as prior evidence with exact source verification.')
    write_json(a.out/'summary.json',result);print(json.dumps(dict(passed=result['passed'],geomeans=means,failed=[k for k,v in gates.items() if not v])),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
