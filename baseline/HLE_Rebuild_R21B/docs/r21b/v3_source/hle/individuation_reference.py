"""Independent R18 raw-journal observer, never a participant input.

Does not call the live selector, learner, constraints, current-capacity view,
or circuit implementation. Reconstructs messages, outcomes, capacities, paired
ownership, four perspective effects and accounting from immutable transactions.
"""
from .individuation_records import *
from .contracts import WorkStatus
from .world_records import ENERGY,TIME
from .model_a import stack,fields,position_of,element_at
from .development_structure import portage,lap
from .conversion_records import ConversionTransaction

PAIRS={'Hero':(1,7),'Child':(6,4),'Parent':(2,8),'Spirit':(5,3)}
CIRCUITS=(('I','ITS','IT','WE','I'),('I','WE','ITS','IT','I'))

def expected_failures(f,o,permissions,acks):
    if o is None:return ('no_feasible_choice',)
    rows={}
    for k,v in o.claims:rows.setdefault(k,set()).add(v)
    tests=(('ne',o.available),('si',o.condition=='clean' and o.observed_epoch==f.epoch),
        ('ni',o.start>=o.ready_at and o.start+o.duration<=f.due),('se',o.load<=f.budget),
        ('te',o.cost<=f.credits and o.output>=f.minimum_output),('ti',all(len(v)==1 for v in rows.values())),
        ('fi',permissions.get(o.key,False)),('fe',acks.get(o.key,False)))
    return tuple(a for a,valid in tests if not valid)

def evaluate(world):
    errors=[];records={};orders={};caps={};current={};partners={p.actor:p for p in world.circuit_partners}
    balances={w.actor:(w.energy,w.time) for w in world.config.wallets}
    spent=0;aspect_work={};channels=[];shared={};total_output=0;counts={};root_material=None;root_current=False;root_access=world.conversion_policy.material_access
    tim=world.profiles[0].tim;actor=world.config.actors[0];withdraw_at=None
    causal_works=set();source_unchanged=True;expected_circuit_phases={};signatures=[]
    def require(ok,label):
        if not ok:errors.append(label)
    for tx in world._journal:
        for wr in tx.works:
            b={x.unit:x.amount for x in wr.before};a={x.unit:x.amount for x in wr.after}
            d={x.unit:x.amount for x in wr.charged};c={x.unit:x.amount for x in wr.credited}
            require((b[ENERGY],b[TIME])==balances[wr.owner],'wallet predecessor')
            require(all(a[u]==b[u]+c.get(u,0)-d.get(u,0) and a[u]>=0 for u in (ENERGY,TIME)),'conserved paid work')
            balances[wr.owner]=a[ENERGY],a[TIME];records[wr.ref]=wr;causal_works.add(wr.ref)
        records[tx.event.ref]=tx.event
        for o in tx.observations:records[o.ref]=o
        if type(tx) is ConversionTransaction and tx.capacity is not None and tx.capacity.owner==actor:
            root_material=tx.capacity.material;root_current=tx.capacity.current
        if type(tx) is ConversionTransaction and tx.command.actor==actor and tx.event.outcome==WorkStatus.COMPLETED:
            if tx.command.operator in ('restrict','restore_access'):root_access=tx.command.operator=='restore_access'
        if type(tx) is not CircuitTransaction:continue
        cmd=tx.command
        if type(cmd) is CircuitOffer:
            require(tx.order is not None and tx.order.offer==cmd and not tx.capacities,'offer is not a learned answer')
            records[tx.order.bulletin]=cmd;orders[cmd.key]=tx.order;counts[cmd.key]=0
            continue
        j=tx.job
        spent+=sum(x.amount for wr in tx.works for x in wr.charged if x.unit==ENERGY)
        if j.outcome!=WorkStatus.COMPLETED:
            require(tx.order is None and tx.communication is None and tx.signal is None and not tx.capacities and tx.account is None,'partial/stale publication')
            continue
        previous=orders.get(cmd.order)
        if previous is not None:
            f=previous.offer
            phases=('choose','apply','coordinate','feedback') if f.circuit==0 else ('choose','organize','apply','feedback')
            if cmd.operator in phases:
                phase=phases.index(cmd.operator)
                require(previous.stage==phase and tx.order.stage==phase+1,'phase ordering')
                origin=position_of(world._profiles[cmd.actor].tim,f.focus)
                for _ in range(phase):origin=lap(origin)
                expected=portage(origin,'cp')
                require(j.plan.positions[-1]==expected,'paid conjugate lap target')
                movement=tx.order.movements[-1]
                require((movement.route.origin.value,movement.route.destination.value)==CIRCUITS[f.circuit][phase:phase+2],'formal route composition')
                aspect_work.setdefault(f.focus,0);aspect_work[f.focus]+=j.plan.required
            if cmd.operator=='choose':
                require(tx.order.menu in records and records[tx.order.menu].sender==f.partner,'real menu before choice')
                for ref in tx.order.uses:
                    require(ref in caps and caps[ref].owner==cmd.actor and current.get(caps[ref].aspect)==ref,'own current retained use')
            if cmd.operator=='apply':
                p=partners[f.partner];option=next((x for x in f.options if x.key==previous.chosen),None)
                perms={x.key:x.license in p.licenses for x in f.options}
                acks={x.key:p.willing and x.start not in p.unavailable_slots and x.load<=p.max_load for x in f.options}
                reasons=expected_failures(f,option,perms,acks)
                if f.circuit==1 and not previous.credited:reasons=tuple(dict.fromkeys(reasons+('unaccepted_arrangement',)))
                key=None if option is None else (f.partner,f.epoch,option.start)
                if option is not None and shared.get(key,0)+option.load>f.budget:reasons=tuple(dict.fromkeys(reasons+('shared_load_exhausted',)))
                s=tx.signal
                require(s.errors==reasons and s.success==(not reasons),'physical consequence reconstruction')
                require(s.performer==cmd.actor,'real performer')
                output=0 if reasons else option.output
                require(s.produced==output,'real output amount')
                if output:
                    shared[key]=shared.get(key,0)+option.load;total_output+=output
                    changes={c.after.relation:c.after.object for c in tx.event.changes if c.after is not None}
                    require(changes.get('r18.total_output')==total_output and changes.get('r18.total_load')==shared[key],'shared system effect')
            if cmd.operator in ('inspect','consult'):
                s=tx.signal;original=records[previous.outcome]
                require((s.order,s.option,s.success,s.errors,s.produced,s.performer)==
                    (original.order,original.option,original.success,original.errors,original.produced,original.performer),'correction content fidelity')
                channels.append({'order':s.order,'option':s.option,'success':s.success,'errors':s.errors,'produced':s.produced,'performer':s.performer.key})
            if cmd.operator=='feedback':
                require(previous.signal in records,'observed feedback')
                for c in tx.capacities:
                    failure=records.get(c.failure);practice=records.get(c.practice)
                    require(type(failure) is CircuitSignal and not failure.success and c.aspect in failure.errors,'observed contrast')
                    require(type(practice) is CircuitSignal and practice.success and practice.performer==c.owner and practice.order!=failure.order,'independent own practice')
                    require(c.aspect in previous.provisional and previous.credited,'practiced candidate and accepted contribution')
                    require(c.material==root_material and c.acquisition and set(c.acquisition)<=causal_works,'original material and paid acquisition')
                    if position_of(tim,c.aspect) in (5,3):
                        expected_deps={current.get(element_at(tim,p)) for p in (1,7,6,4,2,8)}
                        require(None not in expected_deps and set(c.dependencies)==expected_deps,'Spirit prior integration')
        if tx.communication is not None:records[tx.communication.ref]=tx.communication
        if tx.signal is not None:records[tx.signal.ref]=tx.signal
        for cap in tx.capacities:
            caps[cap.ref]=cap;records[cap.ref]=cap
            if cap.current:current[cap.aspect]=cap.ref
            else:current.pop(cap.aspect,None)
        if tx.partner is not None:
            partners[tx.partner.actor]=tx.partner
            if not tx.partner.helper_available:withdraw_at=tx.event.when.tick
        if tx.order is not None:orders[cmd.order]=tx.order;records[tx.order.ref]=tx.order
    # Dependency invalidation is independently reconstructed.
    while True:
        live=set(current.values());next_current={a:r for a,r in current.items() if set(caps[r].dependencies)<=live}
        if next_current==current:break
        current=next_current
    if not (root_current and root_access and world.circuit_policy.material_access):current={}
    held=[]
    for key,o in orders.items():
        if not key.startswith('held:'):continue
        result=records[o.outcome]
        held.append({'order':key,'circuit':o.offer.circuit,'closed':o.closed,'success':result.success,'credited':o.credited,
            'independent':result.performer==o.offer.learner,'aspects_used':sorted(caps[r].aspect for r in o.uses),
            'routes':[m.route.name for m in o.movements],'errors':list(result.errors)})
        require(withdraw_at is not None and records[result.source].when.tick>withdraw_at,'post-withdrawal held demand')
    pairs={name:{'positions':list(pair),'aspects':[element_at(tim,p) for p in pair],
        'retained':all(element_at(tim,p) in current for p in pair),
        'own_practice':[caps[current[element_at(tim,p)]].practice.key for p in pair if element_at(tim,p) in current]}
        for name,pair in PAIRS.items()}
    r18_1=len(current)==8 and len(held)>=2 and all(h['success'] and h['independent'] and len(h['aspects_used'])==8 for h in held)
    r18_2=all(v['retained'] and len(v['own_practice'])==2 for v in pairs.values()) and r18_1
    r18_3={h['circuit'] for h in held if h['success'] and h['credited'] and h['closed']}=={0,1}
    return {'schema':'hle-r18-evaluation-v1','tim':tim,'mode':world.circuit_policy.correction,'integrity_passed':not errors,'errors':errors,
        'gates':{'R18.1':r18_1,'R18.2':r18_2,'R18.3':r18_3},'current_aspects':sorted(current),'complexes':pairs,'held_out':held,
        'paid_work':spent,'aspect_work':aspect_work,'correction_content':channels,'shared_output':total_output,
        'fixed_stack':list(stack(tim)),'fixed_dimensions':[fields(p)['dimensionality'] for p in range(1,9)],
        'original_material':None if root_material is None else root_material.key,
        'clearance':'unassessed: R19 remains open','recursive_closure':'unassessed: R20 remains open'}
