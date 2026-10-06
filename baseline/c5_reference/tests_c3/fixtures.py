"""Declared resource fixtures. Route requests and starting stances are supplied."""
from tests_c2.fixtures import *
from tests_c2.fixtures import cell as cell_c2, expose as expose_c2, req as req_c2
from hle_unified.crossing_execution import CrossingEngine
from hle_unified.crossing_records import CrossingRequest, CROSSING_RECIPES, PATHS, FACES
from hle_unified import crossing_content as cross

SUPPLY=ref("c3-alice-supply")

def setup_c3(tim="iee",budget=200000,engine_type=CrossingEngine,inactive=0,shared=False,quantity=6):
    def factory(world,law):
        world.create("c3-supplied-resources",WRITER,(stock(SUPPLY,"consume",quantity,ALICE),))
        return engine_type(world,law)
    e=setup_c2(tim,budget=budget,engine_type=factory,inactive=inactive,shared=shared)
    for actor in (ALICE,BOB):
        for obj in (SAW,SUPPLY,ref("bob-consumables")): expose(e,actor,obj)
    return e

def expose(e,actor,obj):
    v=e.world.resolve(obj)
    if obj.identity.namespace=="c3.message":
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload")
    elif v.facet(Material):
        selectors=tuple(Selector(k,"detail",("facets","0",k)) for k in ("owner","custodian","condition","quantity"))
        selectors+=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes))
    else: return expose_c2(e,actor,obj)
    if {s.key for s in selectors}<={p.address.key for p in e.participant_view(actor).resolve(obj)}: return
    show(e,actor,obj,key="c3:"+actor.key+":"+obj.identity.key+":"+str(obj.revision),selectors=selectors)

def seed_intent(e,key,cap=3,consent=True,actor=ALICE):
    return seed(e,key,cross.encode(dict(kind="intention",cap=cap,consent=consent)),actor=actor,relation="c3.data",status=ClaimStatus.TENTATIVE)

def req(e,key,recipe,inputs,actor=ALICE,**kwargs):
    return CrossingRequest(key,actor,recipe,ROOM,CUE5,tuple(inputs),tuple(p.address for p in e.participant_view(actor).resolve(SAW)),SAW,**kwargs)

def data(e,ref,actor=ALICE):
    if ref.identity.namespace in ("c3.message","c2.message"): return cross.decode(attrs(e.world.resolve(ref))["payload"])
    return cross.decode(e.participant_view(actor)._bindings[ref].content[0].object)

def work(e,r,allow_failure=False):
    perform(e,r,limit=1000000); d=e.job_status(r.actor,r.key)
    if not allow_failure and d["status"]!="succeeded": raise AssertionError((r.key,d["failure"]))
    return d.get("binding") or d["result"]

def inspect(e,key="observed",actor=ALICE,resource=SUPPLY):
    resource=e.world.head(resource.identity).ref; expose(e,actor,resource)
    event=perform(e,OperationRequest(key,actor,"inspect",ROOM,target=resource,evidence=evidence(e,actor,resource)),limit=10000)
    return receive(e,event,actor,key)

def model(e,key="model",face="accumulation",cap=3):
    intent=seed_intent(e,key+"-intent",cap=cap)
    return work(e,req(e,key,"theorize-"+face+"-v1",(intent,),peer=BOB))

def shared(e,key="shared",consent=True):
    out=cell_c2(e,"Commune","expenditure",prefix=key,consumer=False,consent=consent)
    public=e.job_status(ALICE,key)["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,public)
    return public,out["extra"]["group"]

def exchange(e,source,domain,key,consent=True):
    g=join(e,group(e,key+"-group"),key=key+"-join")
    for actor in (ALICE,BOB): expose_group(e,actor,g["ref"])
    offer=work(e,req(e,key+"-offer","offer-"+domain+"-v1",(source,),peer=BOB,group=g["ref"],demand=1))
    offer=e.job_status(ALICE,key+"-offer")["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,offer)
    own=seed_intent(e,key+"-receiver",cap=2,consent=consent,actor=BOB)
    work(e,req(e,key+"-reply","reply-v1",(offer,own),actor=BOB,peer=ALICE,group=g["ref"]))
    reply=e.job_status(BOB,key+"-reply")["public.0"]; expose(e,ALICE,reply)
    return offer,reply,g["ref"]

def draft(e,key="draft",consent=True):
    source,g=shared(e,key+"-shared",consent=consent)
    current=e.world.head(SUPPLY.identity).ref; expose(e,ALICE,current)
    event=perform(e,OperationRequest(key+"-practice",ALICE,"consume",ROOM,participants=(BOB,),stock=current,amount=1,
        evidence=evidence(e,ALICE,current)),limit=10000)
    obs=receive(e,event,ALICE,key+"-practice-a")
    receive(e,event,BOB,key+"-practice-b")
    out=work(e,req(e,key,"institutionalize-accumulation-v1",(source,obs),group=g,peer=BOB))
    public=e.job_status(ALICE,key)["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,public)
    return public,g

def votes(e,proposal,g,key,consent=True):
    result=[]
    for actor in (ALICE,BOB):
        own=seed_intent(e,key+actor.key+"-own",cap=3,consent=consent if actor==BOB else True,actor=actor)
        r=req(e,key+actor.key,"vote-v1",(proposal,own),actor=actor,group=g)
        work(e,r); public=e.job_status(actor,r.key)["public.0"]
        expose(e,ALICE,public); result.append(public)
    return tuple(result)

def cell(e,name,face,key="case",consumer=True,prepare_only=False,consent=True,dependencies=1):
    extra={}; source=None; inputs=None
    if name in ("Express","Theorize","Share"): source=seed_intent(e,key+"-intent",consent=consent)
    elif name in ("Embody","Coordinate","Organize"):
        inputs=tuple(inspect(e,key+"-observation-"+str(i)) for i in range(dependencies)); source=inputs[0]
    elif name in ("Understand","Apply","Educate"): source=model(e,key+"-model")
    elif name in ("Identify","Mobilize"):
        source,g=shared(e,key+"-shared",consent=consent); extra=dict(group=g,peer=BOB)
    elif name=="Institutionalize":
        if face=="expenditure":
            source,g=draft(e,key+"-draft")
            inputs=(source,*votes(e,source,g,key+"-vote",consent=consent)); extra=dict(group=g,peer=BOB)
        else:
            source,g=shared(e,key+"-shared")
            event=perform(e,OperationRequest(key+"-practice",ALICE,"consume",ROOM,participants=(BOB,),stock=SUPPLY,amount=1,
                evidence=evidence(e,ALICE,SUPPLY)),limit=10000)
            obs=receive(e,event,ALICE,key+"-practice-a"); receive(e,event,BOB,key+"-practice-b")
            inputs=(source,obs); extra=dict(group=g,peer=BOB)
    if name in ("Share","Coordinate","Educate"):
        domain={"Share":"personal","Coordinate":"observation","Educate":"system"}[name]
        offer,reply,g=exchange(e,source,domain,key,consent=consent)
        inputs=(source,offer,reply); extra=dict(group=g,peer=BOB)
    elif name in ("Identify","Understand"):
        own=seed_intent(e,key+"-own",cap=9,consent=consent)
        inputs=(source,own)
    if inputs is None: inputs=(source,)
    if name in ("Express","Apply","Mobilize"): extra["stock"]=SUPPLY
    if name in ("Theorize","Organize"): extra["peer"]=BOB
    r=req(e,key,name.lower()+"-"+face+"-v1",inputs,**extra)
    if prepare_only: return dict(request=r,inputs=inputs,extra=extra)
    result=work(e,r,allow_failure=True); out=dict(request=r,result=result,inputs=inputs,extra=extra)
    if not consumer: return out
    actor=ALICE; group_ref=extra.get("group"); peer=BOB if group_ref else None
    destination=PATHS[name][1]
    if destination=="IT":
        source=receive(e,result,ALICE,key+"-received")
        # Query actual remaining stock after performance, or observed readiness
        # after preparation. A failed preparation supplies no readiness fact.
        if face=="expenditure" or name=="Apply": source=inspect(e,key+"-remaining")
        domain="observation"; demand=20
    elif destination=="WE":
        source=e.job_status(ALICE,key)["public.0"]; actor=BOB; peer=ALICE
        expose(e,actor,source); domain="shared"; demand=5
    else:
        source=result; domain="personal" if destination=="I" else "system"; demand=5
    current=e.world.head((SUPPLY if actor==ALICE else ref("bob-consumables")).identity).ref
    expose(e,actor,current)
    decision=work(e,req(e,key+"-later","use-"+domain+"-v1",(source,),actor=actor,stock=current,
        group=group_ref,peer=peer,demand=demand))
    out.update(downstream=decision,consumer_actor=actor)
    d=data(e,decision,actor)
    if d["action"]=="consume": out["event"]=enact(e,decision,key+"-enact",actor=actor)
    return out

class Ablated(CrossingEngine):
    """Evaluator intervention on the designated main case only; paid work held."""
    def _semantic_step(self,name,p,previous):
        result=super()._semantic_step(name,p,previous)
        if p.get("c3") and p["request"].key=="case" and name.startswith("realize:"):
            kind,target,values=result; d=cross.decode(values["payload"])
            if d["kind"]=="material_command": d["kind"]="missing_material_command"
            else: d["cap"]=None
            return kind,target,{"payload":cross.encode(d)}
        return result

def consequence(e,out):
    return data(e,out["downstream"],out["consumer_actor"])["amount"]
