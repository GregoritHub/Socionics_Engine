"""Independent complete comparison. No production assessor, snapshot or indexes.

Intentionally scans raw journal records; this is an offline oracle, not a runtime
algorithm. It independently computes pointwise claims, path and candidate counts.
"""
from hle.contracts import EvidenceStatus as E, WorldEvent, WorkStatus
from hle.assessment_records import TrialStart, TrialResult, CarrierUse
from hle.metabolism_records import Application, Capability, MetabolicTransaction, operation
from hle.world_records import INSPECT


def complete_report(config, journal, study, at, profiles=()):
    entries = [tx for tx in journal if tx.event.when <= at]
    records = {e.ref:e for e in config.entities}
    records[config.context] = config.context
    for tx in entries:
        for value in (tx.event,)+tx.works+tx.observations+tx.messages+tx.memories+getattr(tx,"extra",()):
            records[value.ref] = value
    def memory_at(moment):
        values=[m for tx in entries if tx.event.when<=moment for m in tx.memories
            if m.owner==study.actor and m.ref.key==f"{len(study.actor.key)}:{study.actor.key}:{study.actor.revision}:{study.memory_key}"]
        return values[-1] if values else None
    def claims_at(moment):
        m=memory_at(moment)
        return [] if m is None else [p for p in m.content if p.subject==study.item and p.relation=="owned_by"]
    def check(p,moment):
        if (p.context!=config.context or p.subject not in records or p.scope.start>moment
            or p.scope.end is not None and p.scope.end<=moment
            or hasattr(p.object,"kind") and p.object not in records): return E.UNASSESSED
        facts=[c.after for tx in entries if tx.event.when<=moment for c in tx.event.changes
            if (c.before or c.after).subject==p.subject and (c.before or c.after).relation==p.relation
            and (c.before or c.after).context==p.context]
        if not facts:return E.UNASSESSED
        return E.ESTABLISHED if facts[-1] is not None and type(facts[-1].object) is type(p.object) and facts[-1].object==p.object else E.FAILED
    def links(moment):return [(p.subject,p.relation,p.object,p.context) for p in claims_at(moment)]
    starts={r.ref:r for tx in entries for r in getattr(tx,"extra",()) if type(r) is TrialStart}
    ends=[r for tx in entries for r in getattr(tx,"extra",()) if type(r) is TrialResult and r.study==study.ref]
    blocked=compensated=corrected=0
    candidate=False
    failed_return=False
    capacity=set()
    last_path=last_identity=E.UNASSESSED
    for result in ends:
        start=starts[result.start]
        # Use the actual time interval, not the runtime's sparse event selection.
        path=[tx for tx in entries if start.snapshot.at<tx.event.when<=result.end.at]
        paid=sum(a.amount for tx in path for w in tx.works if w.owner==study.actor
            for a in w.charged if a.unit.key=="r2.energy_quantum")
        moves=[tx for tx in path if type(tx) is MetabolicTransaction and tx.command.actor==study.actor]
        done=tuple(operation(tx.command.payload) for tx in moves if tx.job.outcome==WorkStatus.COMPLETED)
        offer=start.request.offer
        initiated=offer is not None and any(tx.command.task_id==offer.task_id and tx.command.payload==offer.payload
            and sum(w.completed_units for w in tx.works)>0 for tx in moves)
        # Independently derive affordable from wallet at BeginTrial via works.
        wallet=next(w for w in config.wallets if w.actor==study.actor)
        money=(wallet.energy,wallet.time)
        for tx in entries:
            if tx.event.when>start.snapshot.at:break
            for work in tx.works:
                if work.owner==study.actor:money=tuple(a.amount for a in work.after)
        adequate=start.request.demanded and start.opportunity.required is not None and min(money)>=start.opportunity.required
        is_blocked=False
        interpretable=False
        contradicts=False
        for ref in start.request.corrective:
            obs=records[ref]
            if type(records.get(obs.source)) is not WorldEvent:continue
            for p in obs.content:
                if p.subject==study.item and p.relation=="owned_by" and check(p,start.snapshot.at)==E.ESTABLISHED:
                    interpretable=True
                    contradicts |= any(c.object!=p.object and c.context==p.context for c in claims_at(start.snapshot.at))
        is_blocked=adequate and interpretable and not initiated
        failed=any(check(p,result.end.at)==E.FAILED for p in claims_at(result.end.at))
        rewritten=any(m.owner==study.actor and m.ref.key.endswith(":"+study.memory_key)
            for tx in path for m in tx.memories)
        reconstruction=adequate and contradicts and rewritten and paid>0 and failed and links(start.snapshot.at)==links(result.end.at)
        apps=[r for tx in moves for r in tx.extra if type(r) is Application]
        external=any(r.carrier is not None and r.message is not None for tx in path
            for r in getattr(tx,"extra",()) if type(r) is CarrierUse and r.owner==study.actor)
        last_path=E.FAILED if (paid>study.max_units or external or reconstruction
            or study.forbid_discrepancy and any(a.discrepancy for a in apps)) else E.ESTABLISHED
        # Feature extraction is independent of production identity().
        def feature(moment):
            m=memory_at(moment)
            ps=claims_at(moment)
            perspective=next((p.perspective.value for p in profiles if p.owner==study.actor), "I")
            for tx in entries:
                if tx.event.when>moment:break
                if type(tx) is MetabolicTransaction and tx.command.actor==study.actor: perspective=tx.state.perspective.value
            mapping={"claim_links":links(moment),"claim_scope":[p.scope for p in ps],
                "capacity_rules":sorted({records[c].rule for c in (() if m is None else m.capabilities)}),
                "perspective":perspective}
            return [mapping[f] for f in study.spec.identity_features]
        valid=all(claims_at(t) for t in (start.snapshot.at,result.end.at)) if set(study.spec.identity_features)&{"claim_links","claim_scope"} else True
        if "capacity_rules" in study.spec.identity_features:
            valid &= all(memory_at(t) is not None and memory_at(t).capabilities for t in (start.snapshot.at,result.end.at))
        last_identity=(E.ESTABLISHED if feature(start.snapshot.at)==feature(result.end.at) else E.FAILED) if done==study.operations and valid else E.UNASSESSED
        failed_return |= last_identity==E.FAILED
        initial_memory=memory_at(start.snapshot.at)
        for a in apps:
            account=records[a.account]
            if (initial_memory is not None and account.guard in initial_memory.capabilities
                and a.outcome==WorkStatus.COMPLETED and records[a.enactments[0]].request.operation==INSPECT):capacity.add(account.item)
        blocked=blocked+1 if is_blocked else 0
        compensated=compensated+1 if reconstruction else 0
        candidate |= max(blocked,compensated)>=study.recurrence
        all_correct=bool(claims_at(result.end.at)) and all(check(p,result.end.at)==E.ESTABLISHED for p in claims_at(result.end.at))
        corrected=corrected+1 if adequate and done==study.operations and all_correct and last_path==E.ESTABLISHED and not is_blocked else 0
    checks=[check(p,at) for p in claims_at(at)]
    factual=E.FAILED if E.FAILED in checks else E.ESTABLISHED if checks and E.UNASSESSED not in checks else E.UNASSESSED
    capacity_status=E.ESTABLISHED if study.item in capacity and len(capacity)>1 else E.UNASSESSED
    if compensated>=study.recurrence:shell="compensation_candidate"
    elif blocked>=study.recurrence:shell="foreclosure_candidate"
    elif candidate:
        shell="cleared_in_tested_demands" if corrected>=study.recurrence and study.item in capacity and len(capacity)>1 else "candidate_unresolved"
    elif not ends:shell="unassessed"
    elif not starts[ends[-1].start].request.demanded:shell="rest_or_stable_error"
    elif starts[ends[-1].start].opportunity.required is None:shell="opportunity_unassessed"
    elif not starts[ends[-1].start].opportunity.affordable:shell="resource_limited"
    elif not claims_at(at):shell="ignorance"
    else:shell="no_persistent_candidate"
    direct=[o for tx in entries for o in tx.observations if o.observer==study.actor
        and type(records.get(o.source)) is WorldEvent
        and any(p.subject==study.item and p.relation=="owned_by" for p in o.content)]
    delivered=bool(direct) and any(check(p,at)==E.ESTABLISHED for p in direct[-1].content if p.subject==study.item and p.relation=="owned_by")
    return {"statuses":(factual,last_identity,last_path,capacity_status),"shell":shell,
        "closure":E.FAILED if failed_return else E.UNASSESSED,
        "adjudicable":sum(s!=E.UNASSESSED for s in checks),"contradicted":checks.count(E.FAILED),
        "unresolved":checks.count(E.UNASSESSED),"delivered":int(delivered),"retained":int(bool(checks)),
        "aggregate":(len(ends),blocked,compensated,candidate,corrected,tuple(sorted(capacity,key=lambda r:r.key)))}
