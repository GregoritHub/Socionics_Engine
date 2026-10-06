"""Pure local policy. This module has no world, Truth, or assessor access.

Goals, response options, and the finite ownership language are supplied. Actual
answers, inspections and checking lessons depend on each participant's history.
"""
from dataclasses import replace
from .cards import CARDS, card
from .contracts import (ActionRequest, ClaimStatus, Kind, Ref, Proposition,
    TimeScope, Moment, WorkStatus)
from .memory_records import BindDraft, MemoryCommand, RecallQuery, WriteDraft
from .metabolism_records import (ApplyDraft, EmbodyDraft, MetabolicCommand,
    TheorizeDraft, UnderstandDraft)
from .socion_records import GoalResult, ReceiveCommand
from .world_records import Attempt, INSPECT, MessageDraft, SEND

CUE = card("arcana:1").ref
LESSON = card("arcana:2").ref


def object_cue(item):
    # Stable experimental cue association, not card meaning or a capacity bound.
    # Collisions are permitted and resolved by the account's exact item binding.
    address=item.key+":"+str(item.revision)
    return CARDS[22+sum((i+1)*ord(c) for i,c in enumerate(address))%(len(CARDS)-22)].ref


def item_key(item):
    return f"socion:item:{len(item.key)}:{item.key}:{item.revision}"


def binding_key(item): return "socion:bind:" + item_key(item)


def decide(v, key):
    """Return a new immutable state and optional completed-goal witness."""
    s, p = v.state, v.policy
    s = replace(s, ref=replace(s.ref, revision=s.ref.revision + 1))
    completed = None
    def issue(phase, action, **kw):
        return replace(s, phase=phase, pending=action, **kw), completed
    def mem(phase, payload, basis=(), **kw):
        return issue(phase, MemoryCommand(key, key, s.owner, payload, basis, p.work_limit), **kw)
    def met(phase, payload, **kw):
        return issue(phase, MetabolicCommand(key, key, s.owner, payload, p.work_limit), **kw)
    def inspect(phase="inspect"):
        return issue(phase, Attempt(key, key, ActionRequest(s.owner, INSPECT, (s.item,), ())))
    def recall():
        # No subject restriction: a lesson about another object can supply a guard.
        cue=object_cue(s.item)
        cues=(cue, LESSON) if p.use_lesson and v.lesson is not None else (cue,)
        return mem("recall", RecallQuery(cues, v.context, v.now, relation="owned_by", visit_limit=4096))
    def write(claim, observation):
        # Stale testimony is retained separately; it cannot replace a later direct memory.
        newer = v.memory is not None and any(x.scope.start > claim.scope.start for x in v.memory.content)
        name = item_key(s.item) + (":testimony:" + key if newer else "")
        return mem("write_stale" if newer else "write", WriteDraft(name, (claim,), (),
            ClaimStatus.TENTATIVE if s.notice and s.notice.sender else ClaimStatus.ENDORSED,
            None if newer or v.memory is None else v.memory.ref,
            "own delivered observation; testimony remains an unverified account"),
            (observation,)+(() if newer or v.memory is None else (v.memory.ref,)))
    def resting():
        return replace(s, phase="await" if s.goal else "idle", pending=None,
            mode="", item=None, partner=None, notice=None, account=None, application=None), completed
    def after_binding():
        if s.mode in ("goal", "reply"): return recall()
        return resting()

    if s.pending is not None:
        if v.pending_status is None: raise ValueError("planned operation must execute before another turn")
        if v.pending_status not in (WorkStatus.COMPLETED, WorkStatus.FAILED):
            return replace(s, pending=replace(s.pending, command_id=key)), None
        if v.pending_status == WorkStatus.FAILED and s.phase not in ("apply", "ask", "send"):
            # Expected-version conflicts are not silently repaired into success.
            return replace(s, phase="blocked", pending=None), None
        s=replace(s,pending=None)
        if s.phase == "ask":
            return replace(s, phase="await", query=v.result, waiting=0), None
        if s.phase == "receive": return write(s.notice.claim, s.notice.observation)
        if s.phase == "receive_query":
            needs_check=p.response == "fresh" or (p.use_lesson and v.lesson is not None and bool(v.lesson.capabilities))
            return inspect() if needs_check else recall()
        if s.phase == "inspect":
            claims=[(o,p0) for o in v.observations for p0 in o.content
                    if p0.subject == s.item and p0.relation == "owned_by"]
            if len(claims)!=1: raise ValueError("direct inspection receipt required")
            o,claim=claims[0]
            return write(claim,o.ref)
        if s.phase == "write":
            return mem("bind", BindDraft(binding_key(s.item), object_cue(s.item), v.context, v.result,
                TimeScope(Moment(0,0),None),v.binding), (v.result,)+(() if v.binding is None else (v.binding,)))
        if s.phase == "write_stale": return after_binding()
        if s.phase == "bind": return after_binding()
        if s.phase == "recall": return met("theorize", TheorizeDraft(v.result,s.item,s.partner))
        if s.phase == "theorize":
            s=replace(s,account=v.result)
            if s.mode == "reply":
                return met("understand",UnderstandDraft(v.result,"socion:reply:"+key))
            return met("apply",ApplyDraft(v.result))
        if s.phase == "understand":
            a=v.account
            content=() if a.claim is None else (a.claim,)
            content+=(Proposition(s.item,"reply_to",s.notice.source,v.context,TimeScope(v.now,None)),)
            return issue("send",Attempt(key,key,ActionRequest(s.owner,SEND,(s.partner,),(v.result,)),
                message=MessageDraft(content)))
        if s.phase == "send": return resting()
        if s.phase == "apply":
            s=replace(s,application=v.result)
            return met("embody",EmbodyDraft(v.result,item_key(s.item),None if v.memory is None else v.memory.ref))
        if s.phase == "embody":
            return mem("bind_result",BindDraft(binding_key(s.item),object_cue(s.item),v.context,v.result,
                TimeScope(Moment(0,0),None),v.binding),(v.result,)+(() if v.binding is None else (v.binding,)))
        if s.phase == "bind_result":
            if v.memory.capabilities:
                s=replace(s,lesson=v.memory.ref)
                return mem("bind_lesson",BindDraft("socion:lesson",LESSON,v.context,v.memory.ref,
                    TimeScope(Moment(0,0),None),v.lesson_binding),
                    (v.memory.ref,)+(() if v.lesson_binding is None else (v.lesson_binding,)))
            s=replace(s,phase="finish")
        if s.phase in ("bind_lesson","finish"):
            completed=GoalResult(Ref(Kind.EVIDENCE,"goal-result:"+s.goal.key,1),s.owner,
                s.goal,s.received,s.account,s.application,v.memory.ref)
            s=replace(s,goal=None,query=None,received=None,waiting=0)
            return resting()

    if s.phase == "blocked": return s,None
    # Consume one permitted notice, never another actor's inbox or private basis.
    n=v.notice
    if n is not None:
        s=replace(s,cursor=s.cursor+1)
        if n.kind == "query":
            if p.response == "silent": return s,None
            s=replace(s,item=n.claim.subject,partner=n.sender,notice=n,mode="reply")
            return issue("receive_query",ReceiveCommand(key,key,s.owner,n.observation,p.work_limit))
        matches=(n.kind == "report" and s.goal is not None and n.sender == s.goal.partner
            and n.claim.subject == s.goal.item and n.reply_to == s.query)
        s=replace(s,item=n.claim.subject,partner=n.sender,notice=n,
                  mode="goal" if matches else "absorb",received=n.observation if matches else s.received)
        if matches: s=replace(s,partner=s.goal.partner)
        if n.sender is not None:
            return issue("receive",ReceiveCommand(key,key,s.owner,n.observation,p.work_limit))
        return write(n.claim,n.observation)
    if s.goal is not None:
        s=replace(s,waiting=s.waiting+1)
        if s.waiting < p.patience: return s,None
        s=replace(s,item=s.goal.item,partner=s.goal.partner,mode="goal",notice=None,received=None)
        return recall()
    if s.goals:
        g=s.goals[0]
        s=replace(s,goal=g,goals=s.goals[1:],item=g.item,partner=g.partner,mode="goal",notice=None,
                  received=None,query=None)
        if not p.ask: return recall()
        content=(Proposition(g.item,"query_owner",g.actor,v.context,TimeScope(v.now,None)),)
        return issue("ask",Attempt(key,key,ActionRequest(s.owner,SEND,(g.partner,),()),message=MessageDraft(content)))
    return s,None
