"""Supplied material opportunities and primitive practice, never complete plans."""
from dataclasses import replace
from tests_u5.fixtures import *
from hle_unified.composition import CompositionEngine
from hle_unified.composition_records import CompositionRequest
from hle_unified.composition_language import snapshot, freeze, thaw
from hle_unified.development_values import attrs as unpack

GOAL = (("ge", ("field", "progress", "uses"), 1),
        ("eq", ("field", "target", "condition"), "serviceable"),
        ("eq", ("field", "target", "wear"), 0))


def setup9(*, budget=2000000, tim="iee", train=True, hidden_max=1, tag=""):
    base = setup5(tim=tim, budget=budget, prepare=False)
    definitions = tuple(ObjectVersion(ref("primitive-"+n), WRITER, "Primitive "+n, (Role.PROCEDURE,),
        (Procedure(SIGNATURES[n], (), (), (), "u4."+n+".v1"),)) for n in ("use","care","repair","return"))
    material = []
    for key, maximum in (("train",3),("transfer",4),("counter",hidden_max),("return",1),("old-return",4),("deep",10),("ready-train",3),("ready-return",4),("ready-fragile",1)):
        material += [tool(ref(tag+key), damaged=not key.startswith("ready"), maximum=maximum),
                     tool(ref(tag+key+"-kit"), maximum=100),
                     stock(ref(tag+key+"-repair"),"repair",100), stock(ref(tag+key+"-care"),"care",100)]
    material += [tool(ref("practice-repair"),damaged=True),tool(ref("practice-care"),wear=1),tool(ref("practice-use")),
                 tool(ref("practice-kit"),maximum=100),stock(ref("practice-stock"),"repair",100),stock(ref("practice-care-stock"),"care",100)]
    for key in ("practice-loan","loan"):
        material += [tool(ref(key),owner=BOB,holder=ALICE),
            ObjectVersion(ref(key+"-due"),WRITER,"Received return obligation",(Role.COMMITMENT,),
                (Relation("return_due",(Endpoint("borrower",ObjectRef(ALICE,1)),Endpoint("owner",ObjectRef(BOB,1)),Endpoint("item",ref(key))),
                    True,ROOM,TimeScope(Moment(0,0),None),(Attribute("status","open"),)),))]
    base.world.create("u9-supplied-world",WRITER,(*definitions,*material))
    e = CompositionEngine(base.world, LAW_REF)
    show(e,ALICE,ROOM);show(e,ALICE,CUE5)
    if train:
        for name in ("use","care","repair"):
            proc=ref("primitive-"+name)
            show(e,ALICE,proc,selectors=(Selector("procedure","definition",("facets","0")),))
            roles={"target":ref("practice-"+name)}
            if name=="repair":roles.update(tool=ref("practice-kit"),stock=ref("practice-stock"))
            if name=="care":roles.update(stock=ref("practice-care-stock"))
            for obj in roles.values():show(e,ALICE,obj)
            event=perform(e,OperationRequest("practice-"+name,ALICE,name,ROOM,evidence=evidence(e,ALICE,roles["target"]),**roles))
            receive(e,event,ALICE,"primitive-"+name)
            perform(e,OperationRequest("acquire-"+name,ALICE,"acquire",ROOM,procedure=proc,practice=event))
    return e


def slots9(key="train",tag=""):
    return (("target",ref(tag+key)),("tool",ref(tag+key+"-kit")),
            ("repair_stock",ref(tag+key+"-repair")),("care_stock",ref(tag+key+"-care")))


def reveal9(e,key="train",tag="", *, actor=ALICE):
    for _,obj in slots9(key,tag):
        v=e.world.head(obj.identity)
        selectors=tuple(Selector(n,"detail",("facets","0",n)) for n in ("owner","custodian","quantity","condition"))+tuple(
            Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes))
        show(e,actor,v.ref,selectors=selectors)
    return slots9(key,tag)


def do9(e,key,purpose,**kwargs):
    r=CompositionRequest(key,ALICE,purpose,ROOM,CUE5,**kwargs)
    perform(e,r,limit=10000000)
    d=e.job_status(ALICE,key)
    if d["status"]!="succeeded":raise AssertionError((key,d["failure"]))
    return tuple(e._construct[x] for x in indexed9(d,"output."))


def indexed9(d,prefix):
    return tuple(d[prefix+str(i)] for i in range(sum(k.startswith(prefix) for k in d)))


def notice9(e,key="train",*,tag="",goal=GOAL,prefix=""):
    slots=reveal9(e,key,tag)
    return do9(e,prefix+"notice-"+key,"notice",slots=slots,goal=goal)[0]


def find9(e,demand,*,prefix="search",depth=4,limit=8,tickets=100):
    focus=demand["ref"]
    for i in range(tickets):
        rows=do9(e,prefix+"-"+str(i),"search",focus=focus,depth=depth,limit=limit)
        if rows[-1]["kind"]=="candidate":return rows[-1]
        focus=rows[0]["ref"]
        if rows[0]["status"].startswith("repertoire_exhausted"):return rows[0]
    return rows[0]


def run9(e,demand,program,*,prefix="run"):
    run=do9(e,prefix+"-instantiate","instantiate",focus=demand["ref"],item=program["ref"],limit=32,depth=16)[0]
    return continue9(e,run,prefix=prefix)


def continue9(e,run,*,prefix="run",steps=None):
    count=0
    while run["status"]=="active":
        if steps is not None and count>=steps:break
        i=run["index"];key=prefix+"-"+str(i)
        rows=do9(e,key+"-select","select",focus=run["ref"])
        plan,run=rows
        e.enact(key+"-enact",ALICE,key+"-physical",plan["ref"])
        e.advance(key+"-work",ALICE,key+"-physical",1000)
        event=e.commit(key+"-commit",ALICE,key+"-physical")
        obs=receive(e,event,ALICE,key)
        rows=do9(e,key+"-observe","observe",focus=run["ref"],observation=obs)
        run=rows[0]
        count+=1
    return run


def trained9(e=None):
    e=e or setup9()
    demand=notice9(e)
    candidate=find9(e,demand)
    run=run9(e,demand,candidate)
    capacity=do9(e,"retain","retain",focus=run["ref"])[0]
    return e,capacity


def revised9():
    e,cap=trained9()
    held=notice9(e,"transfer")
    good=run9(e,held,cap,prefix="transfer")
    demand=notice9(e,"counter")
    failed=run9(e,demand,cap,prefix="counter")
    repairs=[d for d in e.composition_view(ALICE) if d.get("origin")==failed["ref"]]
    general=next(d for d in repairs if d["reason"]=="failed_generalization")
    candidate=find9(e,general,prefix="revision-search")
    new=notice9(e,"return")
    tested=run9(e,new,candidate,prefix="revision-test")
    revised=do9(e,"retain-revision","retain",focus=tested["ref"])[0]
    return e,dict(capacity=cap,transfer=good,failed=failed,repair_demands=tuple(repairs),candidate=candidate,revised=revised)


def loan9(e):
    proc=ref("primitive-return")
    show(e,ALICE,proc,selectors=(Selector("procedure","definition",("facets","0")),))
    for obj in (ref("practice-loan"),ref("practice-loan-due")):show(e,ALICE,obj)
    event=perform(e,OperationRequest("practice-return",ALICE,"return",ROOM,target=ref("practice-loan"),relation=ref("practice-loan-due"),
        evidence=evidence(e,ALICE,ref("practice-loan"))))
    receive(e,event,ALICE,"return-practice")
    perform(e,OperationRequest("acquire-return",ALICE,"acquire",ROOM,procedure=proc,practice=event))
    target=e.world.resolve(ref("loan"))
    selectors=tuple(Selector(n,"detail",("facets","0",n)) for n in ("owner","custodian","quantity","condition"))+tuple(
        Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(target.attributes))
    show(e,ALICE,target.ref,selectors=selectors)
    rel=ref("loan-due")
    selectors=(Selector("predicate","detail",("facets","0","predicate")),Selector("status","detail",("facets","0","terms","0","value")))+tuple(
        Selector(n,"detail",("facets","0","endpoints",str(i),"target","identity")) for i,n in enumerate(("borrower","owner","item")))
    show(e,ALICE,rel,selectors=selectors)
    slots=(("target",target.ref),("relation",rel))
    goal=(("ge",("field","progress","uses"),1),("eq",("field","target","custodian"),("field","target","owner")),
        ("eq",("field","relation","status"),"fulfilled"))
    return do9(e,"notice-loan","notice",slots=slots,goal=goal)[0]
