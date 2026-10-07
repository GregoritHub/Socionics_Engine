"""Deterministic active interruption witnesses and invalid continuation controls."""
from tests_workflow_shell.fixtures import *
from tests_workflow_shell import fixtures as shell
from hle_unified.workflow_interruption_execution import WorkflowInterruptionEngine
from hle_unified.workflow_interruption_records import WorkflowInterruptionRequest
from hle_unified.workflow_interruption_audit import audit
from hle_unified.shell_records import EncounterRequest, KINDS
from hle_unified.operations import address, indexed

class Uninterrupted(WorkflowInterruptionEngine):
    """Deliberate evaluator intervention; retains cost but bypasses cancellation."""
    def _workflow_interrupts(self):return False

def setup(**kwargs):return shell.setup(engine_type=kwargs.pop('engine_type',WorkflowInterruptionEngine),**kwargs)

def prepared(name,face,effect='approval',with_pattern=True):
    e=setup(generate=effect=='approval');p=None
    if with_pattern:
        if effect=='approval':p=dev.generated(e)
        else:
            dev.supply8(e,'pattern-origin')
            ref_=dev.inject(e,Effect(effect,name.lower()+'-'+face+'-v1',-1 if effect=='salience' else 1))
            p=e._patterns[ref_]
    out=prepare(e,name,face);dev.supply8(e,'current-neutral',target=out['request'].target)
    return e,p,out

def gate(e,r,key='gate',**kwargs):
    return WorkflowInterruptionRequest(key,r,ObjectRef(BOB,1),ObjectRef(EVE,1),dev.evidence8(e,(r.target,)),**kwargs)

def admit(e,out,key='gate'):
    r=out['request'];e.start(key+':start',gate(e,r,key));e.advance(key+':advance',r.actor,key,1000000);e.commit(key+':commit',r.actor,key)
    return attrs(e.world.resolve(address('c7shi.admission',r.actor,key)))

def finish(e,out,key='gate'):
    r=out['request'];d=admit(e,out,key);later='unavailable'
    if d['child']:
        e.advance(key+':child-advance',r.actor,r.key,1000000)
        if e.job_status(r.actor,r.key)['status']=='ready':e.commit(key+':child-commit',r.actor,r.key)
        child=e.job_status(r.actor,r.key)
        if child['status']=='succeeded':
            used=consume_result(e,dict(out,result=child.get('binding') or child['result']))
            later=used['consequence']['next_task']
    return d,later

def resume_after_stop(e,out):
    """Further native paid work; cancelled work is never reopened."""
    r=out['request'];q=EncounterRequest('after-stop',r.actor,r.target,r.context,r.cue,
        ObjectRef(BOB,1),ObjectRef(EVE,1),dev.evidence8(e,(r.target,)),r.recipe.removeprefix('workflow-'),True,128)
    before=e.wallet(r.actor)['energy'];e.start('after-stop:start',q)
    for i,limit in enumerate((1,3,1000000)):e.advance('after-stop:advance:'+str(i),r.actor,q.key,limit)
    e.commit('after-stop:commit',r.actor,q.key)
    return before-e.wallet(r.actor)['energy']

def panel_case(name,face,effect,worlds=None,continuations=None):
    worlds={} if worlds is None else worlds;continuations={} if continuations is None else continuations
    base,p,out=prepared(name,face,effect);cp=base.checkpoint()
    worlds['interrupted']=WorkflowInterruptionEngine.restore(cp);d,blocked=finish(worlds['interrupted'],out)
    child=worlds['interrupted'].job_status(ALICE,'case')
    assert child['status']=='cancelled' and child['steps_completed']==1 and blocked=='unavailable'
    if effect=='approval':
        worlds['control']=WorkflowInterruptionEngine.restore(cp)
        dev.release8(worlds['control'],'local-release',p,target=out['request'].target);control_out=out
    else:worlds['control'],_,control_out=prepared(name,face,effect,with_pattern=False)
    c,good=finish(worlds['control'],control_out)
    worlds['bypass']=Uninterrupted.restore(cp);b,bypass=finish(worlds['bypass'],out)
    assert good==bypass and good is not None and good!='unavailable'
    assert d['admission_spent']==b['admission_spent']
    bx=worlds['bypass'].job_status(ALICE,'case')
    prefix=bx['recall_units']+sum(indexed(bx,'route.0.charges.'))+bx['route.0.content_units']
    assert prefix==child['spent'] and bx['spent']>=prefix
    for arm in ('interrupted','control'):audit(worlds[arm].world.journal(),worlds[arm].access.checkpoint())
    try:audit(worlds['bypass'].world.journal(),worlds['bypass'].access.checkpoint())
    except ValueError as exc:
        rejection=str(exc);assert 'escaped first boundary' in rejection
    else:raise AssertionError('invalid continuation was accepted')
    checkpoint=worlds['interrupted'].checkpoint()
    continuations['checkpoint']=WorkflowInterruptionEngine.restore(checkpoint)
    continuations['original']=worlds['interrupted']
    continuations['restored']=WorkflowInterruptionEngine.restore(checkpoint)
    worlds['interrupted']=WorkflowInterruptionEngine.restore(checkpoint)
    amounts=[resume_after_stop(continuations[arm],out) for arm in ('original','restored')]
    assert amounts[0]==amounts[1]>0
    assert continuations['original'].checkpoint()==continuations['restored'].checkpoint()
    for arm in ('original','restored'):audit(continuations[arm].world.journal(),continuations[arm].access.checkpoint())
    return worlds,continuations,dict(name=name,face=face,effect=effect,
        origin_mode='generated' if effect=='approval' else 'injected_fixture',
        interrupted_admission_spent=d['admission_spent'],bypass_admission_spent=b['admission_spent'],
        retained_prefix_spent=child['spent'],bypass_prefix_spent=prefix,bypass_total_child_spent=bx['spent'],
        query=good,blocked=blocked,expected_rejection=rejection,exact_continuation=True,continuation_spent=amounts[0])
