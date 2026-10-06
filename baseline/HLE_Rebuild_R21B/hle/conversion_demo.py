"""R17 opportunities over genuine R16 histories; never inject learned output."""
from dataclasses import replace
from .compensation_demo import world as parent_world, introduce, run as parent_run
from .conversion import ConversionWorld
from .conversion_records import ConversionPolicy, ConversionCommand
from .contracts import Ref, Kind, ActionRequest
from .world_records import Attempt, TRANSFER
from .autonomy_records import WorkshopCommand
from .compensation_records import ReleaseCommand
from .concept_demo import fund_command

def run(w,horizon=10000):
    result=parent_run(w,horizon)
    result['resource_censored']=result['resource_censored'] or any(
        min(w._wallets[a].energy,w._wallets[a].time)==0 and
        (a in w._conversion_active or w._operation(a) is not None or w._recall_due(a) is not None)
        for a in w.config.actors)
    return result

def world(history=3, maintained=3, later=6, **kwargs):
    policy = kwargs.pop('conversion_policy', None)
    b = parent_world(history=history, renewals=maintained+later, **kwargs)
    # Required practice and held-out required demand are real environmental
    # constraints, declared before any learning takes place.
    required = b.release.required_items + (Ref(Kind.ENTITY, 'tool:'+str(history+maintained+1), 1),
                                          Ref(Kind.ENTITY, 'tool:'+str(history+maintained+later-1), 1))
    return ConversionWorld(b.config,b.profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,
        b.workshop,b.autonomy,release=replace(b.release,required_items=required),reviewers=b.reviewers,
        conversion_policy=policy)

def offer(w, index, partner=False):
    if not partner:
        return introduce(w,index)
    worker,lender,reviewer=w.config.actors
    old=Ref(Kind.ENTITY,'tool:'+str(index-1),1);spare=Ref(Kind.ENTITY,'retire:'+str(index),1)
    fund_command(w,WorkshopCommand('offer:retire:'+str(index),'offer:retire:'+str(index),lender,'use',(spare,old)))
    fund_command(w,WorkshopCommand('offer:old:'+str(index),'offer:old:'+str(index),worker,'inspect',(old,)))
    tool=Ref(Kind.ENTITY,'tool:'+str(index),1);piece=Ref(Kind.ENTITY,'piece:'+str(index),1)
    w.execute(Attempt('changed:owner:'+str(index),'changed:owner:'+str(index),ActionRequest(lender,TRANSFER,(tool,reviewer),())))
    fund_command(w,WorkshopCommand('offer:clean:'+str(index),'offer:clean:'+str(index),reviewer,'clean',(tool,)))
    w.execute(Attempt('offer:piece:'+str(index),'offer:piece:'+str(index),ActionRequest(lender,TRANSFER,(piece,worker),())))
    for obj in (piece,tool):
        key='offer:inspect:'+obj.key
        fund_command(w,WorkshopCommand(key,key,worker,'inspect',(obj,)))

def case(history=3, maintained=3, stop_after_acquisition=False, **kwargs):
    w=world(history,maintained,**kwargs); worker=w.config.actors[0]
    schedules=[run(w)];cuts=[]
    for i in range(history+maintained):
        cuts.append(len(w._journal));introduce(w,i);schedules.append(run(w))
    historical_report=w.shell_report();start=len(w._journal)
    fund_command(w,ConversionCommand('conversion:release','conversion:release',worker,'release',work_limit=256))
    schedules.append(run(w));practice_start=history+maintained
    for i in range(practice_start,practice_start+2):
        cuts.append(len(w._journal));introduce(w,i);schedules.append(run(w))
    acquired=len(w._journal)
    setup={'history':history,'maintained':maintained,'start':start,'acquired':acquired,
        'cuts':cuts,'historical_report':historical_report,'scheduling':schedules,
        'practice_items':[f'tool:{practice_start}',f'tool:{practice_start+1}'],
        'renewed_items':[f'tool:{practice_start+2}',f'tool:{practice_start+3}'],
        'held_out_items':[f'tool:{practice_start+4}',f'tool:{practice_start+5}']}
    if not stop_after_acquisition: renew(w,setup)
    return w,setup

def renew(w,setup):
    practice_start=setup['history']+setup['maintained']
    # Withdraw the former cheapest carrier. The ordinary lender remains a
    # legitimate available carrier, so fallback cannot be credited as change.
    reviewer=w.config.actors[2]
    fund_command(w,ReleaseCommand('support:withdraw','support:withdraw',reviewer,'boundary',willingness=False,work_limit=256))
    for i in range(practice_start+2,practice_start+6):
        setup['cuts'].append(len(w._journal));offer(w,i,partner=i==practice_start+5);setup['scheduling'].append(run(w))
