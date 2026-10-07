"""Evaluator opportunities for the twenty-cell policy; no evaluator imports in engine."""
from .fixtures import *
from hle_unified.workflow_selection_execution import WorkflowCrossingSelectionEngine
from hle_unified.selection_records import PERSPECTIVES

CROSSING_NAMES=('Express','Embody','Theorize','Understand','Apply','Organize')
PANEL_NAMES=SELF_NAMES+CROSSING_NAMES

class WithheldCrossing(WorkflowCrossingSelectionEngine):
    def _launch_workflow(self,cid,s,row):return None

def crossing_fixture(name,face,engine_type=WorkflowCrossingSelectionEngine,tim='iee'):
    e=setup_workflow(tim,engine_type=engine_type)
    base=cell(e,name,face,prepare_only=True);native=base['request']
    destination=WORKFLOW_RECIPES[native.recipe].destination
    need=seed(e,'outcome-need',wf.encode(dict(kind='workflow_need',
        priorities=tuple(10 if x==destination else 0 for x in PERSPECTIVES),externalize=face=='expenditure')),
        target=native.target,relation='c7ws.need')
    r=WorkflowSelectionRequest('auto',ALICE,ROOM,CUE5,native.target,need,native.inputs,
        stock=native.stock,relation=native.relation,peer=native.peer,group=native.group)
    return e,r,base

def crossing_query(e,r,name):
    if name in SELF_NAMES:return fixed_query(e,r,name)
    key=r.key+':movement'
    # Withholding the defining step creates no native job. Only the lookup's
    # absent-job error means unavailable output; later consumer errors propagate.
    try:job=e.job_status(r.actor,key)
    except KeyError:return 'unavailable selected output'
    if job is None or job['status']!='succeeded':return 'unavailable selected output'
    if name in ('Express','Apply'):
        source=receive(e,job['result'],ALICE,'fixed-selected-event');domain='activity';done=();clock=0
    else:
        source=address('c7w.output',ALICE,key);domain='personal' if name in ('Embody','Understand') else 'system'
        done=() if name=='Embody' else ('care-0',) if name=='Organize' else ('maintain',);clock=1 if done else 0
    req=request(e,'fixed-crossing-query','use-'+domain,None,(source,),target=r.target,completed=done,clock=clock)
    return data(e,work(e,req))['next_task']
