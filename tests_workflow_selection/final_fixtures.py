"""Declared responsiveness worlds; all knowledge and capacity changes are paid."""
from dataclasses import replace
from .social_fixtures import *
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowCapacitySelectionRequest, fields_of
from hle_unified.workflow_selection_audit import audit,extent
from hle_unified.workflow_audit import audit as native_audit

class WithheldFinal(WorkflowFinalSelectionEngine):
    def _launch_workflow(self,cid,s,row):return None

class UnresponsiveFinal(WorkflowFinalSelectionEngine):
    def _workflow_policy(self,s):
        rows,_=super()._workflow_policy(s)
        return rows,next(x for x in rows if x['recipe']=='workflow-express-accumulation-v1')

def final_fixture(name,face,engine_type=WorkflowFinalSelectionEngine,tim='iee'):
    return social_fixture(name,face,engine_type,tim)

def information_base():
    e,r,b=final_fixture('Express','expenditure');supply=ref('partly-known-care-stock')
    e.world.create('supplied-partial-stock',WRITER,(stock(supply,'care',5),))
    show(e,ALICE,supply,key='stock-quantity-only',selectors=(Selector('quantity','detail',('facets','0','quantity')),))
    return e,replace(r,stock=supply),b

def capacity_base():
    e,r,b=final_fixture('Express','expenditure');proc=ref('native-care-means');training=ref('held-out-training-tool');supply=ref('training-care-stock')
    e.world.create('supplied-care-training',WRITER,(ObjectVersion(proc,WRITER,'Named native care',(Role.PROCEDURE,),
        (Procedure(SIGNATURES['care'],(),(),(),'u4.care.v1'),)),tool(training,wear=1,maximum=12),stock(supply,'care',5)))
    show(e,ALICE,proc,key='paid-care-definition',selectors=(Selector('procedure','definition',('facets','0')),))
    for obj in (training,supply):expose(e,ALICE,obj)
    return e,WorkflowCapacitySelectionRequest(**fields_of(r),procedure=proc),b

def acquire_care(e,r,acquire=True):
    training=ref('held-out-training-tool');supply=ref('training-care-stock')
    assert training.identity!=r.target.identity
    event=perform(e,OperationRequest('actual-care-practice',ALICE,'care',ROOM,target=training,stock=supply,
        evidence=evidence(e,ALICE,training)),limit=100000)
    value=e.world.resolve(event)
    show(e,ALICE,event,key='paid-practice-outcome',selectors=tuple(Selector(a.name,'detail',('attributes',str(i),'value'))
        for i,a in enumerate(value.attributes)))
    if acquire:perform(e,OperationRequest('actual-care-acquisition',ALICE,'acquire',ROOM,procedure=r.procedure,practice=event),limit=100000)
    return event

def selection_outcome(e,r,b,rejected=False):
    d=finish(e,r);later=consume(e,r,b);query=social_query(e,r,'Express')
    native_audit(e.world.journal(),e.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))
    rejection=None
    try:audit(e.world.journal(),e.access.checkpoint())
    except ValueError as exc:
        if not rejected or 'not the best evaluated choice' not in str(exc):raise
        rejection=str(exc)
    else:
        if rejected:raise AssertionError('unresponsive choice passed ordinary auditor')
    return dict(recipe=d['recipe'],spent=d['spent'],query=query,child_failure=e.job_status(ALICE,r.key+':movement')['failure'],
        next_task=later['consequence']['next_task'],expected_rejection=rejection)

def responsiveness(register=None):
    """Three comparisons, each with explicit raw branches and bounded claims."""
    worlds=[];pairs=[];register=register or (lambda name,e,bad:None)
    e,r,b=information_base();before=WorkflowFinalSelectionEngine.restore(e.checkpoint())
    register('information-responsive',e,False);register('information-withheld',before,False)
    d0=selection_outcome(before,r,b);worlds.append(('information-withheld',before,False))
    expose(e,ALICE,r.stock);control=UnresponsiveFinal.restore(e.checkpoint())
    register('information-unresponsive',control,True)
    d1=selection_outcome(e,r,b);dc=selection_outcome(control,r,b,True)
    assert d0['recipe']==dc['recipe']=='workflow-express-accumulation-v1' and d1['recipe']=='workflow-express-expenditure-v1'
    assert d1['spent']==dc['spent']==d0['spent'] and d1['query']!=dc['query']
    worlds.extend((('information-responsive',e,False),('information-unresponsive',control,True)))
    pairs.append(dict(kind='delivered-information',before=d0,after=d1,control=dc))
    e,r,b=capacity_base();before=WorkflowFinalSelectionEngine.restore(e.checkpoint())
    register('capacity-responsive',e,False);register('capacity-withheld-acquisition',before,False)
    acquire_care(before,r,False);d0=selection_outcome(before,r,b);worlds.append(('capacity-withheld-acquisition',before,False))
    acquire_care(e,r);control=UnresponsiveFinal.restore(e.checkpoint())
    register('capacity-unresponsive',control,True)
    d1=selection_outcome(e,r,b);dc=selection_outcome(control,r,b,True)
    assert d0['recipe']==dc['recipe']=='workflow-express-accumulation-v1' and d1['recipe']=='workflow-express-expenditure-v1'
    assert d1['spent']==dc['spent']==d0['spent'] and d1['query']!=dc['query']
    worlds.extend((('capacity-responsive',e,False),('capacity-unresponsive',control,True)))
    pairs.append(dict(kind='acquired-care-held-out-target',before=d0,after=d1,control=dc,
        training_target='held-out-training-tool',selected_target=r.target.identity.key))
    e,r,b=final_fixture('Express','expenditure');original=WorkflowFinalSelectionEngine.restore(e.checkpoint())
    register('hidden-delivered-change',e,False);register('hidden-unchanged-material',original,False)
    rows0,win0=e._workflow_policy(e.workflow_selection_view(r))
    perform(e,OperationRequest('hidden-target-transfer',ALICE,'transfer',ROOM,target=r.target,recipient=BOB,participants=(BOB,),
        evidence=evidence(e,ALICE,r.target)),limit=100000)
    rows1,win1=e._workflow_policy(e.workflow_selection_view(r));assert rows0==rows1 and win0==win1
    hidden=WorkflowFinalSelectionEngine.restore(e.checkpoint());register('hidden-undelivered-change',hidden,False)
    dh=finish(hidden,r);audit(hidden.world.journal(),hidden.access.checkpoint())
    hidden_status=None if dh['child'] is None else hidden.job_status(ALICE,r.key+':movement')['status']
    assert dh['recipe']=='workflow-express-expenditure-v1' and (dh['failure'] is not None or hidden_status=='failed')
    original_result=selection_outcome(original,r,b)
    current=e.world.head(r.target.identity).ref;expose(e,ALICE,current);changed=replace(r,target=current)
    d1=selection_outcome(e,changed,b)
    assert d1['recipe']=='workflow-express-accumulation-v1' and dh['spent']==d1['spent']==original_result['spent']
    worlds.extend((('hidden-unchanged-material',original,False),('hidden-undelivered-change',hidden,False),('hidden-delivered-change',e,False)))
    pairs.append(dict(kind='hidden-material-versus-delivered-revision',before=original_result,
        hidden_recipe=dh['recipe'],hidden_admission_failure=dh['failure'],hidden_child_status=hidden_status,
        after=d1,paid_candidates_unchanged_before_delivery=True))
    return worlds,pairs
