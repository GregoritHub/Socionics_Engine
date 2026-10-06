"""Independent offline route/state/ownership reconstruction for the R11 journal.

Uses the fixed positional fixture and independent cube permutations, never the
runtime route planner or active-hop routine. R10's independent consent, practice
and wallet reference remains a separate check.
"""
from collections import Counter
from dataclasses import replace
from hle.contracts import Kind, Ref, WorkStatus
from hle.crux import Perspective, Polarity
from hle.language_records import LanguageTransaction
from hle.organization_records import OrganizationTransaction
from hle.metabolism_records import MetabolicTransaction, ProcessingState
from hle.socion_records import Reception, SocionTransaction, ReceiveCommand
from hle.semantic_records import CancelSemantic
from tests.reference_processing import route_oracle

EXPECTED = {'Learn':('ti',False),'Produce':('fe',True),'Interpret':('ti',False),
 'Intend':('fi',True),'Formulate':('ne',False),'ReviewTerms':('ti',False),
 'Ratify':('fi',True),'Join':('fi',True),'Attend':('ni',False),
 'Dispute':('ti',False),'Leave':('fi',True),'Perform':('te',True)}
DONE=(WorkStatus.COMPLETED,WorkStatus.FAILED)


def active_at(plan, paid):
    used=0; result=plan.path[0]
    for i,unit in enumerate(plan.hop_units):
        used+=unit
        if paid<used: break
        result=plan.path[i+1]
    return result


def reconstruct(profiles, policy, semantic_policy, journal):
    states={p.owner:ProcessingState(Ref(Kind.CURSOR,
        f'processing:{len(p.owner.key)}:{p.owner.key}:{p.owner.revision}:state',1),
        p.owner,p.active,p.perspective,None) for p in profiles}
    types={p.owner:p.tim for p in profiles}
    owners={}; jobs={}; receptions={}; counts=Counter(); charges=Counter(); emissions=Counter()
    plans_seen={}; routes=Counter(); starts=Counter(); ends=Counter(); changes=[]
    for tx in journal:
        changed=()
        for m in tx.messages: emissions[states[m.sender].active]+=1
        if type(tx) in (LanguageTransaction,OrganizationTransaction):
            family='language' if type(tx) is LanguageTransaction else 'organization'
            a=tx.command.actor; key=(a,family,tx.command.task_id); previous=jobs.get(key)
            route=tx.job.route; state=states[a]
            assert owners.get(a) in (None,key), 'semantic ownership conflict'
            assert state.perspective==Perspective.I, 'invalid semantic ingress perspective'
            assert route.family==family and route.movement.route.origin==route.movement.route.destination==Perspective.I
            if previous is None:
                assert owners.get(a) is None and state.busy is None
                assert route.start_state==state.ref, 'route not rooted in current processing state'
                assert route.operation==type(tx.job.command.payload).__name__
                target,expense=EXPECTED[route.operation]
                assert route.movement.polarity==(Polarity.EXPENDITURE if expense else Polarity.ACCUMULATION)
                if semantic_policy.enabled:
                    plan=route.plan
                    oracle=route_oracle(types[a],state.active,target,expense,route.extent,
                        policy.typed_routing,policy.positional_prices)
                    assert (plan.path,plan.positions,plan.support_position,plan.support_index,plan.hop_units,plan.content_units)==oracle, 'route geometry/price mismatch'
                    assert plan.declared_type==types[a] and plan.routing_type==(types[a] if policy.typed_routing else 'ile')
                    assert tx.job.required==sum(oracle[4])+oracle[5]
                else:
                    assert route.plan is None and tx.job.required==route.extent
                plans_seen[key]=route; counts[route.operation+':jobs']+=1
                starts[state.active]+=1
            else:
                assert owners.get(a)==key and previous.outcome not in DONE
                assert tx.job.route==previous.route and tx.job.required==previous.required
                assert tx.job.candidate==previous.candidate, 'partial candidate silently changed'
            prior_paid=0 if previous is None else previous.paid
            charge=sum(w.completed_units for w in tx.works)
            assert tx.job.paid==prior_paid+charge and 0<=tx.job.paid<=tx.job.required
            assert tx.works[0].required_units==tx.job.required-prior_paid
            if type(tx.command) is CancelSemantic:
                assert charge==0 and tx.job.outcome==WorkStatus.FAILED and previous is not None
            if tx.job.outcome==WorkStatus.COMPLETED:
                assert tx.job.paid==tx.job.required and tx.extra==(tx.job.candidate,)
                assert tx.job.result==tx.job.candidate.ref
            else: assert tx.extra==() and tx.job.result is None, 'unpaid semantic output'
            expected_active=state.active if route.plan is None else active_at(route.plan,tx.job.paid)
            expected_busy=None if tx.job.outcome in DONE else 'semantic:'+family+':'+tx.command.task_id
            expected_state=replace(state,ref=replace(state.ref,revision=state.ref.revision+1),active=expected_active,busy=expected_busy)
            assert tx.state==expected_state, 'processing state differs from funded route'
            if tx.job.outcome in DONE:
                owners.pop(a,None); ends[tx.state.active]+=1
            else: owners[a]=key
            charges[route.operation]+=charge; counts[route.operation+':transactions']+=1
            counts['semantic_transactions']+=1
            counts['activation_changes']+=int(state.active!=tx.state.active)
            if route.plan: routes['>'.join(route.plan.path)]+=1
            states[a]=tx.state; jobs[key]=tx.job; changed=(a,)
        elif type(tx) is MetabolicTransaction:
            a=tx.command.actor
            assert owners.get(a) in (None,(a,'r4',tx.command.task_id)), 'R4 overlaps processing owner'
            assert tx.state.active==active_at(tx.job.plan,tx.job.completed_units)
            if tx.job.outcome in DONE: owners.pop(a,None)
            else: owners[a]=(a,'r4',tx.command.task_id)
            states[a]=tx.state; changed=(a,)
        elif type(tx) is SocionTransaction and type(tx.command) is ReceiveCommand:
            a=tx.command.actor; key=(a,'receive',tx.command.task_id)
            assert owners.get(a) in (None,key), 'reception overlaps processing owner'
            job=next(r for r in tx.extra if type(r) is Reception)
            state=next(r for r in tx.extra if type(r) is ProcessingState)
            assert state.active==active_at(job.plan,job.completed)
            assert state.perspective==states[a].perspective==Perspective.I
            if job.outcome==WorkStatus.COMPLETED: owners.pop(a,None)
            else: owners[a]=key
            receptions[key]=job; states[a]=state; changed=(a,)
        changes.append((tx.event.ref,changed))
    return {'states':states,'owners':owners,'changes':tuple(changes),'counts':dict(counts),
        'charges':dict(charges),'emitted_elements':dict(emissions),'routes':dict(routes),
        'starts':dict(starts),'ends':dict(ends),'distinct_plans':len(plans_seen)}


def check_world(w):
    result=reconstruct(w.profiles,w.policy,w.semantic_policy,w._journal)
    assert result['states']==w._processing_states
    assert result['changes']==tuple(w._processing_changes)
    for a,key in result['owners'].items():
        if key[1] in ('language','organization'): assert w._semantic_owners[a]==key[1:]
    assert len(w._semantic_owners)==sum(k[1] in ('language','organization') for k in result['owners'].values())
    return {k:v for k,v in result.items() if k not in ('states','owners','changes')} | {'processing_owners':len(result['owners']),'mismatches':0}
