"""Fixed Phase7 paired panel; workers generate raw evidence, not acceptance."""
import concurrent.futures,gzip,hashlib,json,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tools.run_energy_regression import manifest
PROTOCOL=json.loads((ROOT/'contracts/Energy_Protocol_v1.json').read_text())

def save(out,name,text):
    b=gzip.compress(text.encode(),mtime=0);p=out/(name+'.json.gz');p.write_bytes(b)
    return dict(file=p.name,sha256=hashlib.sha256(b).hexdigest())

def worker(out,spec):
    from unittest.mock import patch
    from tests_energy.fixtures import factory
    from hle_unified.selection_records import dumps
    models=[]
    for model in PROTOCOL['models']:
        captured=[];base=factory(model,spec['energy'],spec['time'])
        def create(world,law):
            e=base(world,law);captured.append(e);return e
        e=p=None;row=dict(model=model,spec=spec,setup_failure=None)
        try:
            if spec['kind']=='automatic':
                from tests_workflow_selection.final_fixtures import final_fixture,finish,consume,social_query,WithheldFinal
                e,r,b=final_fixture(spec['name'],spec['face'],create,spec['tim']);d=finish(e,r)
                assert d['recipe']=='workflow-'+spec['name'].lower()+'-'+spec['face']+'-v1' and d['failure'] is None and d['child'] is not None
                later=consume(e,r,b);good=social_query(e,r,spec['name']);assert later['consequence']['next_task'] is not None
                row['outcome']=json.loads(dumps(dict(decision=d,consequence=later['consequence'],query=good)))
                if spec['tim']=='iee':
                    q,s,_=final_fixture(spec['name'],spec['face'],factory(model,engine_class=WithheldFinal),spec['tim'])
                    c=finish(q,s);bad=social_query(q,s,spec['name']);assert c['child'] is None and c['spent']==d['spent'] and good!=bad
                    row['control']=save(out,spec['id']+'-'+model+'-control',q.checkpoint())
            elif spec['kind']=='core':
                from tests_workflow_population.sustained_fixtures import sustained_population
                with patch('tests_workflow_population.sustained_fixtures.WorkflowFinalSelectionEngine',create):
                    p=sustained_population(spec['seed'],episodes=24,quantum=32,repeat_limit=spec['repeat_limit'])
                e=p.engine;row['outcome']=json.loads(dumps(p.run(20000)))
            else:
                from tests_workflow_sustained_panel.fixtures import sustained_cell,terminal_consequence
                with patch('tests_workflow_sustained_panel.fixtures.WorkflowFinalSelectionEngine',create):p,_=sustained_cell(spec['cell'])
                p.max_turns=2000;e=p.engine;result=p.run();terminal=terminal_consequence(p)
                row['outcome']=json.loads(dumps(dict(result=result,terminal=terminal)))
        except Exception:
            row['error']=traceback.format_exc()
            if spec['funding']!='ample' and p is None and captured:
                row['setup_failure']=row.pop('error');e=captured[-1]
            else:
                if captured:e=captured[-1]
        if e:row['engine']=save(out,spec['id']+'-'+model,e.checkpoint())
        if p:row['population']=save(out,spec['id']+'-'+model+'-population',p.checkpoint())
        models.append(row)
    result=dict(spec=spec,models=models,passed=all('error' not in r and 'engine' in r for r in models))
    (out/(spec['id']+'.row.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result

def specs():
    from hle.model_a import TYPES
    names=('Contemplate','Express','Share','Theorize','Embody','Act','Coordinate','Organize','Identify','Mobilize','Commune','Institutionalize','Understand','Apply','Educate','Integrate')
    for tim in ('iee',*(t for t in TYPES if t!='iee')):
        for name in names:
            for face in ('accumulation','expenditure'):
                yield dict(id='auto-'+tim+'-'+name+'-'+face,kind='automatic',tim=tim,name=name,face=face,funding='ample',energy=200000,time=200000)
    for funding in PROTOCOL['panels']['phase5_core']['funding']:
        for w in PROTOCOL['panels']['phase5_core']['worlds']:
            yield dict(id='core-'+w['id']+'-'+funding['id'],kind='core',seed=w['seed'],repeat_limit=w['repeat_limit'],funding=funding['id'],energy=funding['energy'],time=funding['time'])
        for cell in range(32):
            yield dict(id='extension-'+str(cell)+'-'+funding['id'],kind='extension',cell=cell,funding=funding['id'],energy=funding['energy'],time=funding['time'])

def main(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    rows=[]
    def run(spec):
        p=subprocess.run([sys.executable,__file__,'worker',str(out),json.dumps(spec)],cwd=ROOT,capture_output=True,text=True)
        (out/(spec['id']+'.log')).write_text(p.stdout+p.stderr)
        path=out/(spec['id']+'.row.json')
        if p.returncode or not path.exists():return dict(spec=spec,passed=False,error=p.stderr)
        return json.loads(path.read_text())
    # Declared ample worlds first, then the unchanged scarce settings.
    all_specs=list(specs())
    for funding in ('ample','tight-energy','tight-time'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for f in concurrent.futures.as_completed([pool.submit(run,s) for s in all_specs if s['funding']==funding]):
                r=f.result();rows.append(r)
                (out/'progress.json').write_text(json.dumps(dict(pairs=len(rows),failed=[x['spec']['id'] for x in rows if not x['passed']]),indent=2)+'\n')
                if len(rows)%16==0 or not r['passed']:print(len(rows),r['spec']['id'],r['passed'],flush=True)
    result=dict(passed=all(r['passed'] for r in rows) and manifest()==freeze,pairs=len(rows),source_unchanged=manifest()==freeze,rows=rows)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    if sys.argv[1]=='worker':sys.exit(not worker(pathlib.Path(sys.argv[2]),json.loads(sys.argv[3]))['passed'])
    else:sys.exit(not main(pathlib.Path(sys.argv[1]).resolve())['passed'])
