"""Offline R20 raw-transaction audit, independent of the closure runtime/policy.

Rebuilds consent, individual performance, obligation identity, resource balances,
root heads and subsequent invalidation. Runtime predicate fields are comparison
targets only. Prior R19 clearance is independently reconstructed by its raw fold.
"""
from types import SimpleNamespace
from .closure_records import *
from .composition_records import CompositionRevision, UnfoldResult
from .organization_records import OrganizationResult, OrganizationTransaction
from .organization import terms_id
from .contracts import MemoryRevision, WorkStatus
from .conversion_records import ConversionCapacity, ConversionUse, ConversionStudy, ScopeCandidate
from .individuation_records import AspectCapacity, CircuitOrder, CircuitSignal
from .world_records import Attempt, TRANSFER, ENERGY, TIME
from .clearance_reference import evaluate as clearance_reference
from .shell_assessment import reftext

def evaluate(w):
    records={};origins={};heads={};states={};invalid=set();restricted=set()
    capacities={};roots={};duties={};active={};spent_production={};assessed=[];errors=[]
    balances={x.actor:(x.energy,x.time) for x in w.config.wallets}
    def add(r,event):
        if hasattr(r,'ref'):records[r.ref]=r;origins[r.ref]=event
    def live(r):return r in records and r not in invalid and origins.get(r) not in invalid
    def root_ok(access):return all(heads.get(r.key)==r and live(r) for r in records[access].nodes)
    def raw_clearance(stop):
        view=SimpleNamespace(config=w.config,profiles=w.profiles,policy=w.policy,release=w.release,account_policy=w.account_policy,conversion_policy=w.conversion_policy,circuit_policy=w.circuit_policy,
            circuit_partners=w.circuit_partners,reviewers=w.reviewers,_journal=w._journal[:stop])
        return clearance_reference(view)
    for n,tx in enumerate(w._journal):
        e=tx.event;c=tx.command;add(e,e.ref)
        for work in tx.works:
            add(work,e.ref)
            before={x.unit:x.amount for x in work.before};after={x.unit:x.amount for x in work.after}
            charges={x.unit:x.amount for x in work.charged};credits={x.unit:x.amount for x in work.credited}
            if (before[ENERGY],before[TIME])!=balances[work.owner]:errors.append('wallet predecessor '+reftext(e.ref))
            if any(after[u]!=before[u]+credits.get(u,0)-charges.get(u,0) or after[u]<0 for u in (ENERGY,TIME)):
                errors.append('work conservation '+reftext(e.ref))
            balances[work.owner]=after[ENERGY],after[TIME]
        if type(c).__name__=='WithdrawEvidence':invalid.add(c.source)
        if e.corrects is not None:invalid.add(e.corrects)
        if getattr(c,'operator',None)=='restrict':restricted.add(c.actor)
        if getattr(c,'operator',None)=='restore_access':restricted.discard(c.actor)
        all_records=list(tx.observations)+list(tx.messages)+list(tx.memories)+list(getattr(tx,'extra',()))+list(getattr(tx,'capacities',()))+list(getattr(tx,'parts',()))
        for attr in ('capacity','candidate','study','use','order','signal','communication','material','concept','state'):
            r=getattr(tx,attr,None)
            if r is not None:all_records.append(r)
        for r in all_records:
            add(r,e.ref)
            if type(r) in (MemoryRevision,CompositionRevision):heads[r.ref.key]=r.ref
            if type(r) is AspectCapacity:capacities[r.owner,r.aspect]=r
            if type(r) is ConversionCapacity:roots[r.owner]=r
            if type(r) is OrganizationResult and r.terms is not None:
                if (r.kind=='agreement' and r.status=='active' or r.kind=='exit' and r.status=='withdrawn'
                    or r.kind=='dispute' and r.status=='suspended' or r.kind=='notice' and r.status in ('active','suspended','dissolved')):
                    states[r.owner,r.terms.identity]=r
            if type(r) is SharedDemand:
                duties[r.ref]={};b=records[r.binding]
                spent_production[b.production]=spent_production.get(b.production,0)+len(r.obligations)
                if spent_production[b.production]>records[b.production].produced:errors.append('double-spent production')
            if type(r) is SharedActivation:
                plan=records[r.plan];votes=[]
                for source in r.votes:
                    v=records[source]
                    if type(v) is Observation:
                        from .codec import loads
                        v=loads(v.content[0].object).record
                    votes.append(v)
                if len(votes)!=len(plan.members) or {v.owner for v in votes}!=set(plan.members) or any(not v.approved or v.plan!=plan.ref or v.own_units>v.limit for v in votes):
                    errors.append('invalid member consent')
                active[plan.demand]=(r,plan)
        if type(c) is Attempt and c.action.operation==TRANSFER and e.outcome==WorkStatus.COMPLETED and c.task_id.startswith('organization-act:'):
            # Locate the named originating run from the command namespace;
            # independently inspect its speech and exact enacted recipient.
            run=next((r for r in records.values() if type(r) is OrganizationResult and r.kind=='run'
                and c.task_id.startswith('organization-act:'+r.ref.key+':')),None)
            if run is not None and run.status=='accepted':
                for demand,(activation,plan) in tuple(active.items()):
                    left=[pair for pair in plan.assignments if pair[0] not in duties[demand]]
                    expected=plan.members[(plan.members.index(c.action.actor)+1)%len(plan.members)] if c.action.actor in plan.members else None
                    if (left and left[0][1]==c.action.actor and run.terms is not None and terms_id(run.terms)==plan.terms_digest
                        and c.action.inputs==(records[demand].item,expected)):
                        duties[demand][left[0][0]]=(c.action.actor,e.ref)
                        if len(duties[demand])==len(records[demand].obligations):active.pop(demand)
                        break
        for claim in (r for r in getattr(tx,'extra',()) if type(r) is ClosureResult):
            plan=records[claim.plan];d=records[plan.demand];b=records[d.binding];s=records[plan.search]
            done=duties[d.ref];current=tuple(states.get((m,plan.identity)) for m in plan.members)
            activation=records[claim.activation];consent_live=True
            for source in activation.votes:
                v=records[source]
                if type(v) is Observation:
                    from .codec import loads
                    v=loads(v.content[0].object).record
                consent_live &= live(source) and live(v.ref) and v.approved and v.plan==plan.ref
            root=roots.get(b.owner)
            sig=(() if root is None or not root.current else (root.ref,))+tuple(x.ref for (a,k),x in sorted(capacities.items(),key=lambda v:v[0][1]) if a==b.owner and x.current)
            production=records[b.production];use=records[b.conditional_use];returned=records[b.returned]
            native=(b.owner not in restricted and sig==b.capacities and len(sig)==9 and all(live(x) for x in b.capacities+(b.material,b.production,b.conditional_use,b.returned))
                and production.success and production.performer==b.owner and use.capacity==sig[0]
                and returned.outcome==WorkStatus.COMPLETED and returned.actors==(b.owner,))
            prior=raw_clearance(n)
            native=native and prior['status']=='cleared_in_scope' and prior['integrity_passed']
            # Independent finite-law decision from semantic effects, not the
            # search's reported verdict or claimed minima.
            lower_success=(s.required=='single' or s.required=='shared' and 'consent_cycle' in s.current
                or s.required=='carry' and 'carry_obligations' in s.current)
            exhaustive=tuple(x[0] for x in s.rows)==LOWER
            parent=next((row for row in assessed if row['plan']==d.parent and row['status']=='established'),None)
            pred={'native_current':bool(native),'obligations_preserved':set(done)==set(d.obligations),
                'own_responsibilities':all(done.get(k,(None,))[0]==a for k,a in plan.assignments),
                'current_exact_consent':consent_live and all(x is not None and x.status=='active' and terms_id(x.terms)==plan.terms_digest for x in current),
                'every_member_performs':{a for a,e in done.values()}==set(plan.members),
                'lower_structure_usable':root_ok(plan.access),
                'successive':d.parent is None or parent is not None and records[d.parent].root==plan.parent_root and all(live(x) for x in parent['claim'].dependencies),
                'necessary':exhaustive and not lower_success}
            status='established' if all(pred.values()) else 'horizontal' if all(v for k,v in pred.items() if k!='necessary') else 'unresolved'
            depth=(1 if parent is None else parent['depth']+1) if status=='established' else 0
            expected_duties=tuple((k,done[k][0],done[k][1]) for k in d.obligations if k in done)
            if (dict(claim.predicates),claim.status,claim.depth,claim.duties)!=(pred,status,depth,expected_duties):
                errors.append('independent closure discrepancy '+reftext(claim.ref))
            assessed.append({'ref':claim.ref,'plan':plan.ref,'status':status,'depth':depth,'predicates':pred,'claim':claim})
    final_clearance=raw_clearance(len(w._journal))
    rows=[]
    for row in assessed:
        claim=row['claim'];plan=records[claim.plan];b=records[records[plan.demand].binding]
        stale=not root_ok(plan.access) or any(not live(x) for x in claim.dependencies)
        stale|=any(states.get((records[r].owner,records[r].terms.identity))!=records[r] for r in claim.current_states)
        stale|=b.owner in restricted or final_clearance['status']!='cleared_in_scope'
        rows.append({'claim':reftext(claim.ref),'historical_status':row['status'],'depth':row['depth'],
            'current_status':'invalidated' if stale else row['status'],'predicates':row['predicates'],'duties':len(claim.duties),
            'unavailable_dependencies':[reftext(x) for x in claim.dependencies if not live(x)]})
    return {'schema':'r20-independent-v1','passed':not errors,'errors':errors,'claims':rows,
        'r19_independent_passed':final_clearance['integrity_passed'],'r19_status':final_clearance['status'],
        'production_allocations':{reftext(r):v for r,v in spent_production.items()}}

def compare(w):
    raw=evaluate(w);live=w.closure_report();errors=list(raw['errors'])
    for a,b in zip(raw['claims'],live['claims']):
        for k in ('claim','historical_status','depth','current_status','predicates','duties'):
            if a[k]!=b[k]:errors.append('live/reference '+k+' mismatch')
    if len(raw['claims'])!=len(live['claims']):errors.append('claim count mismatch')
    return {'passed':not errors and raw['r19_independent_passed'],'errors':errors,'reference':raw}
