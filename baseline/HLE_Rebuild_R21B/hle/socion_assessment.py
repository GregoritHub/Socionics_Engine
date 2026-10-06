"""Evaluator-only dyadic predicate and exact finite return tests (S07).

WE is (two distinct actors, shared ownership context, requested transfer and
return, interpreted testimony on each leg). Closure of arbitrary composition
remains unassessed. A later success cannot discard an earlier failed trial.
"""
from .contracts import EvidenceStatus as E, Kind, Ref, WorkStatus, IdeaCell, IdeaPhase
from .assessment_records import PhaseEvidence
from .crux import Perspective
from .socion_records import (AssessDyads, CloseRound, DeclareDyad, Dyad, DyadReport,
    OpenRound, RoundStart, RoundResult)
from .world_records import TRANSFER


def aggregate_status(statuses):
    return E.FAILED if E.FAILED in statuses else E.ESTABLISHED if statuses and all(s==E.ESTABLISHED for s in statuses) else E.UNASSESSED


def understood(w,use):
    """Delivery -> paid reception -> memory -> recalled account -> application."""
    if use.received is None:return False
    obs=w._records[use.received]
    a=w._records[use.account];app=w._records[use.application]
    reception=(use.owner,use.received) in w._completed_reception
    # Offline evaluator follows this goal's exact addresses; policy never calls it.
    retained=any(use.received in w._records[r].observations for r in a.evidence)
    return (reception and retained and a.claim is not None and a.claim in obs.content
            and app.account==a.ref and bool(app.enactments)
            and w._records[use.retained].owner==use.owner)


def assess_command(w,cmd):
    if type(cmd) is DeclareDyad:
        ref=Ref(Kind.ASSESSMENT,"dyad:"+cmd.key,1)
        if (not cmd.key.strip() or ref in w._records or cmd.left==cmd.right or
            cmd.left not in w._actors or cmd.right not in w._actors or cmd.item not in w._items or cmd.max_units<1):
            raise ValueError("invalid dyadic declaration")
        return (Dyad(ref,cmd,w.now),)
    if type(cmd) is OpenRound:
        if cmd.study not in w._dyads or cmd.study in w._dyad_open or not cmd.key.strip():
            raise ValueError("unknown study or open round")
        ref=Ref(Kind.DEMAND,"dyad-round:"+cmd.key,1)
        if ref in w._records:raise ValueError("duplicate round")
        d=w._dyads[cmd.study].request
        if any(w.agent_state(a).goal is not None or w.agent_state(a).goals for a in (d.left,d.right)):
            raise ValueError("declare return before supplying its goals")
        owner=w.truth.current_fact(d.item,"owned_by",w.config.context).object
        if owner!=d.left:raise ValueError("protocol domain starts with left owner")
        return (RoundStart(ref,cmd.study,w.now,owner,len(w._goals_by_item.get(d.item,())),
            w._spent[d.left],w._spent[d.right]),)
    if type(cmd) is CloseRound:
        start=w._round_starts.get(cmd.start)
        ref=Ref(Kind.EVIDENCE,"closed:"+cmd.start.key,1)
        if start is None or ref in w._records:raise ValueError("unknown or closed round")
        d=w._dyads[start.study].request
        uses=tuple(u for u in w._goals_by_item.get(d.item,())[start.cursor:]
            if u.goal.actor in (d.left,d.right) and u.goal.partner in (d.left,d.right))
        units=w._spent[d.left]-start.left_spent+w._spent[d.right]-start.right_spent
        identity=meaning=E.UNASSESSED
        path=E.ESTABLISHED if units<=d.max_units else E.FAILED
        if len(uses)>=2:
            ordered=len(uses)==2 and tuple(u.owner for u in uses)==(d.left,d.right)
            enacted=all(any(w._records[e].request.operation==TRANSFER and
                w._records[e].request.inputs==(d.item,u.goal.partner) and w._records[e].outcome==WorkStatus.COMPLETED
                for e in w._records[u.application].enactments) for u in uses)
            returned=w.truth.current_fact(d.item,"owned_by",w.config.context).object==start.owner
            identity=E.ESTABLISHED if ordered and enacted and returned else E.FAILED
            meaning=E.ESTABLISHED if all(understood(w,u) for u in uses) else E.FAILED
        return (RoundResult(ref,start.ref,start.study,tuple(u.ref for u in uses),identity,path,meaning,units,
            "declared ordered two-party transfer/return; message meaning requires retained consequential use"),)
    if type(cmd) is not AssessDyads or cmd.limit<1:raise ValueError("positive assessment batch required")
    output=[]
    for ref in w.pending_dyads()[:cmd.limit]:
        rounds=tuple(w._round_results[r] for r in w._dyad_rounds[ref])
        statuses=tuple(aggregate_status(tuple(getattr(r,f) for r in rounds)) for f in ("identity","path","meaning"))
        engaged=aggregate_status((statuses[0],statuses[2]))
        phases=tuple(PhaseEvidence(IdeaCell(phase,Perspective.WE),status,
            (ref,)+tuple(r.ref for r in rounds),reason) for phase,status,reason in zip(IdeaPhase,
            (E.ESTABLISHED,E.ESTABLISHED,engaged,E.FAILED if engaged==E.FAILED else E.UNASSESSED),
            ("declared distinct participant standpoints","explicit dyadic expectation and shared context predicate",
             "ordered coordination and exact return with checked interpretation","finite-composition preservation unproved; failures retained")))
        old=w.dyad_report(ref)
        output.append(DyadReport(Ref(Kind.EVIDENCE,"report:"+ref.key,1 if old is None else old.ref.revision+1),
            ref,tuple(r.ref for r in rounds),phases,*statuses,E.FAILED if statuses[0]==E.FAILED else E.UNASSESSED))
    return tuple(output)
