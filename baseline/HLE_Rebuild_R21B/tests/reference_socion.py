"""Offline independent full-journal return comparison, without runtime indexes."""
from hle.contracts import EvidenceStatus as E, WorkStatus
from hle.socion_records import Dyad, GoalResult, Reception, RoundStart, CloseRound
from hle.world_records import ENERGY, TRANSFER


def complete_round(config,journal,start_ref):
    records={}
    starts={}
    facts={o.item:o.owner for o in config.ownership}
    d=start=None;begin=None;uses=[];units=0;receptions=set();begin_owner=None
    for index,tx in enumerate(journal):
        for r in (tx.event,)+tx.works+tx.messages+tx.observations+tx.memories+getattr(tx,'extra',()):
            records[r.ref]=r
            if type(r) is Reception and r.outcome==WorkStatus.COMPLETED:
                receptions.add((r.owner,r.command.observation))
            if type(r) is RoundStart and r.ref==start_ref:
                start=r;d=records[r.study].request;begin=index
                begin_owner=facts[d.item]
        for c in tx.event.changes:
            if (c.before or c.after).relation=='owned_by':facts[(c.before or c.after).subject]=None if c.after is None else c.after.object
        if begin is not None and index>begin:
            units+=sum(r.amount for work in tx.works if work.owner in (d.left,d.right)
                       for r in work.charged if r.unit==ENERGY)
            uses.extend(r for r in getattr(tx,'extra',()) if type(r) is GoalResult and
                r.goal.item==d.item and r.owner in (d.left,d.right) and r.goal.partner in (d.left,d.right))
        if type(tx.command) is CloseRound and tx.command.start==start_ref:break
    if start is None:raise ValueError('missing round')
    identity=meaning=E.UNASSESSED
    if len(uses)>=2:
        complete=(len(uses)==2 and [r.owner for r in uses]==[d.left,d.right] and facts[d.item]==begin_owner)
        meanings=[]
        for use in uses:
            app=records[use.application];account=records[use.account]
            complete=complete and any(records[e].request.operation==TRANSFER and
                records[e].request.inputs==(d.item,use.goal.partner) and records[e].outcome==WorkStatus.COMPLETED
                for e in app.enactments)
            hit=False
            if use.received is not None:
                message=records[use.received]
                hit=((use.owner,use.received) in receptions and account.claim is not None
                    and account.claim in message.content and any(use.received in records[m].observations for m in account.evidence)
                    and app.account==account.ref and bool(app.enactments) and records[use.retained].owner==use.owner)
            meanings.append(hit)
        identity=E.ESTABLISHED if complete else E.FAILED
        meaning=E.ESTABLISHED if all(meanings) else E.FAILED
    return identity,(E.ESTABLISHED if units<=d.max_units else E.FAILED),meaning,units
