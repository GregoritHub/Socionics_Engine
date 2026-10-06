"""Offline oracle: rebuild all inputs from journal, without runtime graph indexes."""
from hle.contracts import ClaimStatus, EvidenceStatus as E, MemoryRevision
from hle.composition_records import CompositionRevision, UnfoldResult, UseWitness
from hle.metabolism_records import Account, Application, EmbodyDraft, MetabolicTransaction
from hle.world_records import ENERGY, TRANSFER


def reference_report(journal, test, at):
    records={}; heads={}; facts={}; origins={}; units={}; account_units={}; application_units={}; uses=[]; accesses=[]
    for tx in journal:
        # Compare at the evaluator's explicitly recorded point, not after the report.
        if tx.event.when>at: break
        for change in tx.event.changes:
            p=change.before or change.after
            facts[(p.subject,p.relation,p.context)]=change.after
        for r in tx.memories+getattr(tx,'extra',()):
            records[r.ref]=r; origins[r.ref]=tx.event.when
            if type(r) in (CompositionRevision,MemoryRevision): heads[(r.owner,r.ref.kind,r.ref.key)]=r.ref
            if type(r) is UnfoldResult and r.query.root==test.request.root and r.query.context==test.request.context and tx.event.when>=test.at:
                accesses.append(r)
        if type(tx) is MetabolicTransaction:
            k=(tx.command.actor,tx.command.task_id)
            units[k]=units.get(k,0)+sum(x.amount for w in tx.works for x in w.charged if x.unit==ENERGY)
            for r in tx.extra:
                if type(r) is Account: account_units[r.ref]=units[k]
                if type(r) is Application: application_units[r.ref]=units[k]
            if tx.memories and type(tx.command.payload) is EmbodyDraft:
                app=records[tx.command.payload.application]; account=records[app.account]; access=records.get(account.recall)
                if type(access) is UnfoldResult and access in accesses:
                    uses.append(UseWitness(access.ref,account.ref,app.ref,tx.memories[0].ref,
                        access.units+account_units[account.ref]+application_units[app.ref]+units[k]))
    s=test.request
    todo=[s.root]; reachable=[]; distinct=set()
    while todo:
        r=todo.pop(0)
        if r in distinct: continue
        distinct.add(r); reachable.append(r)
        node=records[r]
        if type(node) is CompositionRevision:
            todo.extend(p.target for p in node.parts if p.context==s.context)
    stale=tuple(r for r in reachable if heads[(records[r].owner,r.kind,r.key)]!=r)
    claims=[]; capabilities=set()
    for ref in reachable:
        m=records[ref]
        if type(m) is not MemoryRevision or m.claim_status in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED): continue
        claims.extend(p for p in m.content if p.context==s.context and p.scope.start<=at and (p.scope.end is None or at<p.scope.end))
        capabilities.update(records[r].rule for r in m.capabilities)

    def aggregate(values):
        values=list(values)
        if any(v==E.FAILED for v in values):return E.FAILED
        if not values or any(v==E.UNASSESSED for v in values):return E.UNASSESSED
        return E.ESTABLISHED

    agreements=[]
    for e in s.claims:
        relevant=[p for p in claims if p.subject==e.subject and p.relation==e.relation]
        if not relevant: agreements.append(E.UNASSESSED);continue
        start=max(p.scope.start for p in relevant)
        values={(type(p.object),p.object) for p in relevant if p.scope.start==start}
        agreements.append(E.ESTABLISHED if values=={(type(e.value),e.value)} else E.FAILED)
    agreement=aggregate(agreements)
    capacity=(E.ESTABLISHED if set(s.required_rules)<=capabilities else E.FAILED) if s.required_rules else E.UNASSESSED
    freshness=E.FAILED if stale else E.ESTABLISHED
    factual=[]
    for p in dict.fromkeys(claims):
        fact=facts.get((p.subject,p.relation,p.context))
        # The tested ownership grammar uses public entities in the one world context.
        if (p.subject,p.relation,p.context) not in facts: factual.append(E.UNASSESSED)
        else:factual.append(E.ESTABLISHED if fact is not None and (type(p.object),p.object)==(type(fact.object),fact.object) else E.FAILED)
    identity=[]
    for access in accesses:
        queue=[s.root]; done=[]; edges=[]; expected_hits=[]; expected_caps=[]
        while queue:
            ref=queue.pop(0)
            if ref in done:continue
            done.append(ref); r=records[ref]
            if type(r) is CompositionRevision:
                for p in r.parts:
                    if p.context==s.context:
                        edges.append((ref,p));queue.append(p.target)
            else:
                expected_caps.extend(r.capabilities)
                indexes=tuple(i for i,p in enumerate(r.content) if p.context==s.context and p.scope.start<=access.query.at and (p.scope.end is None or access.query.at<p.scope.end))
                if indexes or r.capabilities:expected_hits.append((ref,indexes))
        identity.append(E.ESTABLISHED if (access.nodes==tuple(done)
            and tuple((e.parent,e.part) for e in access.edges)==tuple(edges)
            and tuple((h.memory,h.proposition_indexes) for h in access.hits)==tuple(expected_hits)
            and access.capabilities==tuple(dict.fromkeys(expected_caps))) else E.FAILED)
    useful=[]
    for use in uses:
        a=records[use.account];app=records[use.application];m=records[use.retained]
        actions=[records[r] for r in app.enactments]
        ok=app.outcome.value=='completed' and any(x.request.operation==TRANSFER and x.request.inputs==(a.item,a.recipient) and x.outcome.value=='completed' for x in actions)
        useful.append(E.ESTABLISHED if ok and set(s.required_rules)<={records[r].rule for r in m.capabilities} else E.FAILED)
    return {'nodes':tuple(reachable),'stale':stale,'accesses':tuple(a.ref for a in accesses),'uses':tuple(uses),
        'agreement':agreement,'capacity':capacity,'freshness':freshness,
        'cross_level':aggregate([freshness]+([agreement] if s.claims else [])+([capacity] if s.required_rules else [])),
        'identity':aggregate(identity),'factual':aggregate(factual),
        'factual_counts':tuple(factual.count(e) for e in (E.ESTABLISHED,E.FAILED,E.UNASSESSED)),
        'path':aggregate(E.ESTABLISHED if u.units<=s.max_units else E.FAILED for u in uses),
        'usefulness':aggregate(useful),'closure':E.UNASSESSED}
