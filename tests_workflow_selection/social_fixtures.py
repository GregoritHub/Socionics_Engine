"""Evaluator-only social opportunities and fixed downstream questions."""
from .crossing_fixtures import *
from hle_unified.workflow_selection_execution import WorkflowSocialSelectionEngine

SOCIAL_NAMES=('Share','Coordinate','Identify','Mobilize','Institutionalize','Educate')
ALL_NAMES=PANEL_NAMES+SOCIAL_NAMES

class WithheldSocial(WorkflowSocialSelectionEngine):
    def _launch_workflow(self,cid,s,row):return None

def social_fixture(name,face,engine_type=WorkflowSocialSelectionEngine,tim='iee'):
    return crossing_fixture(name,face,engine_type,tim)

def social_query(e,r,name):
    if name in PANEL_NAMES:return crossing_query(e,r,name)
    key=r.key+':movement'
    try:job=e.job_status(r.actor,key)
    except KeyError:return 'unavailable selected output'
    if job['status']!='succeeded':return 'unavailable selected output'
    actor=r.actor;kw={};done=('maintain',);clock=1
    if name in ('Share','Coordinate','Educate'):
        source=job['public.0'];actor=r.peer;expose(e,actor,source)
        domain='shared';kw=dict(peer=r.actor,group=r.group)
        if name=='Coordinate':done=();clock=0
    elif name=='Mobilize':
        source=receive(e,job['result'],actor,'fixed-selected-event');domain='activity';done=();clock=0
    else:
        source=address('c7w.output',actor,key);domain='personal' if name=='Identify' else 'system'
        kw=dict(peer=r.peer,group=r.group)
    req=request(e,'fixed-social-query','use-'+domain,None,(source,),actor=actor,target=r.target,completed=done,clock=clock,**kw)
    return data(e,work(e,req),actor)['next_task']
