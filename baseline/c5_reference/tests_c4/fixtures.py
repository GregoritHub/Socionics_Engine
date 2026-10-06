"""C4 opportunities are supplied fixtures, never autonomous route selection."""
from tests_c3.fixtures import *
from tests_c3.fixtures import req as cross_req, expose as cross_expose
from hle_unified.crux_composition_execution import CruxCompositionEngine
from hle_unified.crux_composition_records import CruxCompositionRequest, ChildEvidence
from hle_unified.crux_composition_audit import audit
from hle_unified import crux_composition_content as comp

AUX=ref("c4-auxiliary-supply")


def setup(tim="iee",engine_type=CruxCompositionEngine,**kwargs):
    def factory(world,law):
        world.create("c4-supplied-resources",WRITER,(stock(AUX,"consume",2,ALICE),))
        return engine_type(world,law)
    return setup_c3(tim,engine_type=factory,**kwargs)


def expose4(e,actor,obj):
    v=e.world.resolve(obj)
    if obj.identity.namespace=="c4.message":
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload")
    elif obj.identity.namespace=="u4.operation":
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes)
                        if a.name in ("actor","context","status","spent","result"))
    else: return cross_expose(e,actor,obj)
    if {s.key for s in selectors}<={p.address.key for p in e.participant_view(actor).resolve(obj)}: return
    show(e,actor,obj,key="c4:"+actor.key+":"+obj.identity.key+":"+str(obj.revision),selectors=selectors)


def request(e,key,recipe,inputs,actor=ALICE,**kwargs):
    return CruxCompositionRequest(key,actor,recipe,kwargs.pop("context",ROOM),CUE5,tuple(inputs),
        tuple(p.address for p in e.participant_view(actor).resolve(SAW)),SAW,**kwargs)


def read_data(e,obj,actor=ALICE):
    if obj.identity.namespace.endswith(".message"): return comp.decode(attrs(e.world.resolve(obj))["payload"])
    return comp.decode(e.participant_view(actor)._bindings[obj].content[0].object)


def public4(e,key,actor=ALICE):
    obj=e.job_status(actor,key)["public.0"]
    for who in (ALICE,BOB): expose4(e,who,obj)
    return obj


def exchange_in(e,source,domain,key,g=None,cap=2,consent=True):
    if g is None:
        g=join(e,group(e,key+"-group"),key=key+"-join")["ref"]
        for who in (ALICE,BOB): expose_group(e,who,g)
    work(e,cross_req(e,key+"-offer","offer-"+domain+"-v1",(source,),peer=BOB,group=g,demand=1))
    offer=public4(e,key+"-offer")
    own=seed_intent(e,key+"-receiver",cap=cap,consent=consent,actor=BOB)
    work(e,cross_req(e,key+"-reply","reply-v1",(offer,own),actor=BOB,peer=ALICE,group=g))
    reply=public4(e,key+"-reply",BOB)
    return offer,reply,g


def child(e,key,output,actor=ALICE):
    op=e._jobs[actor,key]; expose4(e,ALICE,op)
    return ChildEvidence(op,output)


def parent_request(e,children,key="case",links=(),**kwargs):
    return request(e,key,"parent-v1",tuple(c.output for c in children),children=tuple(children),links=links,**kwargs)


FAMILIES=("Theorize-Apply-Embody","Share-Commune-Identify","Coordinate-Mobilize","Institutionalize-Educate","Organize-Integrate-Apply")


def family(e,name,key="case"):
    children=[]; links=(); actor=ALICE; group_ref=None; focus=key
    if name==FAMILIES[0]:
        own=seed_intent(e,key+"-intent",cap=4)
        m=work(e,cross_req(e,key,"theorize-accumulation-v1",(own,)))
        event=work(e,cross_req(e,key+"-apply","apply-expenditure-v1",(m,),stock=SUPPLY))
        obs=receive(e,event,ALICE,key+"-trial")
        retained=work(e,cross_req(e,key+"-embody","embody-expenditure-v1",(obs,)))
        children=[child(e,key,m),child(e,key+"-apply",obs),child(e,key+"-embody",retained)]; links=((0,1),(1,2))
        decision=work(e,cross_req(e,key+"-use","use-personal-v1",(retained,),demand=5))
    elif name==FAMILIES[1]:
        own=seed_intent(e,key+"-intent",cap=5)
        offer,reply,g=exchange_in(e,own,"personal",key+"-first"); group_ref=g
        work(e,cross_req(e,key+"-share","share-accumulation-v1",(own,offer,reply),peer=BOB,group=g))
        shared_ref=public4(e,key+"-share")
        renewal=seed_intent(e,key+"-renew-own",cap=1)
        work(e,request(e,key+"-renew","commune-offer-v1",(shared_ref,renewal),peer=BOB,group=g,demand=2))
        offer=public4(e,key+"-renew")
        own_b=seed_intent(e,key+"-renew-b",cap=2,actor=BOB)
        work(e,cross_req(e,key+"-reply","reply-v1",(offer,own_b),actor=BOB,peer=ALICE,group=g))
        reply=public4(e,key+"-reply",BOB)
        work(e,request(e,key,"commune-expenditure-v1",(shared_ref,offer,reply),peer=BOB,group=g))
        renewed=public4(e,key)
        stance=seed_intent(e,key+"-stance",cap=5)
        retained=work(e,cross_req(e,key+"-identify","identify-expenditure-v1",(renewed,stance),peer=BOB,group=g))
        children=[child(e,key+"-share",shared_ref),child(e,key,renewed),child(e,key+"-identify",retained)]; links=((0,1),(1,2))
        decision=work(e,cross_req(e,key+"-use","use-personal-v1",(retained,),demand=5))
    elif name==FAMILIES[2]:
        obs=inspect(e,key+"-observation")
        offer,reply,g=exchange_in(e,obs,"observation",key+"-exchange"); group_ref=g
        work(e,cross_req(e,key,"coordinate-expenditure-v1",(obs,offer,reply),peer=BOB,group=g))
        shared_ref=public4(e,key)
        event=work(e,cross_req(e,key+"-mobilize","mobilize-expenditure-v1",(shared_ref,),stock=SUPPLY,peer=BOB,group=g))
        observed=receive(e,event,ALICE,key+"-physical")
        children=[child(e,key,shared_ref),child(e,key+"-mobilize",observed)]; links=((0,1),)
        decision=work(e,cross_req(e,key+"-use","use-observation-v1",(observed,),demand=10))
    elif name==FAMILIES[3]:
        proposal,g=draft(e,key+"-draft"); group_ref=g
        ballot=votes(e,proposal,g,key+"-vote")
        rule=work(e,cross_req(e,key,"institutionalize-expenditure-v1",(proposal,*ballot),peer=BOB,group=g))
        offer,reply,g=exchange_in(e,rule,"system",key+"-learning",g=g,cap=5)
        work(e,cross_req(e,key+"-educate","educate-accumulation-v1",(rule,offer,reply),peer=BOB,group=g))
        taught=public4(e,key+"-educate")
        children=[child(e,key,rule),child(e,key+"-educate",taught)]; links=((0,1),)
        actor=BOB
        decision=work(e,cross_req(e,key+"-use","use-shared-v1",(taught,),actor=BOB,peer=ALICE,group=g,demand=4))
    elif name==FAMILIES[4]:
        a=inspect(e,key+"-observation-a"); b=inspect(e,key+"-observation-b",resource=AUX)
        m1=work(e,cross_req(e,key+"-organize-a","organize-expenditure-v1",(a,)))
        m2=work(e,cross_req(e,key+"-organize-b","organize-expenditure-v1",(b,)))
        combined=work(e,request(e,key,"integrate-expenditure-v1",(m1,m2)))
        event=work(e,cross_req(e,key+"-apply","apply-expenditure-v1",(combined,),stock=SUPPLY,demand=4))
        observed=receive(e,event,ALICE,key+"-concrete")
        children=[child(e,key+"-organize-a",m1),child(e,key,combined),child(e,key+"-apply",observed)]; links=((0,1),(1,2))
        decision=work(e,cross_req(e,key+"-use","use-observation-v1",(observed,),demand=10))
    else: raise ValueError(name)
    # Review the very children used by this circuit; no supplied intermediate meanings.
    parent=work(e,parent_request(e,children,key+"-parent",links,group=group_ref))
    return dict(name=name,focus=focus,decision=decision,actor=actor,outcome=data(e,decision,actor)["amount"],
                children=tuple(children),parent=parent,links=links)


def nested(e,key="case",depth=1,dependencies=2,failed=False,prepare_only=False):
    children=[]
    for i in range(dependencies):
        k=key+"-child-"+str(i)
        own=seed_intent(e,k+"-intent",cap=3+i)
        r=cross_req(e,k,"theorize-accumulation-v1",(own,))
        if failed and i==dependencies-1:
            e.start(k+"-start",r); e.advance(k+"-advance",ALICE,k,1); event=e.cancel(k+"-cancel",ALICE,k)
            out=receive(e,event,ALICE,k+"-observation")
        else: out=work(e,r)
        children.append(child(e,k,out))
    r=parent_request(e,children,key)
    if prepare_only: return r
    original=children[0].output
    parent=work(e,r)
    first_parent=parent
    for i in range(1,depth):
        prior_key=key if i==1 else key+"-level-"+str(i-1)
        r=parent_request(e,(child(e,prior_key,parent),),key+"-level-"+str(i))
        parent=work(e,r)
    # The first parent's exact model child is released; higher parents certify
    # the evidence organization and do not manufacture another model.
    release=work(e,request(e,key+"-release","release-v1",(first_parent,original)))
    decision=work(e,cross_req(e,key+"-use","use-system-v1",(release,),demand=5))
    return dict(name="Nested accountability",focus=key,parent=parent,first_parent=first_parent,
                decision=decision,actor=ALICE,outcome=data(e,decision)["amount"],children=tuple(children))


def context_case(e,key="case",prepare_only=False):
    other=ref("c4-other-context")
    e.declare("other-context",(ObjectVersion(other,WRITER,"A separate task context",(Role.CONTEXT,)),))
    show(e,ALICE,other)
    model_ref=model(e,key+"-source",cap=5)
    own=seed(e,key+"-local",comp.encode(dict(kind="intention",cap=1,consent=True)),context=other,relation="c3.data",status=ClaimStatus.TENTATIVE)
    event=perform(e,OperationRequest(key+"-local-observe",ALICE,"inspect",other,target=SUPPLY,evidence=evidence(e,ALICE,SUPPLY)))
    obs=receive(e,event,ALICE,key+"-local-result")
    r=request(e,key,"context-transfer-v1",(model_ref,own,obs),context=other)
    if prepare_only: return r
    moved=work(e,r)
    use=replace(cross_req(e,key+"-use","use-system-v1",(moved,),demand=4),context=other)
    decision=work(e,use)
    return dict(name="Context transfer",focus=key,parent=None,decision=decision,actor=ALICE,
                outcome=data(e,decision)["amount"],output=moved,source=model_ref,context=other)


def before_request(e,key):
    """Replay a complete witness to the exact declared operation boundary."""
    q=type(e)(OperationStore.restore(e._initial),LAW_REF)
    for command,_ in e._commands.values():
        if command[0]=="start" and getattr(command[2],"key",None)==key:
            return q,command[2]
        q._execute(command)
    raise AssertionError(key)


class Ablated(CruxCompositionEngine):
    """Matched-cost evaluator interventions, never accepted by raw audit."""
    def _semantic_step(self,name,p,previous):
        result=super()._semantic_step(name,p,previous)
        if p.get("request") and p["request"].key=="case" and (name.startswith("realize:") or name.startswith("retain:")):
            kind,target,values=result; d=comp.decode(values["payload"])
            if d["kind"]=="nested": d.update(complete=False,status="blocked")
            elif p["recipe"].name=="Integrate": d["cap"]=6
            elif p["recipe"].name=="Commune": d["cap"]=2
            else: d["cap"]=1
            return kind,target,{"payload":comp.encode(d)}
        return result
