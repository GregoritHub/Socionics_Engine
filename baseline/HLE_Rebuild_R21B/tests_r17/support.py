from dataclasses import replace
from hle.conversion import ConversionWorld
from hle.conversion_records import ConversionCommand, ConversionTransaction
from hle.concept_demo import fund_command
from hle.autonomy_records import WorkshopCommand
from hle.contracts import Ref,Kind,ActionRequest
from hle.world_records import Attempt,TRANSFER

def fresh(w,config=None):
    return ConversionWorld(config or w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
        w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,account_policy=w.account_policy,
        conversion_policy=w.conversion_policy)

def prefix(w,n):
    v=fresh(w)
    for tx in w._journal[1:n]: v.execute(tx.command)
    return v

def first(w,op):
    return next(i for i,t in enumerate(w._journal) if type(t) is ConversionTransaction and t.job.operation==op)

def command(w,operator,**kw):
    key='test:'+operator+':'+str(len(w._journal))
    return ConversionCommand(key,key,w.config.actors[0],operator,**kw)

def failed_trial(w):
    """Real intervening use invalidates the clean-return precondition."""
    v=prefix(w,first(w,'try')+1);a,lender,_=v.config.actors
    u=v._practice_pending[a];extra=Ref(Kind.ENTITY,'retire:0',1)
    v.execute(Attempt('intervene:piece','intervene:piece',ActionRequest(lender,TRANSFER,(extra,a),())))
    fund_command(v,WorkshopCommand('intervene:use','intervene:use',a,'use',(extra,u.item)))
    event=fund_command(v,WorkshopCommand('intervene:return','intervene:return',a,'return',(u.item,)))
    fund_command(v,command(v,'advance',work_limit=256))
    return v,event
