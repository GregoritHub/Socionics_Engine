"""Run and retain all 480 frozen R21 episodes, including unfinished episodes."""
import argparse,gc,gzip,hashlib,json,platform,sys,time,traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r21_workloads import run_episode,replay_witness,trace_digest
from r21_reference import audit
from hle.codec import dumps

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def trace(path,w):
    h=hashlib.sha256();size=0
    with gzip.open(path,'wt',compresslevel=6) as f:
        for tx in w._journal:
            line=dumps(tx)+'\n';f.write(line);h.update(line.encode());size+=len(line.encode())
    return {'path':path.name,'sha256':h.hexdigest(),'uncompressed_bytes':size,
            'compressed_bytes':path.stat().st_size,'transactions':len(w._journal)}

def case(out,tim,seed,regime,budget):
    name=f'{tim}_{seed}_{regime}';clock=time.perf_counter()
    w,meta=run_episode(tim,seed,budget)
    meta['regime']=regime
    analysis=audit(w,meta)
    r=replay_witness(w)
    witness={'exact_transaction_replay':r._journal==w._journal,
        'successful_policy':meta['cleared'] and analysis['sustained']['passed'],
        'status':r.clearance_report()['status'],
        'scope':'separately executed same legal command policy; failed witness does not prove impossibility'}
    del r;gc.collect()
    evidence=trace(out/(name+'.transactions.jsonl.gz'),w)
    expected=(meta['resource_stop'] is not None and not meta['cleared']) if regime=='inadequate' else (
        meta['cleared'] and meta['status']=='cleared_in_scope' and analysis['sustained']['passed'] and witness['successful_policy'])
    passed=expected and analysis['raw_clearance']['passed'] and analysis['resources']['passed'] and witness['exact_transaction_replay'] and 'error' not in meta
    row={'name':name,**meta,'assessment':analysis,'feasibility':witness,'trace':evidence,
         'passed':passed,'seconds':time.perf_counter()-clock}
    save(out/(name+'.json'),row)
    compact={k:row[k] for k in ('name','tim','seed','regime','budget','history','stage','cleared','resource_stop','status','events','work','passed','seconds')}
    compact.update(eligible=analysis['sustained']['eligible'],changes=analysis['sustained']['demand_changes'],
        integrity=analysis['raw_clearance']['passed'] and analysis['resources']['passed'],
        exact_replay=witness['exact_transaction_replay'],error=meta.get('error'),
        unfinished=analysis['resources']['unfinished_count'])
    del w;gc.collect();return compact

def summarize(rows,expected=480):
    spec=json.loads((ROOT/'docs/r12/acceptance_v1.json').read_text())['evaluation']
    grid={(tim,seed,regime) for tim in spec['types'] for seed in spec['evaluation_seeds'] for regime in spec['regimes']}
    actual={(r['tim'],r['seed'],r['regime']) for r in rows}
    regimes={}
    for regime in ('adequate','constrained_feasible','inadequate'):
        group=[r for r in rows if r['regime']==regime]
        regimes[regime]={'planned':160,'executed':len(group),'passed':sum(r['passed'] for r in group),
            'clearances':sum(r['cleared'] for r in group),'complete_horizons':sum(r['eligible']>=100 and r['changes']>=2 for r in group),
            'resource_stops':sum(r['resource_stop'] is not None for r in group)}
    return {'schema':'r21-panel-v1','planned':expected,'executed':len(rows),
        'denominator_complete':len(rows)==expected and actual==grid,
        'passed':len(rows)==expected and actual==grid and all(r['passed'] for r in rows),
        'regimes':regimes,'rows':rows,'python':sys.version,'platform':platform.platform()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r21/panel')
    p.add_argument('--type',action='append');p.add_argument('--workers',type=int,default=1)
    a=p.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=True)
    spec=json.loads((ROOT/'docs/r12/acceptance_v1.json').read_text())['evaluation']
    protocol=ROOT/'docs/r21/Protocol_R21_v1.json'
    if hashlib.sha256(protocol.read_bytes()).hexdigest()!=(protocol.with_suffix('.sha256')).read_text().strip():
        raise ValueError('frozen R21 protocol changed')
    jobs=[]
    for tim in a.type or spec['types']:
        for seed in spec['evaluation_seeds']:
            for regime,b in spec['regimes'].items():
                jobs.append((out,tim,seed,regime,b['energy']))
    rows=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for row in pool.map(execute_job,jobs):
            rows.append(row);print(json.dumps(row),flush=True)
            save(out/'progress.json',summarize(rows))
    report=summarize(rows);save(out/'summary.json',report)
    print(json.dumps({'executed':len(rows),'regimes':report['regimes'],'passed':report['passed']}),flush=True)
    return 0 if report['passed'] else 1

def execute_job(job):
    out,tim,seed,regime,budget=job
    path=out/(f'{tim}_{seed}_{regime}.compact.json')
    # Source-only archives omit the separate raw evidence payload. In that
    # case regenerate the episode instead of presenting a missing trace as
    # an available cached evaluation.
    if path.exists() and (out/(f'{tim}_{seed}_{regime}.transactions.jsonl.gz')).exists():
        return json.loads(path.read_text())
    row=case(*job);save(path,row);return row

if __name__=='__main__':raise SystemExit(main())
