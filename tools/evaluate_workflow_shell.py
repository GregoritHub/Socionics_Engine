"""FB3.1 exhaustive prevention, paid correction and matched invalid bypass."""
import sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_shell.fixtures import NAMES,FACES,panel_case
from tools.evaluate_workflow_selection import manifest,save

def main(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest()
    (out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
    for name in NAMES:
        for face in FACES:
            key=name+'-'+face;worlds={}
            try:
                _,row=panel_case(name,face,worlds)
                row['worlds']={arm:save(out,key+'-'+arm,e) for arm,e in worlds.items()}
                rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
                print('PASS',key,flush=True)
            except Exception:
                (out/(key+'-failure.txt')).write_text(traceback.format_exc())
                for arm,e in worlds.items():save(out,key+'-'+arm+'-failed',e)
                raise
    unchanged=manifest()==freeze
    result=dict(passed=unchanged,pairs=32,worlds=96,invalid_bypasses_rejected=32,source_unchanged=unchanged)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');assert unchanged

if __name__=='__main__':main(Path(sys.argv[1]))
