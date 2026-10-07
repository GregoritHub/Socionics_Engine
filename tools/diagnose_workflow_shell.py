"""Preserve the inherited five-effect boundary before FB3.1 extension."""
import sys, json, gzip, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT), str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c7_workflow.fixtures import *
from tests_u8 import fixtures as dev
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.crux_shell_records import ShellMovementRequest
from hle_unified.shell_records import PatternPolicy, Effect, KINDS
from hle_unified.workflow_selection_audit import audit
from tools.evaluate_workflow_selection import manifest, save

def main(out):
    out.mkdir(parents=True,exist_ok=False)
    freeze=manifest(); (out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    rows=[]
    for kind in KINDS:
        e=None
        try:
            e=setup_workflow(engine_type=WorkflowFinalSelectionEngine)
            e.declare('diagnostic-anchors',(definition(dev.TRIGGER,'Entrusted workflow opportunity'),))
            for ref_ in (dev.TRIGGER,ObjectRef(EVE,1),SAW2):
                if ref_ not in e.access._known_refs(ALICE): show(e,ALICE,ref_)
            e.configure_patterns('diagnostic-policy',PatternPolicy(ALICE,generate=False))
            dev.supply8(e,'diagnostic-origin')
            pattern=dev.inject(e,Effect(kind,'*',-1 if kind=='salience' else 1))
            out_=cell(e,'Contemplate','accumulation',prepare_only=True)
            r=out_['request'];dev.supply8(e,'diagnostic-current',target=r.target)
            try:
                q=ShellMovementRequest('gate',r,ObjectRef(BOB,1),ObjectRef(EVE,1),dev.evidence8(e,(r.target,)))
                e.start('diagnostic-gate',q)
            except ValueError as exc: boundary=str(exc)
            else: boundary='accepted'
            out_['result']=work(e,r); later=consume_result(e,out_)
            raw_audit=audit(e.world.journal(),e.access.checkpoint())
            rows.append(dict(effect=kind,origin_mode='injected_fixture',inherited_gate=boundary,
                bare_workflow_status=e.job_status(ALICE,r.key)['status'],
                next_task=later['consequence']['next_task'],independent_audit=raw_audit['passed'],**save(out,kind,e)))
            (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(kind,boundary,'bare workflow succeeded',flush=True)
        except Exception:
            (out/(kind+'-failure.txt')).write_text(traceback.format_exc())
            if e:save(out,kind+'-failed',e)
            raise
    unchanged=manifest()==freeze
    result=dict(status='diagnostic finding',effects=5,source_unchanged=unchanged,
        conclusion='Inherited ShellMovementRequest rejects WorkflowRequest at its type boundary; bare workflow execution does not apply those Shell effects.',rows=rows)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');assert unchanged

if __name__=='__main__':main(Path(sys.argv[1]))
