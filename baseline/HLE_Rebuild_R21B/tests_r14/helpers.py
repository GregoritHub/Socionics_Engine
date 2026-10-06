from dataclasses import replace
from hle.autonomy_demo import world,run,report
from hle.autonomy import AutonomousWorld
from hle.autonomy_records import *
from hle.autonomy_policy import decide,select
from hle.contracts import Ref,Kind,WorkStatus
from hle.memory_records import MemoryCommand,RecallQuery
from hle.world_records import Tick,Attempt,TRANSFER,INSPECT,Credit
from hle.contracts import ActionRequest


def actors_items(w):
    a,b=w.config.actors
    tool=next((r for r,_ in w.workshop.conditions if r.key.endswith(':tool')),None)
    piece=next(r for r,_ in w.workshop.conditions if r.key.endswith(':piece'))
    return a,b,tool,piece


def advance_until(w,predicate,limit=1400):
    for i in range(limit):
        if predicate(w):return i
        changed=False
        for actor in w.config.actors:
            if w.autonomy_ready(actor):w.autonomy_step(actor);changed=True
            if predicate(w):return i+1
        if not changed:break
    raise AssertionError('requested trace boundary not reached')


def next_selection(w,actor):
    s=w.autonomy_state(actor)
    return (actor not in w._active_turn and s.pending is not None and type(s.pending) is MemoryCommand
        and type(s.pending.payload) is RecallQuery and s.pending.command_id in w._commands
        and w._commands[s.pending.command_id].event.outcome==WorkStatus.COMPLETED)


def until_used(w):
    return advance_until(w,lambda x:any(tx.event.action=='r14.use' and tx.event.outcome==WorkStatus.COMPLETED for tx in x._journal))


def active_families(w,actor):return {d.specification.family for d in w.own_demands(actor) if d.status!='resolved'}
def ever_families(w,actor):return {d.specification.family for d in w._demand_records.values() if d.owner==actor}

def autonomous_only(w,actor,limit=1000):
    for _ in range(limit):
        if not w.autonomy_ready(actor):return
        w.autonomy_step(actor)
    raise AssertionError('actor did not reach a bounded wait/rest state')
