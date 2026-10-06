"""R21 environment and bounded release driver; no credits or supplied capacities.

Seeds change actual history length, option ordering and the order of repeated
demand families. Evaluation observes results but never supplies a verdict to
the participant. All participant decisions use the existing engine APIs.
"""
import hashlib
import random
from dataclasses import replace
from contextlib import contextmanager
from hle.closure import ClosureWorld
from hle.individuation_demo import world, acquire_conversion, acquire_aspects, do
from hle.clearance_demo import begin, challenge
from hle.clearance_records import CASES
from hle.contracts import WorkStatus
from hle.world_records import Credit
from hle.codec import dumps


class BudgetStop(RuntimeError):
    pass


def make_world(tim, seed, budget):
    history = 3 + seed % 3
    b = world(tim, 'self', history=history, maintained=3, energy=budget,
              names=tuple(f's{seed}:{name}' for name in ('worker','lender','reviewer')))
    partners = tuple(replace(p,max_load=5) for p in b.circuit_partners)
    w = ClosureWorld(b.config,b.profiles,b.policy,b.agents,b.organization_policies,
        b.semantic_policy,b.workshop,b.autonomy,release=b.release,reviewers=b.reviewers,
        circuit_policy=b.circuit_policy,partners=partners)
    return w, history


def fresh(w):
    return ClosureWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,
        w.semantic_policy,w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,
        account_policy=w.account_policy,conversion_policy=w.conversion_policy,
        circuit_policy=w.circuit_policy,partners=w.circuit_partners)


@contextmanager
def bounded(w):
    execute = w.execute
    def emit(c):
        if isinstance(c,Credit):
            raise ValueError('R21 prohibits resource top-ups')
        event = execute(c)
        if event.outcome in (WorkStatus.PARTIAL,WorkStatus.DEFERRED):
            actor = getattr(c,'actor',getattr(getattr(c,'action',None),'actor',None))
            if actor is not None and min(w._wallets[actor].energy,w._wallets[actor].time)==0:
                raise BudgetStop(event.reason)
        return event
    w.execute = emit
    try:
        yield w
    finally:
        del w.execute


def permutation(seed, label):
    def permute(options):
        result=list(options)
        random.Random(f'{seed}:{label}').shuffle(result)
        return result
    return permute


def renewal_case(seed, n):
    # Three consecutive demand environments. Two actual changes at 34 and 67.
    families=['selection','temporal','obligations']
    random.Random(seed).shuffle(families)
    block=0 if n<34 else 1 if n<67 else 2
    variations=('equal_renewal','increased_requirement','changed_context_partner',
                'delay_or_changed_testimony')
    return families[block]+'.'+variations[n%4]


def opportunity(w,case,seed,n):
    start=len(w._journal)
    fs,item=challenge(w,case,allocate=False,prefix=f'r21:{seed}:renew:{n}',
        assess=False,permutation=permutation(seed,f'renew:{n}'))
    return {'number':n+1,'case':case,'start':start,'stop':len(w._journal),
            'orders':[f.key for f in fs],'item':item.key}


def run_episode(tim,seed,budget,horizon=100):
    w,history=make_world(tim,seed,budget)
    meta={'tim':tim,'seed':seed,'budget':budget,'history':history,'maintained':3,
          'stage':'development','opportunities':[],'cleared':False,'resource_stop':None,
          'cuts':{}}
    try:
        with bounded(w):
            acquire_conversion(w,history,3)
            meta['cuts']['conversion']=len(w._journal)
            acquire_aspects(w)
            meta['cuts']['aspects']=len(w._journal)
            do(w,'',w.config.actors[2],'support',flag=False)
            begin(w,allocate=False)
            meta['stage']='clearance'
            for case in CASES:
                challenge(w,case,allocate=False,permutation=permutation(seed,case))
            meta['cleared']=w.clearance_report()['status']=='cleared_in_scope'
            meta['cuts']['clearance']=len(w._journal)
            meta['stage']='continuation'
            if meta['cleared']:
                for n in range(horizon):
                    meta['opportunities'].append(opportunity(w,renewal_case(seed,n),seed,n))
            meta['stage']='finished'
    except BudgetStop as e:
        meta['resource_stop']=str(e)
    except Exception as e:
        meta['error']=type(e).__name__+': '+str(e)
    meta['status']=w.clearance_report()['status']
    meta['events']=len(w._journal)
    meta['work']={a.key:budget-w._wallets[a].energy for a in w.config.actors}
    return w,meta


def trace_digest(w):
    h=hashlib.sha256()
    for tx in w._journal:
        h.update(dumps(tx).encode());h.update(b'\n')
    return h.hexdigest()


def replay_witness(w):
    """A separately executed legal command policy on identical genesis/budget.

    This is a constructive feasibility witness, not a second independent
    learning algorithm. Raw-journal assessment separately checks consequences.
    """
    r=fresh(w)
    for tx in w._journal[1:]:
        if isinstance(tx.command,Credit):raise ValueError('credited policy is not budget feasible')
        r.execute(tx.command)
        if r._journal[-1]!=tx:raise AssertionError('separate legal policy differs')
    return r
