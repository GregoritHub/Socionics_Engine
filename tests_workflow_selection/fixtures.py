"""Evaluator-only starting opportunities; never imported by the selector."""
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_selection_execution import WorkflowSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest
from hle_unified.operations import address
from hle_unified.selection_records import loads

SELF_NAMES=('Contemplate','Act','Commune','Integrate')

class WithheldChoice(WorkflowSelectionEngine):
    def _launch_workflow(self,cid,s,row): return None

def fixture(name,face,engine_type=WorkflowSelectionEngine,tim='iee',budget=200000):
    e=setup_workflow(tim,engine_type=engine_type,budget=budget)
    base=cell(e,name,face,prepare_only=True);native=base['request']
    priorities=tuple(10 if i==SELF_NAMES.index(name) else 0 for i in range(4))
    need=seed(e,'outcome-need',wf.encode(dict(kind='workflow_need',priorities=priorities,externalize=face=='expenditure')),
        target=native.target,relation='c7ws.need')
    r=WorkflowSelectionRequest('auto',ALICE,ROOM,CUE5,native.target,need,native.inputs,
        stock=native.stock,relation=native.relation,peer=native.peer,group=native.group)
    return e,r,base

def finish(e,r):
    for i in range(8):
        if e.participate('turn-'+str(i),r) is None: break
    return attrs(e.world.resolve(address('c7ws.decision',r.actor,r.key)))

def consume(e,r,base):
    child=e.job_status(ALICE,r.key+':movement')
    native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
    return consume_result(e,dict(request=native,result=child.get('binding') or child['result'],inputs=native.inputs,extra=base['extra']))

def fixed_query(e,r,name):
    """Same downstream request in both arms, with no manufactured fallback output."""
    key=r.key+':movement'
    if name=='Act':
        current=e.world.head(r.target.identity).ref;expose(e,BOB,current)
        perform(e,OperationRequest('fixed-owner-use',BOB,'use',ROOM,target=current,evidence=evidence(e,BOB,current)),limit=100000)
        return e.job_status(BOB,'fixed-owner-use')['status']
    source=address('c7w.output',ALICE,key)
    domain={'Contemplate':'personal','Commune':'shared','Integrate':'system'}[name]
    kw=dict(peer=r.peer,group=r.group) if name=='Commune' else {}
    req=request(e,'fixed-query','use-'+domain,None,(source,),target=r.target,completed=('maintain',),clock=1,**kw)
    try:return data(e,work(e,req))['next_task']
    except ValueError:return 'unavailable selected output'
