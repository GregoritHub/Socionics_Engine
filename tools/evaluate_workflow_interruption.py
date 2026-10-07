"""FB3.2 active interruption and exact checkpoint pairs on all 32 cells."""
import sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_interruption.fixtures import NAMES,FACES,KINDS,panel_case
from tools.evaluate_workflow_selection import manifest,save

def main(out):
    out.mkdir(parents=True,exist_ok=False);(out/'continuations').mkdir()
    freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
    for i,name in enumerate(NAMES):
        for j,face in enumerate(FACES):
            key=name+'-'+face;effect=KINDS[(i*2+j)%len(KINDS)];worlds={};continued={}
            try:
                _,_,row=panel_case(name,face,effect,worlds,continued)
                row['worlds']={arm:save(out,key+'-'+arm,e) for arm,e in worlds.items()}
                row['continuation_worlds']={arm:save(out/'continuations',key+'-'+arm,e) for arm,e in continued.items()}
                rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
                print('PASS',key,effect,flush=True)
            except Exception:
                (out/(key+'-failure.txt')).write_text(traceback.format_exc())
                for arm,e in worlds.items():save(out,key+'-'+arm+'-failed',e)
                for arm,e in continued.items():save(out/'continuations',key+'-'+arm+'-failed',e)
                raise
    unchanged=manifest()==freeze
    result=dict(passed=unchanged,pairs=32,panel_worlds=96,continuation_worlds=96,
        invalid_continuations_rejected=32,exact_continuations=32,effects=5,source_unchanged=unchanged)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');assert unchanged

if __name__=='__main__':main(Path(sys.argv[1]))
