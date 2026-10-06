"""R14 finite environment setup and actor-only scheduler, not a task controller."""
from dataclasses import replace
import hashlib
from .contracts import Ref,Kind
from .autonomy import AutonomousWorld
from .autonomy_records import AutonomyPolicy,WorkshopConfig,AutonomousTransaction
from .metabolism_records import Profile,ProcessingPolicy
from .socion_records import AgentPolicy
from .model_a import ego
from .world_records import WorldConfig,Entity,Ownership,Wallet


def world(tim='sli',seed=101,energy=20000,borrowed=True,wear=True,due=True,may_lend=True,tool=True,
          native_use=True,teaching=False,work_limit=64,intentions=None):
    prefix='s'+str(seed)+':'
    borrower=Ref(Kind.ENTITY,prefix+'worker',1);lender=Ref(Kind.ENTITY,prefix+'partner',1)
    actors=(borrower,lender)
    equipment=Ref(Kind.ENTITY,prefix+'tool',1);piece=Ref(Kind.ENTITY,prefix+'piece',1)
    context=Ref(Kind.CONTEXT,'workshop',1)
    things=[Entity(piece,piece.key,'object')];owns=[Ownership(piece,borrower)];conditions=[(piece,'raw')]
    if tool:
        things.append(Entity(equipment,equipment.key,'object'));owns.append(Ownership(equipment,lender if borrowed else borrower));conditions.append((equipment,'clean'))
    if teaching:
        teacher_tool=Ref(Kind.ENTITY,prefix+'teacher_tool',1);teacher_piece=Ref(Kind.ENTITY,prefix+'teacher_piece',1)
        things.extend((Entity(teacher_tool,teacher_tool.key,'object'),Entity(teacher_piece,teacher_piece.key,'object')))
        owns.extend((Ownership(teacher_tool,lender),Ownership(teacher_piece,lender)))
        conditions.extend(((teacher_tool,'clean'),(teacher_piece,'raw')))
    # Seeded permutation using an already allowlisted standard-library primitive.
    # No RNG/latent future state is supplied to participant policy.
    things.sort(key=lambda e: hashlib.sha256((str(seed)+e.ref.key).encode()).digest())
    owns.sort(key=lambda o: hashlib.sha256((str(seed)+o.item.key).encode()).digest())
    conditions.sort(key=lambda c: hashlib.sha256((str(seed)+c[0].key).encode()).digest())
    config=WorldConfig(context,tuple(Entity(a,a.key,'actor') for a in actors)+tuple(things),actors,tuple(owns),
        tuple(Wallet(a,energy,energy) for a in actors),(),((borrower,lender),(lender,borrower)))
    profiles=(Profile(borrower,tim,ego(tim)[0]),Profile(lender,'iee','ne'))
    policies=(AutonomyPolicy(borrower,primitives=tuple(x for x in ('inspect','use','clean','lend','return') if native_use or x!='use'),work_limit=work_limit),
        AutonomyPolicy(lender,may_lend=may_lend,work_limit=work_limit))
    if intentions is not None:policies=tuple(replace(p,intentions=intentions) for p in policies)
    return AutonomousWorld(config,profiles,ProcessingPolicy(),tuple(AgentPolicy(a) for a in actors),
        workshop=WorkshopConfig(tuple(conditions),wear,due),autonomy=policies)


def run(w,horizon=800):
    steps=0
    for _ in range(horizon):
        changed=False
        for actor in w.config.actors:
            if w.autonomy_ready(actor):
                w.autonomy_step(actor);steps+=1;changed=True
        if not changed:break
    return {'opportunities':steps,'horizon_exhausted':any(w.autonomy_ready(a) for a in w.config.actors),'events':len(w._journal),
        'resource_censored':any(min(w._wallets[a].energy,w._wallets[a].time)==0 and (w.autonomy_state(a).pending is not None or a in w._active_turn or not w.autonomy_state(a).initialized) for a in w.config.actors)}


def report(w,scheduling=None):
    acts=[tx for tx in w._journal if tx.event.action.startswith('r14.') and tx.event.action!='r14.consider']
    histories=[]
    for tx in w._journal:
        if type(tx) is AutonomousTransaction and tx.demands:
            for d in tx.demands:
                histories.append({'created_event':tx.event.ref.key,'actor':d.owner.key,'item':d.item.key,'family':d.specification.family,
                    'origin':d.specification.origin.value,'status':d.status,'origins':[r.key for r in d.specification.origin_events],
                    'memory':[r.key+'@'+str(r.revision) for r in d.specification.material_lineage]})
    states=[{'actor':a.key,'state':w.autonomy_state(a).phase,'decision':None if w.autonomy_state(a).decision is None else w.autonomy_state(a).decision.kind,
        'reason':None if w.autonomy_state(a).decision is None else w.autonomy_state(a).decision.reason} for a in w.config.actors]
    facts=[{'item':item.key,'relation':rel,'value':p.object.key if type(p.object) is Ref else p.object} for (item,rel,ctx),p in w._facts.items()
        if rel in ('condition','loan_active','return_due','owned_by')]
    return {'scheduling':scheduling,'actions':[{'action':x.event.action,'actor':x.command.actor.key,'inputs':[i.key for i in x.command.inputs],
        'outcome':x.event.outcome.value,'event':x.event.ref.key} for x in acts], 'demands':histories,'participants':states,
        'world_evaluator_facts':facts,'shell_assessment':'unassessed; no R14 automatic Shell classification'}


def main_demo():
    w=world();r=run(w);summary=report(w,r)
    restored=AutonomousWorld.restore(w.checkpoint())
    summary['exact_restore']=restored.checkpoint()==w.checkpoint()
    summary['milestone']='R14';return summary
