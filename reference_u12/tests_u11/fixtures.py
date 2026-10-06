"""Declared opportunities and independently practiced primitive skills.

Programs, invitations, disclosure and execution opportunities are harness
inputs. Actual coordination, obligations, effects and retention are outputs.
"""
from tests_u5.fixtures import *
from hle_unified.collective import CollectiveEngine
from hle_unified.collective_records import CollectiveRequest
from hle_unified.operations import indexed
from hle_unified import codec, nesting
from hle_unified.development_values import attrs as unpack

SHARED=ref("u11-shared-tool")
BOB_CARE=ref("u11-bob-care")


def expose(e,actor,obj):
    value=e.world.resolve(obj)
    if value.facet(Material):
        selectors=tuple(Selector(k,"detail",("facets","0",k)) for k in ("owner","custodian","quantity","condition"))
        selectors+=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(value.attributes))
    elif obj.identity.namespace.startswith("u11."):
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="payload")
    else: selectors=(Selector("name","name",("label",)),)
    if e.participant_view(actor).resolve(obj):
        have={p.address.key for p in e.participant_view(actor).resolve(obj)}
        if {s.key for s in selectors}<=have:return
    show(e,actor,obj,key="u11:"+actor.key+":"+obj.identity.namespace+":"+obj.identity.key+":"+str(obj.revision),selectors=selectors)


def setup11(*,budget=2000000,train_bob=True,train_eve=False,tim="iee"):
    base=setup5(prepare=False,budget=budget,tim=tim)
    primitives=("repair","transfer","use","care","consume")
    definitions=tuple(ObjectVersion(ref("u11-primitive-"+n),WRITER,"Primitive "+n,(Role.PROCEDURE,),
        (Procedure(SIGNATURES[n],(),(),(),"u4."+n+".v1"),)) for n in primitives)
    materials=[tool(SHARED,damaged=True,maximum=5),stock(BOB_CARE,"care",8,BOB)]
    for actor in (ALICE,BOB,EVE):
        for name in primitives:
            materials.append(tool(ref("u11-practice-"+actor.key+"-"+name),owner=actor,
                                  damaged=name=="repair",wear=int(name=="care"),maximum=20))
        materials.extend((tool(ref("u11-kit-"+actor.key),owner=actor,maximum=60),
            stock(ref("u11-repair-"+actor.key),"repair",20,actor),
            stock(ref("u11-care-"+actor.key),"care",20,actor),
            stock(ref("u11-consume-"+actor.key),"consume",20,actor)))
    base.world.create("u11-supplied-workshop",WRITER,(*definitions,*materials))
    e=CollectiveEngine(base.world,LAW_REF)
    for actor in (ALICE,BOB,EVE):
        for obj in (ROOM,CUE5,ObjectRef(ALICE,1),ObjectRef(BOB,1),ObjectRef(EVE,1)): expose(e,actor,obj)
        if actor==BOB and not train_bob or actor==EVE and not train_eve:continue
        train(e,actor,primitives)
    return e


def train(e,actor,primitives):
    for name in primitives:
        proc=ref("u11-primitive-"+name)
        show(e,actor,proc,selectors=(Selector("procedure","definition",("facets","0")),))
        roles={"target":ref("u11-practice-"+actor.key+"-"+name)}
        if name=="repair":roles.update(tool=ref("u11-kit-"+actor.key),stock=ref("u11-repair-"+actor.key))
        if name=="care":roles.update(stock=ref("u11-care-"+actor.key))
        if name=="transfer":roles.update(recipient=EVE if actor!=EVE else ALICE)
        if name=="consume":roles={"stock":ref("u11-consume-"+actor.key)}
        for item in roles.values():
            if type(item) is ObjectRef: expose(e,actor,item)
        source=next(v for v in roles.values() if type(v) is ObjectRef)
        event=perform(e,OperationRequest("u11-practice-"+name,actor,name,ROOM,
            participants=tuple(v for k,v in roles.items() if k=="recipient"),evidence=evidence(e,actor,source),**roles))
        receive(e,event,actor,"u11-practice-result-"+actor.key+"-"+name)
        perform(e,OperationRequest("u11-acquire-"+name,actor,"acquire",ROOM,procedure=proc,practice=event))


def work(e,key,purpose,*,actor=ALICE,expect=True,read=True,**kwargs):
    focus=kwargs.get("focus")
    if focus and read: expose(e,actor,focus)
    for item in (*kwargs.get("members",()),*kwargs.get("resources",())):expose(e,actor,item)
    r=CollectiveRequest(key,actor,purpose,ROOM,CUE5,**kwargs)
    perform(e,r,limit=10000000)
    d=e.job_status(actor,key)
    if expect and d["status"]!="succeeded": raise AssertionError((key,d.get("diagnostic"),d["failure"]))
    return tuple(e._records11[r] for r in indexed(d,"output."))


def group(e,key,*,members=(),resources=()):
    return work(e,key,"compose",members=members,resources=resources,boundary="Workshop context; explicit member consent; no transfer of ownership")[0]


def join(e,g,actor=BOB,key="join"):
    g=e._records11[e._heads11[g["ref"].identity]]
    invitation=work(e,key+"-invite","invite",focus=g["ref"],peer=actor)[0]
    values=work(e,key+"-accept","join",actor=actor,focus=invitation["ref"])
    return values[0]


def step(actor,name,**roles):
    return ("work",actor,ref("u11-primitive-"+name),tuple(sorted((k,v.identity if type(v) is ObjectRef else v) for k,v in roles.items())))


def proposed(e,g,program,key="program"):
    for part in program:
        if part[0]=="call":expose(e,ALICE,part[1])
    return work(e,key,"plan",focus=e._heads11[g["ref"].identity],program=program)[0]


def instantiate(e,plan,key="run",mode="aggregate",accept=True):
    run=work(e,key,"instantiate",focus=plan["ref"],mode=mode)[0]
    if accept:
        for actor in dict.fromkeys(row[1] for row in run["agenda"]):
            work(e,key+"-accept-"+actor.key,"accept",actor=actor,focus=run["ref"])
    return run


def select(e,run,key="step",*,details=True):
    scope,actor,_,roles=run["agenda"][run["index"]]
    if details:
        for role,obj in roles:
            if role in ("target","tool","stock","relation"):expose(e,actor,e.world.head(obj).ref)
    return work(e,key+"-select","select",actor=actor,focus=run["ref"])


def perform_step(e,run,key="step"):
    selection,run=select(e,run,key)
    actor=selection["worker"]
    e.enact(key+"-enact",actor,key+"-physical",selection["ref"])
    e.advance(key+"-advance",actor,key+"-physical",1000)
    event=e.commit(key+"-commit",actor,key+"-physical")
    observation=receive(e,event,actor,key+"-observed-"+actor.key)
    if actor!=run["owner"]:receive(e,event,run["owner"],key+"-observed-"+run["owner"].key)
    result=work(e,key+"-settle","observe",actor=actor,focus=run["ref"],observation=observation)
    return result[0]


def finish(e,run,key="execute"):
    while run["status"]=="active":run=perform_step(e,run,key+"-"+str(run["index"]))
    return run


def repair_group(e,key="repair-group"):
    resources=(SHARED,ref("u11-kit-alice"),ref("u11-repair-alice"))
    return group(e,key,resources=tuple(e.world.head(r.identity).ref for r in resources))


def circuit11(*,flat=False):
    e=setup11()
    child=repair_group(e)
    repair_program=(step(ALICE,"repair",target=SHARED,tool=ref("u11-kit-alice"),stock=ref("u11-repair-alice")),)
    plan=proposed(e,child,repair_program,"repair-program")
    run=finish(e,instantiate(e,plan,"repair-run"),"repair")
    capacity=work(e,"retain-repair","retain",focus=run["ref"])[0]
    # Reintroduce a real material demand through an actual paid damage action.
    expose(e,ALICE,e.world.head(SHARED.identity).ref)
    damage=perform(e,OperationRequest("renew-demand",ALICE,"damage",ROOM,target=e.world.head(SHARED.identity).ref,
        evidence=evidence(e,ALICE,e.world.head(SHARED.identity).ref)))
    receive(e,damage,ALICE,"renew-demand")
    root=group(e,"workshop-team",members=(child["ref"],),resources=(e.world.head(SHARED.identity).ref,BOB_CARE))
    root=join(e,root)
    program=(repair_program if flat else (("call",capacity["ref"]),))+(step(ALICE,"transfer",target=SHARED,recipient=BOB),
             step(BOB,"use",target=SHARED),step(BOB,"care",target=SHARED,stock=BOB_CARE))
    plan=proposed(e,root,program,"team-program")
    before=work(e,"before-summary","summarize",focus=root["ref"])[0]
    run=finish(e,instantiate(e,plan,"team-run",mode="detailed" if flat else "aggregate"),"team")
    retained=work(e,"retain-team","retain",focus=run["ref"])[0]
    after=work(e,"after-summary","summarize",focus=root["ref"])[0]
    return e,dict(child=child,root=root,plan=plan,run=run,capacity=retained,child_capacity=capacity,before=before,after=after)
