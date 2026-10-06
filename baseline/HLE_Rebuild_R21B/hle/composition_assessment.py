"""Evaluator-only R7 consistency conditions, distinct from participant access."""
from .contracts import ClaimStatus, EvidenceStatus as E, Kind, MemoryRevision, Ref, WorkStatus
from .memory import in_scope
from .memory_records import RecallHit
from .world_records import TRANSFER
from .composition_records import (CompositionReport, CompositionRevision,
    CompositionTest, Edge)


def combine(statuses):
    values=tuple(statuses)
    return E.FAILED if E.FAILED in values else E.UNASSESSED if not values or E.UNASSESSED in values else E.ESTABLISHED


def snapshot(w, root, context, at):
    """Exact selected view; never follows a current head in place of a child."""
    queue=[root]; seen={root}; nodes=[]; edges=[]; hits=[]; caps=[]; cursor=0
    while cursor<len(queue):
        ref=queue[cursor]; cursor+=1; nodes.append(ref); r=w._records[ref]
        if type(r) is CompositionRevision:
            for p in r.parts:
                if context is None or p.context==context:
                    edges.append(Edge(ref,p))
                    if p.target not in seen: queue.append(p.target); seen.add(p.target)
        else:
            caps.extend(r.capabilities)
            indexes=tuple(i for i,p in enumerate(r.content) if p.context==context and in_scope(p.scope,at))
            if context is not None and (indexes or r.capabilities): hits.append(RecallHit(ref,indexes))
    return tuple(nodes),tuple(edges),tuple(hits),tuple(dict.fromkeys(caps))


def declaration(w, cmd, when):
    root=w._records.get(cmd.root)
    ref=Ref(Kind.ASSESSMENT,"composition-test:"+cmd.key,1)
    if type(root) is not CompositionRevision or ref in w._records or cmd.context not in w._known[root.owner]:
        raise ValueError("known root/context and new test identity required")
    for c in cmd.claims:
        if c.subject not in w._known[root.owner] or type(c.value) is Ref and c.value not in w._known[root.owner]:
            raise ValueError("unknown claim referent")
    return CompositionTest(ref,cmd,when)


def assess(w, test, when):
    s=test.request; at=w.now
    nodes,edges,hits,caps=snapshot(w,s.root,s.context,at)
    stale=[]
    for ref in nodes:
        r=w._records[ref]
        head=w._composition_heads.get(ref.key) if type(r) is CompositionRevision else w._memory_heads[r.owner].get(ref.key)
        if head is None or head.ref!=ref: stale.append(ref)
    claims=[]; rules=set()
    for hit in hits:
        memory=w._records[hit.memory]
        if memory.claim_status in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED): continue
        claims.extend(memory.content[i] for i in hit.proposition_indexes)
        rules.update(w._records[r].rule for r in memory.capabilities)
    constraints=[]
    for c in s.claims:
        candidates=[p for p in claims if (p.subject,p.relation)==(c.subject,c.relation)]
        if not candidates: constraints.append(E.UNASSESSED); continue
        newest=max(p.scope.start for p in candidates)
        values={(type(p.object),p.object) for p in candidates if p.scope.start==newest}
        constraints.append(E.ESTABLISHED if values=={(type(c.value),c.value)} else E.FAILED)
    agreement=combine(constraints)
    capacity=(E.ESTABLISHED if set(s.required_rules)<=rules else E.FAILED) if s.required_rules else E.UNASSESSED
    freshness=E.FAILED if stale else E.ESTABLISHED
    cross_level=combine((freshness,)+((agreement,) if s.claims else ())+((capacity,) if s.required_rules else ()))
    facts=[w.truth.check(p,at).status for p in dict.fromkeys(claims)]
    accesses=tuple(r for r in w._accesses.get((s.root,s.context),()) if w._records[w._origins[r]].when>=test.at)
    identity=[]
    for ref in accesses:
        access=w._records[ref]; expected=snapshot(w,s.root,s.context,access.query.at)
        identity.append(E.ESTABLISHED if (access.nodes,access.edges,access.hits,access.capabilities)==expected else E.FAILED)
    uses=tuple(u for u in w._uses.get((s.root,s.context),()) if u.access in accesses)
    useful=[]
    for use in uses:
        a=w._records[use.account]; app=w._records[use.application]; m=w._records[use.retained]
        actions=[w._records[r] for r in app.enactments]
        transfer=any(x.request.operation==TRANSFER and x.request.inputs==(a.item,a.recipient)
                     and x.outcome==WorkStatus.COMPLETED for x in actions)
        retained={w._records[r].rule for r in m.capabilities}
        useful.append(E.ESTABLISHED if app.outcome==WorkStatus.COMPLETED and transfer
                      and set(s.required_rules)<=retained else E.FAILED)
    old=w._composition_reports.get(test.ref)
    ref=Ref(Kind.EVIDENCE,"composition-report:"+test.ref.key,1 if old is None else old.ref.revision+1)
    return CompositionReport(ref,test.ref,at,nodes,tuple(stale),accesses,uses,agreement,capacity,freshness,
        cross_level,combine(identity),combine(facts),combine(E.ESTABLISHED if u.units<=s.max_units else E.FAILED for u in uses),
        combine(useful),(facts.count(E.ESTABLISHED),facts.count(E.FAILED),facts.count(E.UNASSESSED)))
