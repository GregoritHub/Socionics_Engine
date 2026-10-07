"""Frozen FB5.4 continued-family worlds and source-withholding controls."""
import gzip,hashlib,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_families.fixtures import family,withheld,terminal_query,FAMILIES,WorkflowAgenda,ALICE
from tools.evaluate_workflow_continuation import manifest


def save(folder,key,p):
    path=folder/(key+'.json.gz');path.write_bytes(gzip.compress(p.checkpoint().encode(),mtime=0))
    return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main(folder):
    folder.mkdir(parents=True,exist_ok=False);freeze=manifest()
    (folder/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[];p=None
    try:
        for name in FAMILIES:
            for control in (False,True):
                key=name+('-withheld' if control else '')
                p=withheld(name) if control else family(name);p.run(2000)
                answer=terminal_query(p)
                assert p.halted=='missing_prior_result' if control else p.stage==len(p.goals) and p.halted is None
                assert answer is None if control else answer['next_task'] is not None
                rows.append(dict(case=key,family=name,control=control,**save(folder,key,p)))
                print('SAVED',key,flush=True)
        for name in FAMILIES[:2]:
            p=family(name);p.run(2);save(folder,name+'-interrupted',p)
            q=WorkflowAgenda.restore(p.checkpoint());p.run(2000);q.run(2000)
            assert p.checkpoint()==q.checkpoint()
            rows.append(dict(case=name+'-restore',control=False,restore=True,**save(folder,name+'-restore',q)))
        p=family(FAMILIES[0]);key='agenda:family:0:movement'
        for _ in range(100):
            p.step()
            if (ALICE,key) in p.engine._jobs:
                d=p.engine.job_status(ALICE,key)
                if d['status'] not in ('succeeded','failed','cancelled') and d['spent']>0:break
        p.engine.cancel('authored-interruption',ALICE,key);p.run(2000);assert p.halted=='native_cancelled'
        rows.append(dict(case='cancelled-child',control=False,**save(folder,'cancelled-child',p)))
        p=family(FAMILIES[1]);p.run(1);assert not p.done
        rows.append(dict(case='finite-budget',control=False,**save(folder,'finite-budget',p)))
        assert manifest()==freeze
        (folder/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
        (folder/'summary.json').write_text(json.dumps(dict(passed=True,source_unchanged=True,cases=len(rows),families=5,controls=5),indent=2)+'\n')
    except Exception:
        (folder/'failure.txt').write_text(traceback.format_exc())
        if p is not None:save(folder,'failed-current',p)
        raise
    print('PASS',len(rows),'frozen cases',flush=True)

if __name__=='__main__':main(Path(sys.argv[1]))
