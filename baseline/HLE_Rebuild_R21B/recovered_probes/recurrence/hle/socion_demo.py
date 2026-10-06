"""R6 demand harness. It schedules actors; their policies select every response."""
from dataclasses import replace
from .contracts import Kind, Ref
from .demo import ALICE, BOB, BOX, TOOL, config, request
from .metabolism_records import ProcessingPolicy, Profile
from .socion import SocionWorld
from .socion_records import (AddGoal, AgentPolicy, AssessDyads, CloseRound,
    DeclareDyad, Goal, OpenRound)


def world(types=("lse","iee"),processing=ProcessingPolicy(),agents=None,energy=5000,time=5000,witnesses=(),links=None):
    c=config(energy,time,witnesses)
    if links is not None:c=replace(c,message_links=links)
    return SocionWorld(c,tuple(Profile(a,t) for a,t in zip(c.actors,types)),processing,
        agents or tuple(AgentPolicy(a) for a in c.actors))


def settle(w,limit=3000,order=(ALICE,BOB)):
    """Bounded fair scheduler. Resource exhaustion stops without spin/repricing."""
    for step in range(limit):
        acted=False
        for actor in order:
            if w.ready(actor):
                view=w.agent_view(actor)
                if min(view.energy,view.time)==0:continue
                w.advance(actor);acted=True
        if not acted:return step
    raise RuntimeError("declared scheduling horizon exhausted")


def demand(w,key,actor,item,partner):
    w.execute(AddGoal("goal:"+key,Goal(key,actor,item,partner)))
    settle(w)
    return w._goal_results.get(Ref(Kind.EVIDENCE,"goal-result:"+key,1))


def learned_pair(agents=None):
    """Contradict both private histories by explicit hidden world interventions.

    These are external conditions, not injected beliefs or injected lessons.
    Both agents independently choose checking and acquire their own R4 guard.
    """
    from .world_records import Attempt, Correction, TRANSFER
    w=world(agents=agents);settle(w)
    for key,actor,item,partner in (("box",ALICE,BOX,BOB),("tool",BOB,TOOL,ALICE)):
        e=w.execute(Attempt("history:"+key,"history:"+key,request(actor,TRANSFER,(item,partner))))
        w.execute(Correction("hidden:"+key,e.ref,actor,"declared hidden change for the R6 history control"))
    settle(w)
    w.execute(AddGoal("goal:learn:a",Goal("learn:a",ALICE,BOX,BOB)))
    w.execute(AddGoal("goal:learn:b",Goal("learn:b",BOB,TOOL,ALICE)))
    settle(w)
    return w


def run_socion_demo():
    w=world();settle(w)
    w.execute(DeclareDyad("declare:round","round",ALICE,BOB,BOX))
    study=Ref(Kind.ASSESSMENT,"dyad:round",1)
    w.execute(OpenRound("open:round",study,"round"))
    first=demand(w,"out",ALICE,BOX,BOB)
    second=demand(w,"back",BOB,BOX,ALICE)
    w.execute(CloseRound("close:round",Ref(Kind.DEMAND,"dyad-round:round",1)))
    w.execute(AssessDyads("report:round"))
    report=w.dyad_report(study)
    return w,{"milestone":"R6","events":len(w._journal),"goals":len(w._goal_results),
        "return":report.identity.value,"path":report.path.value,"meaning":report.meaning.value,
        "WE":{p.cell.phase.value:p.status.value for p in report.phases},
        "charged":{a.key:w._spent[a] for a in w.config.actors},
        "scope":"independent local policies in a supplied ownership/query grammar; no unrestricted language or empirical type claim",
        "next":"R7: stated recursive composition hypothesis"}
