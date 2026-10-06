"""Supplied finite maintenance/teaching setting; never claimed as emergence."""
from tests_c3.fixtures import *
from tests_c3.fixtures import expose as old_expose
from hle_unified.workflow_execution import WorkflowEngine
from hle_unified.workflow_records import WorkflowRequest, WORKFLOW_RECIPES, PATHS, FACES
from hle_unified import workflow_content as wf

DEVICE=ref("workflow-device");LOAN=ref("workflow-loan");DUE=ref("workflow-due")

def setup_workflow(tim="iee",engine_type=WorkflowEngine,budget=200000,inactive=0,shared=False):
    def factory(world,law):
        due=ObjectVersion(DUE,WRITER,"Restore owner's access to loan",(Role.COMMITMENT,),
            (Relation("return_due",(Endpoint("borrower",ObjectRef(ALICE,1)),Endpoint("owner",ObjectRef(BOB,1)),
                Endpoint("item",LOAN)),True,ROOM,TimeScope(Moment(0,0),None),(Attribute("status","open"),)),))
        world.create("workflow-equipment",WRITER,(tool(DEVICE,wear=1,maximum=12),tool(LOAN,owner=BOB,holder=ALICE,wear=1,maximum=12),due))
        return engine_type(world,law)
    e=setup_c3(tim,engine_type=factory,budget=budget,inactive=inactive,shared=shared)
    for actor in (ALICE,BOB):
        for obj in (DEVICE,LOAN,DUE,CARE): expose(e,actor,obj)
    return e

def expose(e,actor,obj):
    if obj.identity.namespace=="c7w.message":
        v=e.world.resolve(obj)
        if any(p.address.key=="payload" for p in e.participant_view(actor).resolve(obj)): return
        show(e,actor,obj,key="workflow:"+actor.key+":"+obj.identity.key,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload"))
    else: old_expose(e,actor,obj)

def tasks(actor=ALICE):
    return (("maintain","care",(),0,2,actor),("handover","transfer",("maintain",),1,4,actor))

def authored(e,key,rows=None,actor=ALICE,target=DEVICE,consent=True,hypothetical=False,kind="intention"):
    value=dict(kind=kind,tasks=tasks() if rows is None else rows,consent=consent,hypothetical=hypothetical)
    wf.authored(value)
    return seed(e,key,wf.encode(value),actor=actor,target=target,relation="c7w.data",status=ClaimStatus.TENTATIVE)

def request(e,key,name,face,inputs,actor=ALICE,target=DEVICE,**kw):
    recipe="workflow-"+name.lower()+"-"+face+"-v1" if face else "workflow-"+name+"-v1"
    return WorkflowRequest(key,actor,recipe,ROOM,CUE5,tuple(inputs),tuple(p.address for p in e.participant_view(actor).resolve(target)),target,**kw)

def work(e,r,allow_failure=False):
    perform(e,r,limit=1000000); d=e.job_status(r.actor,r.key)
    if not allow_failure and d["status"]!="succeeded": raise AssertionError((r.key,d["failure"]))
    return d.get("binding") or d["result"]

def data(e,ref,actor=ALICE):
    if ref.identity.namespace=="c7w.message": return wf.decode(attrs(e.world.resolve(ref))["payload"])
    return wf.decode(e.participant_view(actor)._bindings[ref].content[0].object)

def observe(e,key,target=DEVICE,primitive="inspect",participants=()):
    current=e.world.head(target.identity).ref;expose(e,ALICE,current)
    stock_ref=e.world.head(CARE.identity).ref if primitive=="care" else None
    if stock_ref: expose(e,ALICE,stock_ref)
    event=perform(e,OperationRequest(key,ALICE,primitive,ROOM,participants=participants,target=current,stock=stock_ref,evidence=evidence(e,ALICE,current)),limit=100000)
    assert e.job_status(ALICE,key)["status"]=="succeeded"
    return receive(e,event,ALICE,key)

def model(e,key,rows=None,target=DEVICE):
    own=authored(e,key+"-intent",rows,target=target,hypothetical=True)
    return work(e,request(e,key,"Theorize","accumulation",(own,),target=target))

def exchange(e,source,key,domain="personal",g=None,target=DEVICE,consent=True):
    if g is None:
        g=join(e,group(e,key+"-group"),key=key+"-join")["ref"]
        for actor in (ALICE,BOB): expose_group(e,actor,g)
    if domain=="activity":
        d,_=e._read_workflow(e.participant_view(ALICE),source,request(e,"shape","Embody","accumulation",(source,),target=target))
        rows=wf.readiness(d)
    else: rows=data(e,source)["tasks"] if source.identity.namespace.startswith("c7w.") else wf.decode(e.participant_view(ALICE)._bindings[source].content[0].object)["tasks"]
    a=authored(e,key+"-own",rows,target=target,kind="stance")
    work(e,request(e,key+"-offer","offer-"+domain,None,(source,a),peer=BOB,group=g,target=target,completed=(rows[0][0],),clock=1))
    offer=e.job_status(ALICE,key+"-offer")["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,offer)
    b=authored(e,key+"-peer",rows,actor=BOB,target=target,kind="stance",consent=consent)
    work(e,request(e,key+"-reply","reply",None,(offer,b),actor=BOB,peer=ALICE,group=g,target=target))
    reply=e.job_status(BOB,key+"-reply")["public.0"];expose(e,ALICE,reply)
    return offer,reply,g

def shared(e,key,target=DEVICE,consent=True):
    own=authored(e,key+"-intent",target=target)
    offer,reply,g=exchange(e,own,key,target=target,consent=consent)
    work(e,request(e,key,"Share","expenditure",(own,offer,reply),peer=BOB,group=g,target=target))
    public=e.job_status(ALICE,key)["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,public)
    return public,g

def draft(e,key):
    source,g=shared(e,key+"-shared")
    obs=observe(e,key+"-practice",primitive="care",participants=(BOB,))
    result=work(e,request(e,key,"Institutionalize","accumulation",(source,obs),group=g,peer=BOB))
    public=e.job_status(ALICE,key)["public.0"]
    for actor in (ALICE,BOB): expose(e,actor,public)
    return public,g

def votes(e,source,g,key,consent=True):
    refs=[]
    for actor,peer in ((ALICE,BOB),(BOB,ALICE)):
        own=authored(e,key+actor.key+"-own",actor=actor,kind="stance",consent=consent if actor==BOB else True)
        work(e,request(e,key+actor.key,"vote",None,(source,own),actor=actor,peer=peer,group=g))
        v=e.job_status(actor,key+actor.key)["public.0"];expose(e,ALICE,v);refs.append(v)
    return tuple(refs)

def cell(e,name,face,key="case",prepare_only=False,consumer=True,consent=True):
    target=LOAN if name=="Act" and face=="accumulation" else DEVICE;extra={}
    if name=="Contemplate":
        inputs=(authored(e,key+"-one",target=target),authored(e,key+"-two",target=target,hypothetical=face=="expenditure"))
    elif name in ("Express","Share","Theorize"):
        inputs=(authored(e,key+"-intent",target=target),)
    elif name in ("Embody","Coordinate","Act"):
        inputs=(observe(e,key+"-observed",target=target),)
    elif name=="Organize":
        first=observe(e,key+"-care",primitive="care"); second=observe(e,key+"-use",primitive="use")
        inputs=(first,second)
    elif name in ("Apply","Understand","Educate"):
        inputs=(model(e,key+"-model"),)
    elif name in ("Identify","Mobilize","Commune"):
        source,g=shared(e,key+"-shared",consent=consent);inputs=(source,);extra=dict(peer=BOB,group=g)
    elif name=="Integrate":
        rows=tasks();inputs=(model(e,key+"-maintenance",rows[:1]),model(e,key+"-handover",rows[1:]))
    elif name=="Institutionalize":
        if face=="accumulation":
            source,g=shared(e,key+"-shared");obs=observe(e,key+"-practice",primitive="care",participants=(BOB,));inputs=(source,obs)
        else:
            source,g=draft(e,key+"-draft");inputs=(source,*votes(e,source,g,key+"-vote",consent=consent))
        extra=dict(peer=BOB,group=g)
    if name in ("Share","Coordinate","Educate","Commune"):
        offer,reply,g=exchange(e,inputs[0],key+"-exchange",domain={"Share":"personal","Coordinate":"activity","Educate":"system","Commune":"shared"}[name],
            g=extra.get("group"),target=target,consent=consent)
        inputs=(inputs[0],offer,reply);extra=dict(peer=BOB,group=g)
    if name in ("Identify","Understand"):
        inputs=(*inputs,authored(e,key+"-stance",kind="stance",consent=consent))
    if name in ("Express","Mobilize","Apply") and face=="expenditure":extra["stock"]=e.world.head(CARE.identity).ref
    if name=="Act":
        extra["peer"]=BOB
        if face=="accumulation": extra["relation"]=DUE
    if name in ("Express","Mobilize","Apply","Act"):
        target=e.world.head(target.identity).ref;expose(e,ALICE,target)
    r=request(e,key,name,face,inputs,target=target,**extra)
    if prepare_only:return dict(request=r,inputs=inputs,extra=extra)
    result=work(e,r,allow_failure=True);out=dict(request=r,result=result,inputs=inputs,extra=extra)
    if not consumer:return out
    return consume_result(e,out)

def consume_result(e,out):
    r=out["request"];recipe=WORKFLOW_RECIPES[r.recipe];d=e.job_status(r.actor,r.key)
    actor=ALICE; source=out["result"];target=r.target;kw={k:v for k,v in out["extra"].items() if k in ("peer","group")}
    if recipe.destination=="IT":
        source=receive(e,source,ALICE,r.key+"-observed-result")
        if recipe.name=="Act":
            # Actual new custody enables this independently paid material use.
            current=e.world.head(target.identity).ref;expose(e,BOB,current)
            event=perform(e,OperationRequest(r.key+"-owner-use",BOB,"use",ROOM,target=current,evidence=evidence(e,BOB,current)),limit=100000)
            out["owner_use"]=e.job_status(BOB,r.key+"-owner-use")["status"]
            out["owner_event"]=event
        kw={}
    elif recipe.destination=="WE":
        source=d["public.0"];actor=BOB;kw["peer"]=ALICE;expose(e,actor,source)
    if recipe.destination!="IT":
        # The question is fixed by the declared case, including in the ablation.
        # It never derives its hypothetical completion from the changed output.
        completed=() if recipe.name in ("Embody","Coordinate") else ("care-0",) if recipe.name=="Organize" else ("maintain",)
        clock=1 if completed else 0
    else: completed=();clock=0
    domain={"I":"personal","IT":"activity","WE":"shared","ITS":"system"}[recipe.destination]
    decision=work(e,request(e,r.key+"-consumer","use-"+domain,None,(source,),actor=actor,target=target,completed=completed,clock=clock,**kw))
    out.update(downstream=decision,consumer_actor=actor,consequence=data(e,decision,actor));return out

class Ablated(WorkflowEngine):
    """Deliberate evaluator intervention; normal raw semantics must reject it."""
    def _semantic_step(self,name,p,previous):
        result=super()._semantic_step(name,p,previous)
        if p.get("c7w") and p["request"].key=="case" and (name.startswith("resolve:") or len(p["recipe"].steps)==1):
            kind,target,values=result; value=wf.decode(values["payload"])
            resolved=value["kind"]=="resolved_work"; d=wf.decode(value["content"]) if resolved else value
            d.update(tasks=(),feasible=False,authorized=False)
            if d["kind"]=="command": d["kind"]="withheld_command"
            if resolved: value["content"]=wf.encode(d)
            else:value=d
            return kind,target,{"payload":wf.encode(value)}
        return result
