"""R7 supplied demands: acquire a lesson, nest it, and use it on another item."""
from .composition import ComposedWorld
from .composition_records import (AssessCompositions, CompositionCommand,
    DeclareCompositionTest, Expectation, FoldDraft, Part, UnfoldDraft)
from .contracts import Kind, Ref, WorkStatus
from .demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from .metabolism_demo import finish, remember_initial, retrieve
from .metabolism_records import (ApplyDraft, EmbodyDraft, ProcessingPolicy, Profile, TheorizeDraft)
from .socion_records import AgentPolicy
from .world_records import Attempt, TRANSFER


def world(energy=5000,time=5000):
    return ComposedWorld(config(energy,time),(Profile(ALICE,"lse"),Profile(BOB,"iee")),
        ProcessingPolicy(),(AgentPolicy(ALICE),AgentPolicy(BOB)))


def complete(w,payload,key,actor=BOB,limit=64):
    i=0
    while True:
        w.execute(CompositionCommand(f"{key}:{i}",key,actor,payload,limit))
        job=w.composition_job(actor,key)
        if job.outcome in (WorkStatus.COMPLETED,WorkStatus.FAILED): return job
        wallet=w.truth.wallet(actor)
        if not min(wallet.energy,wallet.time): return job
        i+=1


def learned_world():
    w=world(); original=remember_initial(w)
    w.execute(Attempt("history:transfer","history:transfer",request(ALICE,TRANSFER,(BOX,BOB))))
    recalled=retrieve(w,"history:recall")
    account=finish(w,TheorizeDraft(recalled,BOX,ALICE),"history:theorize")
    app=finish(w,ApplyDraft(account.result),"history:apply")
    finish(w,EmbodyDraft(app.result,"box",original.ref),"history:embody")
    tool=remember_initial(w,"tool",TOOL)
    return w,w.memory_head(BOB,"box"),tool


def compose(w,lesson,tool,include_lesson=True,key=""):
    parts=(Part("held-out ownership",tool.ref,ROOM),)
    if include_lesson:
        learned=complete(w,FoldDraft(key+"learned-check",(Part("retained correction",lesson.ref,ROOM),)),key+"fold:lesson")
        parts=(Part("checking organization",learned.result,ROOM),)+parts
    root=complete(w,FoldDraft(key+"transfer-organization",parts),key+"fold:parent")
    return root.result


def use(w,root,key="held-out",item=TOOL):
    access=complete(w,UnfoldDraft(root,ROOM,w.now),key+":unfold")
    account=finish(w,TheorizeDraft(access.result,item,ALICE),key+":theorize")
    app=finish(w,ApplyDraft(account.result),key+":apply")
    retained=finish(w,EmbodyDraft(app.result,key+":consequence"),key+":embody")
    return access,account,app,retained


def run_composition_demo():
    w,lesson,tool=learned_world(); root=compose(w,lesson,tool)
    w.execute(DeclareCompositionTest("declare:composition","held-out",root,ROOM,
        (Expectation(TOOL,"owned_by",BOB),),("inspect_before_transfer",),1000))
    test=Ref(Kind.ASSESSMENT,"composition-test:held-out",1)
    full=complete(w,UnfoldDraft(root,None,w.now),"full-unfold")
    access,account,app,retained=use(w,root)
    w.execute(AssessCompositions("report:composition"))
    report=w.composition_report(test); application=w._records[app.result]
    actions=[w._records[r].request.operation.key for r in application.enactments]
    return w,{"milestone":"R7","events":len(w._journal),"root":root.key,
        "full_nodes":len(w._records[full.result].nodes),"contextual_nodes":len(w._records[access.result].nodes),
        "actions":actions,"learned_capability":lesson.capabilities[0].key,
        "access_units":access.completed,"use_units":report.uses[0].units,
        **{k:getattr(report,k).value for k in ("identity","agreement","capacity","freshness","cross_level","factual","path","usefulness","closure")},
        "scope":"versioned contextual DAG proposal; supplied assembly/demand; inherited learned checking grammar",
        "next":"R8: extend participant language"}
