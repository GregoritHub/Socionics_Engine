"""Declared finite opportunities; corrections and capacities are runtime outputs."""
from tests_u7.fixtures import *
from hle_unified.development import DevelopmentEngine
from hle_unified.development_records import DevelopmentRequest
from hle_unified.development_policy import opportunity
from hle_unified.development_audit import audit


def setup8(**kwargs):
    return DevelopmentEngine.adopt(setup7(budget=kwargs.pop("budget",20000), **kwargs))


def supply8(e,key,*,target=SAW,actor=ALICE,context=ROOM,partner=ObjectRef(BOB,1),**kwargs):
    # Revise one continuing statement, preserving earlier blame/counterevidence.
    _, sources = opportunity(e.participant_view(actor),target,context)
    version = ObjectRef(sources[0].identity,sources[0].revision+1) if sources else ref("u8-facts:"+target.identity.key+":"+str(target.revision)+":"+context.identity.key+":"+actor.key)
    return supply(e,key,target=target,actor=actor,context=context,version=version,partner=partner,**kwargs)


def evidence8(e,targets,actor=ALICE,context=ROOM):
    v=e.participant_view(actor)
    sources=tuple(dict.fromkeys(s for t in targets for s in opportunity(v,t,context)[1]))
    return tuple(p.address for s in sources for p in v.resolve(s))


def request8(e,key,purpose,p,targets=(SAW,),*,actor=ALICE,partner=ObjectRef(BOB,1),
             context=ROOM,cue=CUE5,evidence_=None,**kwargs):
    return DevelopmentRequest(key,actor,purpose,p.ref if hasattr(p,"ref") else p,context,cue,tuple(targets),
        evidence8(e,targets,actor,context) if evidence_ is None else evidence_,partner,**kwargs)


def develop(e,r):
    event=perform(e,r,limit=10000)
    d=e.job_status(r.actor,r.key)
    assert d["status"]=="succeeded",d["failure"]
    return event


def release8(e,key,p,target=SAW,**kwargs):
    supply8(e,key,target=target,**kwargs)
    develop(e,request8(e,key,"release",p,(target,),partner=kwargs.get("partner",ObjectRef(BOB,1))))
    return e.job_status(ALICE,key)["development"]


def respond8(e,key,p,targets=(SAW,),*,prepare=True,partner=ObjectRef(BOB,1),demand=True,**terms):
    if prepare:
        for i,t in enumerate(targets):
            supply8(e,key+":"+str(i),target=t,partner=partner,**terms)
    return develop(e,request8(e,key,"respond",p,targets,partner=partner,demand=demand))


def practice8(e,key,p,event):
    response=e._response_results[event]
    obs=receive(e,event,ALICE,key)
    r=request8(e,key,"practice",p,response["targets"],partner=response["partner"],observation=obs,
               evidence_=tuple(x.address for x in e.participant_view(ALICE).resolve(obs)))
    develop(e,r)
    return e._practices[p.ref][-1]


def reorganize8(e,key,p,purpose="reorganize"):
    examples=e._practices[p.ref]
    addresses=tuple(x.address for ex in examples for x in e.participant_view(ALICE).resolve(ex["observation"]))
    r=request8(e,key,purpose,p,(SAW,),evidence_=tuple(dict.fromkeys(addresses)))
    develop(e,r)
    return e.job_status(ALICE,key)["development"]


def trained8(e=None, *, reorganize=True):
    e=e or setup8()
    p=e.pattern_view(ALICE)[0] if e.pattern_view(ALICE) else generated(e)
    for i,target in enumerate((SAW2,ObjectRef(BOB,1),GROUP,RULE)):
        release8(e,"release-"+str(i),p,target)
    for i,targets in enumerate(((SAW2,ObjectRef(BOB,1)),(GROUP,RULE))):
        event=respond8(e,"practice-task-"+str(i),p,targets)
        practice8(e,"practice-"+str(i),p,event)
    if reorganize:reorganize8(e,"reorganize",p)
    return e,p


def returned8(e,p):
    for i,targets in enumerate(((MEMORY,POSSIBILITY),(ACTION,OBLIGATION))):
        event=respond8(e,"return-task-"+str(i),p,targets,partner=ObjectRef(EVE,1))
        practice8(e,"return-"+str(i),p,event)
    reorganize8(e,"reown",p,purpose="reown")
    return e
