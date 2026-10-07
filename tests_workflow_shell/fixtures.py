"""Deterministic paid workflow opportunities; only approval is generated."""
from tests_c7_workflow.fixtures import *
from tests_u8 import fixtures as dev
from hle_unified.workflow_shell_execution import WorkflowShellEngine
from hle_unified.workflow_shell_records import WorkflowShellRequest
from hle_unified.workflow_shell_audit import audit
from hle_unified.shell_records import PatternPolicy, Effect
from hle_unified.selection_records import NAMES, FACES

class BypassedGate(WorkflowShellEngine):
    """Deliberate evaluator intervention; ordinary raw audit must reject it."""
    def _workflow_shell_allows(self,decision,route):return decision is not None

def setup(tim='iee',engine_type=WorkflowShellEngine,generate=True):
    e=setup_workflow(tim,engine_type=engine_type)
    e.declare('workflow-shell-anchors',(definition(dev.TRIGGER,'Entrusted workflow opportunity'),
        definition(dev.OTHER_TRIGGER,'Distinct workflow opportunity')))
    for ref_ in (dev.TRIGGER,dev.OTHER_TRIGGER,ObjectRef(EVE,1),SAW2):
        if ref_ not in e.access._known_refs(ALICE):show(e,ALICE,ref_)
    e.configure_patterns('workflow-shell-policy',PatternPolicy(ALICE,generate=generate))
    return e

def prepare(e,name,face,key='case',**kwargs):
    return cell(e,name,face,key=key,prepare_only=True,**kwargs)

def gate(e,r,key='gate',**kwargs):
    return WorkflowShellRequest(key,r,ObjectRef(BOB,1),ObjectRef(EVE,1),
        dev.evidence8(e,(r.target,)),**kwargs)

def finish(e,out,key='gate',partial=False,consume=True):
    r=out['request'];q=gate(e,r,key)
    e.start(key+':start',q)
    if partial:
        e.advance(key+':partial',r.actor,key,1)
        e=type(e).restore(e.checkpoint())
    e.advance(key+':advance',r.actor,key,1000000)
    e.commit(key+':commit',r.actor,key)
    d=attrs(e.world.resolve(address('c7sh.admission',r.actor,key)))
    later='unavailable'
    if d['child']:
        e.advance(key+':child-advance',r.actor,r.key,1000000)
        if e.job_status(r.actor,r.key)['status']=='ready':e.commit(key+':child-commit',r.actor,r.key)
        child=e.job_status(r.actor,r.key)
        if child['status']=='succeeded' and consume:
            result=child.get('binding') or child['result']
            consumed=consume_result(e,dict(out,result=result))
            later=consumed['consequence']['next_task']
    return e,d,later

def prepared(name,face):
    base=setup();pattern=dev.generated(base);out=prepare(base,name,face)
    dev.supply8(base,'current-neutral',target=out['request'].target)
    return base,pattern,out

def panel_case(name,face,worlds=None):
    worlds={} if worlds is None else worlds
    base,pattern,out=prepared(name,face);cp=base.checkpoint()
    worlds['deformed']=WorkflowShellEngine.restore(cp)
    _,d,blocked=finish(worlds['deformed'],out)
    worlds['corrected']=WorkflowShellEngine.restore(cp)
    release=dev.release8(worlds['corrected'],'local-release',pattern,target=out['request'].target)
    _,c,good=finish(worlds['corrected'],out)
    worlds['bypass']=BypassedGate.restore(cp)
    _,b,bypass=finish(worlds['bypass'],out)
    assert d['child'] is None and blocked=='unavailable'
    assert c['child'] is not None and good is not None and good!='unavailable'
    assert b['child'] is not None and bypass==good
    assert d['admission_spent']==b['admission_spent']
    for arm in ('deformed','corrected'):audit(worlds[arm].world.journal(),worlds[arm].access.checkpoint())
    try:audit(worlds['bypass'].world.journal(),worlds['bypass'].access.checkpoint())
    except ValueError as exc:
        rejection=str(exc);assert 'admission disagrees with paid encounter' in rejection
    else:raise AssertionError('invalid bypass was accepted')
    return worlds,dict(name=name,face=face,effect='approval',origin_mode='generated',
        deformed_admission_spent=d['admission_spent'],bypass_admission_spent=b['admission_spent'],
        corrected_admission_spent=c['admission_spent'],
        correction_spent=worlds['corrected'].job_status(ALICE,'local-release')['spent'],
        blocked=blocked,corrected_next_task=good,bypass_next_task=bypass,rejection=rejection)
