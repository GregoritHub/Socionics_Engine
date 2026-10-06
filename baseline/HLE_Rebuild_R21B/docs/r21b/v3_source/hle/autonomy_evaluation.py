"""Offline R14 evidence. Never imported by the participant decision policy."""
import hashlib
from .autonomy_demo import world,run,report
from .autonomy import AutonomousWorld
from .autonomy_records import AutonomousTransaction,AutonomyTurn,WorkshopCommand,INTENT_REL
from .contracts import WorkStatus
from .development_evaluation import accounting


def restart(w):
    return AutonomousWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,
        w.semantic_policy,w.workshop,w.autonomy)


def audit(w):
    """Independent ledger fold plus candidate-publication and paid-progress checks."""
    result=accounting(w);turns={};domain={}
    for tx in w._journal:
        if type(tx) is not AutonomousTransaction:continue
        key=(tx.command.actor,tx.command.task_id)
        bucket=turns if type(tx.command) is AutonomyTurn else domain
        bucket[key]=bucket.get(key,0)+sum(work.completed_units for work in tx.works)
        if tx.decision_job is not None:
            if tx.decision_job.paid<tx.decision_job.plan.required and (tx.participant is not None or tx.demands):
                raise AssertionError('unpaid policy output')
            if tx.participant is not None and tx.decision_job.outcome!=WorkStatus.COMPLETED:raise AssertionError('premature decision')
    for key,job in w._turn_jobs.items():
        if turns[key]!=job.paid:raise AssertionError('decision cost mismatch')
    for key,job in w._workshop_jobs.items():
        if domain[key]!=job.paid:raise AssertionError('physical cost mismatch')
    result.update({'paid_decision_jobs':len(turns),'physical_jobs':len(domain),'decision_units':sum(turns.values()),'physical_units':sum(domain.values())})
    return result


def reference_demands(w):
    """Independent bounded reference over exact paid-recall snapshots.

    Reconstructs known predicates from the snapshot references, without calling
    the live policy or querying simulator Truth. This is not a Shell detector.
    """
    checked=0;families={}
    for tx in w._journal:
        if type(tx) is not AutonomousTransaction or tx.participant is None or tx.decision_job.snapshot.recall is None:continue
        snapshot=tx.decision_job.snapshot;actor=tx.command.actor
        if not snapshot.access_valid:continue
        rr=w._records[snapshot.recall]
        if rr.truncated:continue
        intentions=set();facts={}
        for ref,indices in snapshot.memories:
            m=w._records[ref]
            if m.owner!=actor:raise AssertionError('foreign memory in participant snapshot')
            for i in indices:
                p=m.content[i]
                if p.relation==INTENT_REL and p.subject==actor:intentions.add(p.object)
                else:facts.setdefault(p.subject,{})[p.relation]=p.object
        expected=set()
        for item,f in facts.items():
            if 'care_for_used_tools' in intentions and f.get('workshop_kind')=='tool' and f.get('owned_by')==actor and f.get('condition')=='dirty':expected.add(('maintenance',item))
            if 'honor_accepted_loans' in intentions and f.get('workshop_kind')=='tool' and f.get('borrower')==actor and f.get('loan_active') is True and f.get('return_due') is True:expected.add(('return_commitment',item))
            if 'prepare_owned_workpieces' in intentions and f.get('workshop_kind')=='workpiece' and f.get('owned_by')==actor and f.get('condition')=='raw':expected.add(('production',item))
        observed={(d.family,d.item) for d in tx.participant.decision.demands}
        if expected!=observed:raise AssertionError('incremental policy/reference demand mismatch')
        generated={(d.specification.family,d.item) for d in tx.demands if d.status!='resolved' and (d.specification.family,d.item) in expected}
        if generated!=expected:raise AssertionError('missing generated demand record')
        checked+=1
        for family,_ in observed:families[family]=families.get(family,0)+1
    return {'decisions_checked':checked,'family_occurrences':dict(families),'passed':True}


def all_prefixes(w):
    """Check every journal prefix under the same remaining external command inputs."""
    final=w.checkpoint();current=restart(w);count=0;categories={}
    for n in range(1,len(w._journal)+1):
        if n>1:current.execute(w._journal[n-1].command)
        restored=AutonomousWorld.restore(current.checkpoint())
        for tx in w._journal[n:]:restored.execute(tx.command)
        if restored.checkpoint()!=final:raise AssertionError('full continuation differs at prefix '+str(n))
        count+=1;tx=w._journal[n-1]
        category=type(tx.command).__name__+':'+tx.event.outcome.value
        categories[category]=categories.get(category,0)+1
    return {'prefixes':count,'cutpoints':dict(categories),'comparison':'same remaining typed external inputs; decisions are recomputed and full transactions checked',
        'final_sha256':hashlib.sha256(final.encode()).hexdigest(),'passed':True}


def fresh_schedulers():
    """New schedulers at completed round boundaries choose all future work anew."""
    w=world();copies=[]
    for i in range(85):
        for actor in w.config.actors:
            if w.autonomy_ready(actor):w.autonomy_step(actor)
        if i in (5,25,45,60,75):copies.append((i,AutonomousWorld.restore(w.checkpoint())))
        if not any(w.autonomy_ready(a) for a in w.config.actors):break
    run(w);rows=[]
    for boundary,other in copies:
        run(other)
        equal=other.checkpoint()==w.checkpoint()
        if not equal:raise AssertionError('fresh scheduler changed subsequent independently selected work')
        rows.append({'round_boundary':boundary,'exact':True})
    return {'fresh_controllers':len(rows),'cases':rows,'passed':True}


def positive(w):
    a,b=w.config.actors[:2]
    piece=next(r for r,_ in w.workshop.conditions if r.key.endswith(':piece'))
    tool=next(r for r,_ in w.workshop.conditions if r.key.endswith(':tool'))
    f=w.truth
    qualifying={d.specification.family for d in w._demand_records.values() if d.owner==a}
    return (f.current_fact(piece,'condition',w.config.context).object=='ready'
        and f.current_fact(tool,'condition',w.config.context).object=='clean'
        and f.current_fact(tool,'owned_by',w.config.context).object==b
        and f.current_fact(tool,'loan_active',w.config.context).object is False
        and {'maintenance','return_commitment'}<=qualifying
        and all(d.status=='resolved' for d in w.own_demands(a)))
