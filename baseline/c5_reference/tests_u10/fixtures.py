"""Declared workshop opportunities; complete procedures are runtime outputs."""
from tests_u9.fixtures import *
from hle_unified.grounded_language import LanguageEngine
from hle_unified.language_records import LanguageRequest
from hle_unified import language_semantics as sem, codec


def setup10(*, train_bob=True, hidden_max=1, budget=20000000, tim="iee"):
    base = setup5(tim=tim,budget=budget,prepare=False)
    definitions = tuple(ObjectVersion(ref("primitive-"+n),WRITER,"Primitive "+n,(Role.PROCEDURE,),
        (Procedure(SIGNATURES[n],(),(),(),"u4."+n+".v1"),)) for n in ("use","care","repair","return"))
    materials=[]
    for actor, cases in ((ALICE,(("train",3),("transfer",4),("counter",1),("return",1),("old-return",4),("repair-demo",1))),
                         (BOB,(("bob-first",5),("bob-fragile",hidden_max),("bob-later",1),("bob-safe",6),("bob-promise",5),("bob-composed",7)))):
        for name,maximum in cases:
            materials.extend((tool(ref(name),owner=actor,damaged=True,maximum=maximum),
                tool(ref(name+"-kit"),owner=actor,maximum=100),stock(ref(name+"-repair"),"repair",100,actor),
                stock(ref(name+"-care"),"care",100,actor)))
        for name in ("use","care","repair"):
            materials.append(tool(ref(actor.key+"-practice-"+name),owner=actor,damaged=name=="repair",wear=int(name=="care")))
        materials.extend((tool(ref(actor.key+"-practice-kit"),owner=actor,maximum=100),
            stock(ref(actor.key+"-practice-repair-stock"),"repair",100,actor),
            stock(ref(actor.key+"-practice-care-stock"),"care",100,actor)))
    base.world.create("supplied-u10-workshop",WRITER,(*definitions,*materials))
    e=LanguageEngine(base.world,LAW_REF)
    for actor in (ALICE,BOB):
        for obj in (ROOM,CUE5,ObjectRef(ALICE,1),ObjectRef(BOB,1)):show(e,actor,obj)
        if actor==BOB and not train_bob:continue
        for name in ("use","care","repair"):
            proc=ref("primitive-"+name)
            show(e,actor,proc,selectors=(Selector("procedure","definition",("facets","0")),))
            roles={"target":ref(actor.key+"-practice-"+name)}
            if name=="repair":roles.update(tool=ref(actor.key+"-practice-kit"),stock=ref(actor.key+"-practice-repair-stock"))
            if name=="care":roles.update(stock=ref(actor.key+"-practice-care-stock"))
            for obj in roles.values():
                if not e.participant_view(actor).resolve(obj):show(e,actor,obj)
            event=perform(e,OperationRequest("practice-"+name,actor,name,ROOM,evidence=evidence(e,actor,roles["target"]),**roles))
            receive(e,event,actor,actor.key+"-primitive-"+name)
            perform(e,OperationRequest("acquire-"+name,actor,"acquire",ROOM,procedure=proc,practice=event))
    return e


def work10(e,key,purpose,*,actor=ALICE,**kwargs):
    r=LanguageRequest(key,actor,purpose,ROOM,CUE5,**kwargs)
    perform(e,r,limit=10000000)
    d=e.job_status(actor,key)
    if d["status"]!="succeeded":raise AssertionError((key,d["failure"]))
    return tuple(e._language[x] for x in indexed9(d,"output."))


def work9(e,key,purpose,*,actor=ALICE,**kwargs):
    perform(e,CompositionRequest(key,actor,purpose,ROOM,CUE5,**kwargs),limit=10000000)
    d=e.job_status(actor,key)
    if d["status"]!="succeeded":raise AssertionError((key,d["failure"]))
    return tuple(e._construct[x] for x in indexed9(d,"output."))


def expose(e,actor,obj):
    v=e.world.resolve(obj)
    selectors=tuple(Selector(n,"detail",("facets","0",n)) for n in ("owner","custodian","quantity","condition"))+tuple(
        Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes))
    # Each immutable exact revision needs only one paid read.
    if {"max_wear","purpose"} & {p.address.key for p in e.participant_view(actor).resolve(obj)}:return
    show(e,actor,obj,key=actor.key+":details:"+obj.identity.key+":"+str(obj.revision),selectors=selectors)


def reveal10(e,key,*,actor=ALICE):
    slots=tuple((slot,e.world.head(obj.identity).ref) for slot,obj in slots9(key))
    for _,obj in slots:expose(e,actor,obj)
    return slots


def deliver10(e,message,*,read=True):
    actor=message["receiver"];obj=e.world.resolve(message["ref"])
    selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(obj.attributes) if a.name in ("payload","wording"))
    key="utterance:"+actor.key+":"+obj.ref.identity.key
    e.disclose("show:"+key,actor,obj.ref,selectors)
    if read:perform(e,OperationRequest("read:"+key,actor,"read",ROOM,delivery="show:"+key),limit=10000)
    return key


def expose_demo(e,message):
    wire=dict(codec.loads(message["payload"]));actor=message["receiver"]
    expose(e,actor,wire["target"])
    for event in wire["events"]:
        if e.participant_view(actor).resolve(event):continue
        obj=e.world.resolve(event)
        show(e,actor,event,key=actor.key+":demo:"+event.identity.key,selectors=tuple(
            Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(obj.attributes)))


def teacher10(e=None):
    e=e or setup10()
    e,cap=trained9(e)
    original=e._construct[cap["practice"]]
    d=notice9(e,"transfer");second=run9(e,d,cap,prefix="second")
    entry=work10(e,"coin","coin",focus=cap["ref"])[0]
    return e,dict(capacity=cap,entry=entry,runs=(original,second))


def teach10(e,entry,runs,*,prefix="teach"):
    entries=[]
    for i,run in enumerate(runs):
        message=work10(e,prefix+"-demo-"+str(i),"send",peer=BOB,act="demonstration",focus=run["ref"],term=entry["term"])[0]
        deliver10(e,message);expose_demo(e,message)
        entries.append(work10(e,prefix+"-learn-"+str(i),"learn",actor=BOB,focus=message["ref"])[0])
    return entries


def request10(e,entry,key="bob-first",*,prefix="request",body=None,goal=GOAL):
    slots=reveal10(e,key,actor=ALICE);reveal10(e,key,actor=BOB)
    message=work10(e,prefix+"-send","send",peer=BOB,act="request",body=body or ("word",entry["term"]),slots=slots,goal=goal)[-1]
    deliver10(e,message)
    interpreted=work10(e,prefix+"-interpret","interpret",actor=BOB,focus=message["ref"])[0]
    return message,interpreted


def response10(e,interpreted,*,prefix="response"):
    return work10(e,prefix,"respond",actor=BOB,focus=interpreted["ref"])[-1]


def enact_response10(e,response,*,prefix="listener",steps=None):
    run=work9(e,prefix+"-instantiate","instantiate",actor=BOB,focus=response["demand"],item=response["candidate"],limit=32,depth=16)[0]
    return continue10(e,run,prefix=prefix,steps=steps)


def continue10(e,run,*,prefix="listener",steps=None):
    actor=run["actor"];count=0
    while run["status"]=="active":
        if steps is not None and count>=steps:break
        i=run["index"];key=prefix+"-"+str(i)
        plan,run=work9(e,key+"-select","select",actor=actor,focus=run["ref"])
        e.enact(key+"-enact",actor,key+"-physical",plan["ref"])
        e.advance(key+"-work",actor,key+"-physical",10000)
        event=e.commit(key+"-commit",actor,key+"-physical")
        obs=receive(e,event,actor,key)
        run=work9(e,key+"-observe","observe",actor=actor,focus=run["ref"],observation=obs)[0]
        count+=1
    return run


def repair10(e,teacher,*,prefix="repair"):
    # The teacher separately tests the reported material distinction. Its U9
    # revision still requires its own observed failure and independent practice.
    demand=notice9(e,"counter")
    failed=run9(e,demand,teacher["capacity"],prefix=prefix+"-teacher-failure")
    general=next(d for d in e.composition_view(ALICE) if d.get("origin")==failed["ref"] and d["reason"]=="failed_generalization")
    candidate=find9(e,general,prefix=prefix+"-search")
    d=notice9(e,"return");tested=run9(e,d,candidate,prefix=prefix+"-test")
    revised=do9(e,prefix+"-retain","retain",focus=tested["ref"])[0]
    d=do9(e,prefix+"-notice-extra","notice",slots=reveal10(e,"repair-demo"),goal=GOAL)[0]
    second=run9(e,d,revised,prefix=prefix+"-second")
    entry=work10(e,prefix+"-coin","coin",focus=revised["ref"],term=teacher["entry"]["term"])[0]
    learned=teach10(e,entry,(tested,second),prefix=prefix+"-teach")
    return dict(capacity=revised,entry=entry,learned=learned,teacher_failure=failed)


def circuit10():
    e,t=teacher10()
    message,unknown=request10(e,t["entry"],prefix="unknown")
    questions=[x for x in e.language_view(BOB) if x["kind"]=="message" and x["act"]=="clarification"]
    deliver10(e,questions[-1]);heard=work10(e,"hear-question","interpret",focus=questions[-1]["ref"])[0]
    learned=teach10(e,t["entry"],t["runs"])
    message,understood=request10(e,t["entry"],prefix="known")
    response=response10(e,understood);first=enact_response10(e,response)
    body=("seq",(("word",t["entry"]["term"]),("act","use"),("act","care")))
    new_goal=(("ge",("field","progress","uses"),2),*GOAL[1:])
    _,novel=request10(e,t["entry"],"bob-composed",prefix="novel-composition",body=body,goal=new_goal)
    response=response10(e,novel,prefix="novel-response")
    composed=enact_response10(e,response,prefix="novel-run")
    _,broad=request10(e,t["entry"],"bob-fragile",prefix="fragile")
    response=response10(e,broad,prefix="fragile-response");failed=enact_response10(e,response,prefix="fragile-run")
    challenged,report=work10(e,"challenge","challenge",actor=BOB,focus=failed["ref"])
    deliver10(e,report);expose_demo(e,report)
    received=work10(e,"hear-counterexample","interpret",focus=report["ref"])[0]
    revision=repair10(e,t)
    returns=[]
    for key in ("bob-later","bob-safe"):
        _,interpreted=request10(e,revision["entry"],key,prefix=key)
        response=response10(e,interpreted,prefix=key+"-response")
        returns.append(enact_response10(e,response,prefix=key+"-run"))
    return e,dict(teacher=t,unknown=unknown,question=heard,learned=learned,first=first,composed=composed,failed=failed,
        challenged=challenged,report_received=received,revision=revision,returns=returns)
