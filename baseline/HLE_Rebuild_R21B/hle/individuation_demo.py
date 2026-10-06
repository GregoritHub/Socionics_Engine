"""R18 opportunities and fresh stateless controller; no supplied learned answers."""
from dataclasses import replace
from .individuation import IndividuationWorld
from .individuation_records import *
from .conversion_demo import world as conversion_world, offer as loan_offer, run as conversion_run
from .compensation_demo import introduce
from .conversion_records import ConversionCommand
from .concept_demo import fund_command
from .model_a import TYPES, stack, element_at, ego
from .metabolism_records import Profile
from .world_records import Credit

PAIR_SEATS=((1,7),(6,4),(2,8),(5,3))

def dual_of(tim):
    return next(t for t in TYPES if stack(t)[:2]==stack(tim)[4:6])

def world(tim='sli',mode='self',history=1,maintained=1,**kwargs):
    cp=kwargs.pop('circuit_policy',None) or CircuitPolicy(correction=mode)
    b=conversion_world(history=history,maintained=maintained,**kwargs)
    helper_type=dual_of(tim) if mode=='dual' else tim
    learner,partner,helper=b.config.actors
    profiles=(Profile(learner,tim,ego(tim)[0]),Profile(partner,'iee',ego('iee')[0]),Profile(helper,helper_type,ego(helper_type)[0]))
    return IndividuationWorld(b.config,profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,
        b.workshop,b.autonomy,release=b.release,reviewers=b.reviewers,circuit_policy=cp)

def acquire_conversion(w,history=1,maintained=1):
    conversion_run(w)
    for i in range(history+maintained):introduce(w,i);conversion_run(w)
    actor=w.config.actors[0]
    fund_command(w,ConversionCommand('conversion:release','conversion:release',actor,'release',work_limit=256))
    conversion_run(w)
    for i in range(history+maintained,history+maintained+2):introduce(w,i);conversion_run(w)
    if actor not in w._capacities:raise AssertionError('R17 acquisition missing')
    return w

def command(w,key,actor,op,**kw):
    ident='r18:'+key+':'+op+':'+str(len(w._journal))
    return CircuitCommand(ident,ident,actor,key,op,**kw)

def do(w,key,actor,op,**kw):return fund_command(w,command(w,key,actor,op,**kw))

def make_offer(w,key,focus,circuit=0,held=False,all_traps=False,partner=None):
    actor,original_partner,helper=w.config.actors
    partner=partner or original_partner
    from .individuation_logic import epoch_key
    epoch=epoch_key(key)
    good=WorkOption(key+':usable',observed_epoch=epoch,start=4 if held else 2,ready_at=3 if held else 1,cost=2,output=6)
    # These are environmental counterexamples, not input annotations carrying
    # the target aspect or an answer. Identifiers vary across held-out orders.
    defects={
        'ne':dict(available=False),
        'si':dict(condition='dirty',observed_epoch=max(0,epoch-1)),
        'ni':dict(ready_at=8),
        'se':dict(load=4),
        'te':dict(output=1),
        'ti':dict(claims=(('station','one'),('station','two'))),
        'fi':dict(license='exclusive'),
        'fe':dict(start=9),
    }
    aspects=ASPECTS if all_traps else (focus,)
    bad=tuple(replace(good,key=key+':offer:'+str(i),cost=1,**defects[a]) for i,a in enumerate(aspects))
    # Partner can carry load=4 so se differs from fe; deadline permits slot=9
    # so fe differs from ni. Each missing rule has a distinct trap.
    return CircuitOffer('offer:'+key,key,actor,partner,helper,bad+(good,),focus,circuit,epoch,due=12,budget=3)

class CircuitController:
    """A new instance needs only live records; no hidden learned state."""
    def next(self,w,key,delegate=False):
        o=w._circuit_orders[key];f=o.offer
        if o.closed:return None
        if o.menu is None:return command(w,key,f.partner,'menu')
        if o.stage==0:return command(w,key,f.learner,'choose')
        if f.circuit==0:
            if o.stage==1:return command(w,key,f.helper if delegate else f.learner,'apply')
            if o.stage==2:
                return command(w,key,f.partner,'review') if o.review is None else command(w,key,f.learner,'coordinate')
        else:
            if o.stage==1:
                return command(w,key,f.partner,'review') if o.review is None else command(w,key,f.learner,'organize')
            if o.stage==2:return command(w,key,f.helper if delegate else f.learner,'apply')
        if o.signal is None:
            assisted=w.circuit_policy.correction!='self' and w._work_partners[f.helper].helper_available
            return command(w,key,f.helper if assisted else f.learner,'consult' if assisted else 'inspect')
        return command(w,key,f.learner,'feedback')

def run_order(w,offer,delegate=False):
    w.execute(offer)
    for _ in range(20):
        # Deliberately construct a fresh controller each decision.
        cmd=CircuitController().next(w,offer.key,delegate)
        if cmd is None:return w._circuit_orders[offer.key]
        event=fund_command(w,cmd)
        if event.outcome not in (WorkStatus.COMPLETED,WorkStatus.FAILED):return w._circuit_orders[offer.key]
    raise AssertionError('finite work-order controller did not terminate')

def acquire_aspects(w):
    a=w.config.actors[0];tim=w._profiles[a].tim
    for pair_index,pair in enumerate(PAIR_SEATS):
        for seat in pair:
            aspect=element_at(tim,seat)
            for trial in range(2):
                run_order(w,make_offer(w,f'acquire:{seat}:{trial}',aspect,pair_index%2))
    return w

def case(tim='sli',mode='self',history=1,maintained=1,renew=True,**kwargs):
    w=world(tim,mode,history,maintained,**kwargs)
    # Policy is a real independently owned partner availability resource.
    # Load=4 remains schedulable to distinguish the actor's own budget guard.
    # Set at genesis, before any outcome is known.
    partners=tuple(replace(p,max_load=5) for p in w.circuit_partners)
    w=IndividuationWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
        w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,circuit_policy=w.circuit_policy,partners=partners)
    acquire_conversion(w,history,maintained)
    for actor,wallet in tuple(w._wallets.items()):
        w.execute(Credit('r18:match:'+actor.key,actor,200000-wallet.energy,200000-wallet.time,'R18 matched comparison allocation'))
    start=len(w._journal)
    acquire_aspects(w)
    acquired=len(w._journal)
    do(w,'',w.config.actors[2],'support',flag=False)
    if renew:
        for circuit in (0,1):run_order(w,make_offer(w,'held:'+str(circuit),element_at(tim,1),circuit,held=True,all_traps=True))
        # Original physical native use, care and conditional return still work.
        for i in range(history+maintained+2,history+maintained+4):loan_offer(w,i);conversion_run(w)
    return w,{'tim':tim,'mode':mode,'start':start,'acquired':acquired,'history':history,'maintained':maintained}
