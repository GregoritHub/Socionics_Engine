"""Declared C2 fixtures, separate from participant policy and raw audit."""
from dataclasses import replace
from tests_c1.fixtures import *
from hle_unified.self_execution import SelfRouteEngine
from hle_unified.self_records import SelfRouteRequest
from hle_unified import self_content as sem
from hle_unified.operations import indexed
from tests_u11.fixtures import group,join,expose as expose_group


def setup_c2(tim="iee",*,actual="damaged",budget=100000,engine_type=SelfRouteEngine,inactive=0,shared=False):
    def construct(world,law):
        world.create("c2-bob-supplied-stock",WRITER,(stock(ref("bob-consumables"),"consume",10,BOB),))
        return engine_type(world,law)
    e=setup_c1(tim,actual=actual,budget=budget,engine_type=construct,inactive=inactive,shared=shared)
    # Bob's private capacity and consumables are an explicit fixture, not created by dialogue.
    for actor in (ALICE,BOB):
        for obj in (ROOM,CUE5,ObjectRef(ALICE,1),ObjectRef(BOB,1)):
            if not e.participant_view(actor).resolve(obj): show(e,actor,obj)
    return e


def expose(e,actor,obj):
    v=e.world.resolve(obj)
    if obj.identity.namespace=="c2.message":
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload")
    elif v.facet(Material):
        selectors=tuple(Selector(k,"detail",("facets","0",k)) for k in ("owner","custodian","condition"))
        selectors+=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes))
    else:
        return expose_group(e,actor,obj)
    if {s.key for s in selectors}<={p.address.key for p in e.participant_view(actor).resolve(obj)}: return
    show(e,actor,obj,key="c2:"+actor.key+":"+obj.identity.key+":"+str(obj.revision),selectors=selectors)


def seed_data(e,key,data,*,actor=ALICE,target=SAW):
    if not e.participant_view(actor).resolve(target): show(e,actor,target)
    sem.validate(data,actor,target)
    return seed(e,key,sem.encode(data),actor=actor,target=target,relation="c2.data",status=ClaimStatus.TENTATIVE)


def req(e,key,recipe,inputs,*,actor=ALICE,target=SAW,**kwargs):
    ev=tuple(p.address for p in e.participant_view(actor).resolve(target))
    return SelfRouteRequest(key,actor,recipe,ROOM,CUE5,tuple(inputs),ev,target,**kwargs)


def work(e,r):
    perform(e,r,limit=1000000)
    d=e.job_status(r.actor,r.key)
    if d["status"]!="succeeded": raise AssertionError((r.key,d["failure"]))
    return d.get("binding") or d["result"]


def data(e,ref,actor=ALICE):
    if ref.identity.namespace=="c2.message":
        return sem.decode(attrs(e.world.resolve(ref))["payload"])
    return sem.decode(e.participant_view(actor)._bindings[ref].content[0].object)


def consume(e,source,key="consumer",*,actor=ALICE,target=SAW,**kwargs):
    return work(e,req(e,key,"content-use-v1",(source,),actor=actor,target=target,**kwargs))


def cell(e,name,polarity,*,prefix="case",target=SAW,consumer=True,consent=True,cap=2,prepare_only=False):
    recipe=name.lower()+"-"+polarity+"-v1"
    extra={}; inputs=()
    if name=="Contemplate":
        a=seed_data(e,prefix+"-prior",dict(kind="personal",condition="serviceable",hypothetical=False),target=target)
        b=seed_data(e,prefix+"-alternative",dict(kind="personal",condition="damaged",hypothetical=polarity=="expenditure"),target=target)
        inputs=(a,b)
    elif name=="Act":
        inputs=(target,KIT,STOCK) if polarity=="accumulation" else (target,)
        if polarity=="accumulation": extra=dict(tool=KIT,stock=STOCK)
    elif name=="Commune":
        g=join(e,group(e,prefix+"-group"),key=prefix+"-join")
        for actor in (ALICE,BOB): expose_group(e,actor,g["ref"])
        a=seed_data(e,prefix+"-alice",dict(kind="stance",cap=5,consent=True),target=target)
        b=seed_data(e,prefix+"-bob",dict(kind="stance",cap=cap,consent=consent),actor=BOB,target=target)
        ar=req(e,prefix+"-offer","exchange-offer-v1",(a,),peer=BOB,group=g["ref"],target=target)
        work(e,ar); offer=e.job_status(ALICE,ar.key)["public.0"]
        for actor in (ALICE,BOB): expose(e,actor,offer)
        br=req(e,prefix+"-reply","exchange-reply-v1",(b,offer),actor=BOB,peer=ALICE,group=g["ref"],target=target)
        work(e,br); reply=e.job_status(BOB,br.key)["public.0"]
        expose(e,ALICE,reply)
        inputs=(offer,reply); extra=dict(peer=BOB,group=g["ref"])
    elif name=="Integrate":
        a=seed_data(e,prefix+"-maintenance",dict(kind="system",nodes=(("restore",("damaged",),("serviceable",),"repair",ALICE),)),target=target)
        b=seed_data(e,prefix+"-work",dict(kind="system",nodes=(("perform",("serviceable",),("used",),"use",ALICE),)),target=target)
        inputs=(a,b)
    r=req(e,prefix,recipe,inputs,target=target,**extra)
    if prepare_only: return dict(request=r,inputs=inputs,extra=extra)
    perform(e,r,limit=1000000)
    status=e.job_status(ALICE,r.key)
    result=status.get("binding") or status["result"]
    out=dict(request=r,result=result,inputs=inputs,extra=extra)
    if not consumer: return out
    if name=="Act":
        target=e.world.head(target.identity).ref
        expose(e,ALICE,target)
        event=perform(e,OperationRequest(prefix+"-later",ALICE,"use" if polarity=="accumulation" else "care",ROOM,
            target=target,stock=CARE if polarity=="expenditure" else None,evidence=evidence(e,ALICE,target)),limit=10000)
        out["downstream"]=event
    else:
        if name=="Commune":
            public=e.job_status(ALICE,r.key)["public.0"]
            expose(e,BOB,public)
            # The receiver uses its own paid-read result; no borrowed binding.
            expose(e,BOB,ref("bob-consumables"))
            decision=consume(e,public,prefix+"-later",actor=BOB,target=target,group=extra["group"],demand=4,stock=ref("bob-consumables"))
            out["consumer_actor"]=BOB
            if polarity=="expenditure" and consent:
                out["event"]=enact(e,decision,prefix+"-participate",actor=BOB)
        else:
            expose(e,ALICE,target)
            decision=consume(e,result,prefix+"-later",target=target,tool=KIT,stock=STOCK)
        out["downstream"]=decision
        if name=="Contemplate" or name=="Integrate" and polarity=="expenditure":
            if data(e,decision)["action"]!="none":
                out["event"]=enact(e,decision,prefix+"-action")
            if name=="Integrate" and "event" in out:
                current=e.world.head(target.identity).ref
                receive(e,out["event"],ALICE,prefix+"-restored")
                expose(e,ALICE,current)
                follow=consume(e,result,prefix+"-follow",target=current)
                out["follow"]=follow
                out["follow_event"]=enact(e,follow,prefix+"-follow-action")
    return out


class Ablated(SelfRouteEngine):
    """Evaluator intervention, deliberately rejected by normal semantic audit."""
    def _semantic_step(self,name,p,previous):
        if "request" not in p: return super()._semantic_step(name,p,previous)
        kind,target,values=super()._semantic_step(name,p,previous)
        d=sem.decode(values["payload"])
        if name=="differentiate": d.update(supported=("serviceable",),unresolved=False)
        elif name=="rehearse": d.update(hypothetical=False,unresolved=False)
        elif name=="material_command": d["kind"]="missing"
        elif name in ("clarify","acknowledge"): d.update(cap=5,difference=False,positions=(5,5))
        elif name in ("reconcile","interfaces"):
            d.update(edges=(),order=(),compatible=False)
        return kind,target,{"payload":sem.encode(d)}
