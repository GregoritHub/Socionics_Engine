"""Sequential U13 reference/candidate measurements and unchanged budget gates."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
from evaluate_u13 import source_manifest


def geomean(values):
    return math.exp(sum(math.log(x) for x in values)/len(values))


def compare(out, protocol):
    results, gates = [], {}
    def pair(suite, kind, history):
        paths = [out/f'{suite}_{kind}_{history}_{m}'/'result.json' for m in ('reference', 'candidate')]
        return [json.loads(p.read_text()) for p in paths]
    active = []
    for kind in protocol['common']['workloads']:
        history_rows = []
        for n in protocol['common']['history']:
            r,c = pair('common', kind, n)
            ratios = {k: c[k]/r[k] for k in ('median_participant_seconds', 'restore_seconds', 'archive_bytes')}
            active.append(ratios['median_participant_seconds'])
            key = f'common:{kind}:{n}'
            gates[key+':semantic'] = r['protected'] == c['protected'] and c['exact_restore'] and c['resources']['passed'] and c['reference_passed']
            gates[key+':active'] = ratios['median_participant_seconds'] <= 1.10
            gates[key+':gzip'] = ratios['archive_bytes'] <= 1.10
            gates[key+':restore'] = ratios['restore_seconds'] <= 1.25
            history_rows.append(c)
            results.append({'suite':'common','kind':kind,'history':n,'ratios':ratios})
        gates[f'common:{kind}:history'] = history_rows[-1]['median_participant_seconds']/history_rows[0]['median_participant_seconds'] <= 2
        gates[f'common:{kind}:visits'] = history_rows[-1]['median_affected_record_visits']/history_rows[0]['median_affected_record_visits'] <= 2
    gates['common:geomean_active'] = geomean(active) <= .85
    live = []
    for kind in protocol['common']['checkpoints']:
        r,c = pair('checkpoint',kind,0)
        ratios = {k:c[k]/r[k] for k in ('live_bytes','peak_bytes','gzip_bytes','restore_seconds')}
        live.append(ratios['live_bytes']); key='checkpoint:'+kind
        gates[key+':semantic'] = r['protected'] == c['protected'] and c['exact_roundtrip'] and c['audit']['passed']
        for metric, limit in [('live_bytes',1.1),('peak_bytes',1.0),('gzip_bytes',1.1),('restore_seconds',1.25)]:
            gates[key+':'+metric] = ratios[metric] <= limit
        results.append({'suite':'checkpoint','kind':kind,'ratios':ratios})
    gates['common:geomean_live'] = geomean(live) <= .85
    native_active, native_live = [], []
    for kind in protocol['native']['workloads']:
        history_rows=[]
        for n in protocol['native']['history']:
            r,c = pair('native',kind,n)
            ratios = {k:c[k]/r[k] for k in ('median_participant_seconds','restore_seconds','gzip_bytes')}
            native_active.append(ratios['median_participant_seconds']); key=f'native:{kind}:{n}'
            gates[key+':semantic'] = r['protected']==c['protected'] and c['exact_restore'] and r['exact_restore'] and c['assessment_passed'] and r['assessment_passed']
            for metric,limit in [('median_participant_seconds',1.1),('restore_seconds',1.25),('gzip_bytes',1.1)]:
                gates[key+':'+metric] = ratios[metric] <= limit
            if c['memory']:
                for metric,limit in [('live_bytes',1.1),('peak_bytes',1.0)]:
                    ratios[metric] = c['memory'][metric]/r['memory'][metric]
                    gates[key+':'+metric] = ratios[metric] <= limit
                native_live.append(ratios['live_bytes'])
            history_rows.append(c)
            results.append({'suite':'native','kind':kind,'history':n,'ratios':ratios})
        gates[f'native:{kind}:history'] = history_rows[-1]['median_participant_seconds']/history_rows[0]['median_participant_seconds'] <= 2
        gates[f'native:{kind}:visits'] = history_rows[-1]['median_affected_record_visits']/history_rows[0]['median_affected_record_visits'] <= 2
    gates['native:geomean_active'] = geomean(native_active) <= .85
    gates['native:geomean_live'] = geomean(native_live) <= .85
    interaction_ratios=[]
    for domain in ('tool','pump'):
        r,c=pair('interaction',domain,0)
        ratio=c['median_episode_seconds']/r['median_episode_seconds']
        interaction_ratios.append(ratio)
        gates[f'interaction:{domain}:semantic']=(r['passed'] and c['passed'] and
            [s['protected'] for s in r['samples']]==[s['protected'] for s in c['samples']])
        gates[f'interaction:{domain}:time']=ratio<=1.1
        results.append({'suite':'interaction','kind':domain,'ratios':{'episode_seconds':ratio}})
    gates['interaction:geomean_time']=geomean(interaction_ratios)<=.85
    return {'schema':'hle-u13-measurements-v1','rows':results,'gates':gates,
            'geomeans':dict(common_active=geomean(active),common_live=geomean(live),
                            native_active=geomean(native_active),native_live=geomean(native_live),
                            interaction_episode=geomean(interaction_ratios)),
            'passed':all(gates.values())}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--summarize',action='store_true')
    p.add_argument('--reference-run',type=Path,
                   help='Reuse completed reference workers from this same environment, with exact reference-source checks; never reuse candidate samples.')
    args=p.parse_args(); out=args.out.resolve()
    protocol=json.loads((ROOT/'contracts/U13_Protocol_v1.json').read_text())
    if not args.summarize:
        out.mkdir(parents=True,exist_ok=False)
        before=source_manifest(); (out/'execution_source.json').write_text(json.dumps(before,indent=2)+'\n')
        previous_rows=[]
        if args.reference_run:
            previous_source=json.loads((args.reference_run/'execution_source.json').read_text())
            required=[k for k in before if k.startswith(('reference_u12/','baseline/HLE_Rebuild_R21B/hle/','contracts/'))
                      or k in ('tools/u13_benchmark.py','tools/u13_interaction_benchmark.py')]
            # Only the unchanged reference implementation is eligible. A changed
            # workload, fixture, price, protocol or reference worker is an error.
            mismatches=[k for k in required if previous_source.get(k)!=before[k]]
            if mismatches:raise ValueError('reference source changed: '+repr(mismatches))
            previous_rows=json.loads((args.reference_run/'progress.json').read_text())
        rows=[]
        cases=[('interaction',k,0) for k in ('tool','pump')]
        cases += [('common',k,n) for k in protocol['common']['workloads'] for n in protocol['common']['history']]
        cases += [('checkpoint',k,0) for k in protocol['common']['checkpoints']]
        cases += [('native',k,n) for k in protocol['native']['workloads'] for n in protocol['native']['history']]
        for suite,kind,n in cases:
            for mode in ('reference','candidate'):
                directory=out/f'{suite}_{kind}_{n}_{mode}';directory.mkdir()
                previous = None if args.reference_run is None else args.reference_run/directory.name
                if mode=='reference' and suite!='interaction' and previous is not None and (previous/'result.json').exists():
                    data=json.loads((previous/'result.json').read_text())
                    if (data['python']!=sys.version or data['platform']!=platform.platform()
                            or (data['suite'],data['kind'],data['history'],data['mode'])!=(suite,kind,n,mode)):
                        raise ValueError('reference environment or workload changed')
                    origin=next(r for r in previous_rows if (r['suite'],r['kind'],r['history'],r['mode'])==(suite,kind,n,mode))
                    if origin['exit_code']!=0:raise ValueError('failed reference cannot be reused')
                    shutil.copytree(previous,directory,dirs_exist_ok=True)
                    row={**origin,'reference_reused_from':str(previous.resolve()),
                         'reference_source_verified':True,'new_timed_samples':False}
                    rows.append(row);(out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
                    print(json.dumps(row),flush=True)
                    continue
                command=[sys.executable,str(ROOT/'tools/u13_benchmark.py'),'--suite',suite,'--mode',mode,
                         '--kind',kind,'--history',str(n),'--out',str(directory/'result.json')]
                if suite=='interaction':
                    command=[sys.executable,str(ROOT/'tools/u13_interaction_benchmark.py'),'--mode',mode,
                             '--domain',kind,'--out',str(directory/'result.json')]
                start=time.perf_counter()
                with (directory/'execution.log').open('w') as log:
                    r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                row=dict(suite=suite,kind=kind,history=n,mode=mode,command=command,
                         seconds=time.perf_counter()-start,exit_code=r.returncode)
                rows.append(row); (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(json.dumps(row),flush=True)
                if r.returncode: return r.returncode
        same=before==source_manifest()
        (out/'source_check.json').write_text(json.dumps({'unchanged':same})+'\n')
        if not same:return 1
    result=compare(out,protocol)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'geomeans':result['geomeans'],
                      'failed':[k for k,v in result['gates'].items() if not v]}),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
