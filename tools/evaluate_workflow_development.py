"""Save the prospective workflow correction and recurrence panel."""
import sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_development.fixtures import history,unsupported
from tools.evaluate_workflow_selection import manifest,save


def main(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();rows=[]
    (out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    worlds={}
    try:
        history(worlds)
        for key,e in worlds.items():rows.append(dict(kind='history',**save(out,key,e)))
        for kind in ('forecast','salience','exclude_route'):
            worlds={};_,attempt=unsupported(kind,worlds)
            attempt['worlds']={arm:save(out,'unsupported-'+kind+'-'+arm,e) for arm,e in worlds.items()}
            (out/('unsupported-'+kind+'-attempt.json')).write_text(json.dumps(attempt,indent=2)+'\n')
            rows.extend(dict(kind='refusal',**entry) for entry in attempt['worlds'].values())
    except Exception:
        (out/'failure.txt').write_text(traceback.format_exc())
        for key,e in worlds.items():save(out,'failed-'+key,e)
        raise
    unchanged=manifest()==freeze
    (out/'summary.json').write_text(json.dumps(dict(passed=unchanged,worlds=len(rows),source_unchanged=unchanged,rows=rows),indent=2)+'\n')
    assert unchanged and len(rows)==16
    print('PASS development worlds',len(rows),flush=True)


if __name__=='__main__':main(Path(sys.argv[1]))
