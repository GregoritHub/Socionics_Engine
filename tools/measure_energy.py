"""Sequential isolated core costs and unchanged legacy workload guards."""
import gzip,hashlib,json,os,pathlib,platform,statistics,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tools.run_energy_regression import manifest

def worker(config):
    root=pathlib.Path(config['root']);sys.path[:0]=[str(root),str(root/'baseline/HLE_Rebuild_R21B')]
    from unittest.mock import patch
    from tests_workflow_population.sustained_fixtures import sustained_population
    from hle_unified.population import Population
    from hle_unified.population_audit import audit_population
    from hle_unified.workflow_selection_audit import audit
    from hle_unified.selection_records import loads
    start=time.perf_counter()
    if config['model']=='grade-v1':
        from tests_energy.fixtures import factory
        with patch('tests_workflow_population.sustained_fixtures.WorkflowFinalSelectionEngine',factory('grade-v1')):
            p=sustained_population(config['seed'],repeat_limit=config['repeat_limit'],inactive=config['inactive'],shared=config['shared'])
    else:p=sustained_population(config['seed'],repeat_limit=config['repeat_limit'],inactive=config['inactive'],shared=config['shared'])
    setup=time.perf_counter()-start;start=time.perf_counter();cpu=time.process_time();result=p.run(20000);active=time.perf_counter()-start;cpu=time.process_time()-cpu
    assert result['done'];start=time.perf_counter();cp=p.checkpoint();checkpoint=time.perf_counter()-start
    start=time.perf_counter();restored=Population.restore(cp);restore=time.perf_counter()-start;assert cp==restored.checkpoint()
    start=time.perf_counter();a=audit(p.engine.world.journal(),p.engine.access.checkpoint());b=audit_population(p.engine.world.journal(),loads(cp));auditing=time.perf_counter()-start
    return dict(config=config,result=result,setup_seconds=setup,active_seconds=active,active_cpu_seconds=cpu,checkpoint_seconds=checkpoint,restore_seconds=restore,audit_seconds=auditing,checkpoint_bytes=len(cp.encode()),gzip_bytes=len(gzip.compress(cp.encode(),mtime=0)),checkpoint_sha256=hashlib.sha256(cp.encode()).hexdigest(),transactions=len(p.engine.world.journal()),native_completions=b['native_completions'],exact_restore=True,raw_audit=True)

def main(out,reference):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    protocol=json.loads((ROOT/'contracts/Energy_Protocol_v1.json').read_text());configs=[]
    for model in ('legacy-r4','grade-v1'):
        for w in protocol['panels']['phase5_core']['worlds']:
            configs.append(dict(id=model+'-'+w['id'],root=str(ROOT),model=model,seed=w['seed'],repeat_limit=w['repeat_limit'],inactive=0,shared=False,group='model'))
    for w in protocol['panels']['phase5_core']['worlds']:
        configs.append(dict(id='reference-'+w['id'],root=str(reference),model='legacy-r4',seed=w['seed'],repeat_limit=w['repeat_limit'],inactive=0,shared=False,group='reference'))
    for shared in (False,True):
        for n in (0,100,1000):
            if not shared and not n:continue
            configs.append(dict(id='history-'+str(shared)+'-'+str(n),root=str(ROOT),model='legacy-r4',seed=17,repeat_limit=2,inactive=n,shared=shared,group='history'))
    rows=[]
    for config in configs:
        for sample in range(4):
            p=subprocess.run([sys.executable,__file__,'worker',json.dumps(config)],cwd=config['root'],capture_output=True,text=True)
            key=config['id']+'-'+str(sample);(out/(key+'.stdout.json')).write_text(p.stdout);(out/(key+'.stderr.log')).write_text(p.stderr)
            if p.returncode:raise RuntimeError(key+': '+p.stderr)
            row=json.loads(p.stdout);row.update(sample=sample,warmup=sample==0);rows.append(row)
            print(key,round(row['active_seconds'],3),flush=True)
    def median(key):return statistics.median(r['active_seconds'] for r in rows if r['config']['id']==key and not r['warmup'])
    guards=[]
    for w in protocol['panels']['phase5_core']['worlds']:
        current='legacy-r4-'+w['id'];old='reference-'+w['id'];ratio=median(current)/median(old)
        a={r['checkpoint_sha256'] for r in rows if r['config']['id']==current};b={r['checkpoint_sha256'] for r in rows if r['config']['id']==old}
        guards.append(dict(kind='unchanged-native',world=w['id'],ratio=ratio,limit=2,exact_checkpoint=a==b and len(a)==1,passed=ratio<=2 and a==b and len(a)==1))
    for shared in (False,True):
        keys=[('legacy-r4-default-17' if not shared and not n else 'history-'+str(shared)+'-'+str(n)) for n in (0,100,1000)]
        vals=[median(k) for k in keys];ratio=max(vals)/min(vals)
        guards.append(dict(kind='inactive-history',shared=shared,medians=vals,ratio=ratio,limit=3,passed=ratio<=3))
    result=dict(passed=all(g['passed'] for g in guards) and manifest()==freeze,source_unchanged=manifest()==freeze,python=sys.version,host=platform.platform(),samples=len(rows),guards=guards,rows=rows,claim='Descriptive model costs, no optimization claim. Warmup excluded; timings untraced, sequential isolated subprocesses.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result['passed'],flush=True);return result
if __name__=='__main__':
    if sys.argv[1]=='worker':print(json.dumps(worker(json.loads(sys.argv[2]))))
    else:sys.exit(not main(pathlib.Path(sys.argv[1]).resolve(),pathlib.Path(sys.argv[2]).resolve())['passed'])
