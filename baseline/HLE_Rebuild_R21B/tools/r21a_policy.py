"""Declared constructive feasibility policy, launched independently from genesis.

No candidate journal is an input. No evaluator status controls the schedule.
The unchanged paid primitives are a baseline; a budget stop is not feasibility.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.clearance_records import EpisodeResourceContract, CASES
from hle.resource_contracts import PROTOCOL_ID, PROTOCOL_SHA256, BUDGETS
from hle.contracts import Ref, Kind
from hle.clearance_demo import begin, challenge
from hle.individuation_demo import acquire_conversion, acquire_aspects, do
from r21_workloads import make_world, fresh, bounded, BudgetStop, permutation, renewal_case

POLICY_ID = 'r21a.independent-construction.v1'


def protocol():
    path = ROOT/'docs/r21a/Protocol_R21_v2.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('frozen R21 v2 contract changed')
    return json.loads(path.read_text())


def make_contract_world(tim, seed, regime):
    w, history = make_world(tim, seed, BUDGETS[regime])
    w.execute(EpisodeResourceContract('r21a:contract', f'{tim}:{seed}:{regime}', regime,
                                     seed, PROTOCOL_ID, PROTOCOL_SHA256))
    return w, history


def genesis_digest(w):
    return hashlib.sha256(fresh(w).checkpoint().encode()).hexdigest()


def episode_scope(w):
    declaration = w._journal[1].command
    if type(declaration) is not EpisodeResourceContract:
        raise ValueError('journaled v2 contract required')
    tim = next(p.tim for p in w.profiles if p.owner == w.config.actors[0])
    return {'tim': tim, 'seed': declaration.seed, 'regime': declaration.regime,
            'episode_id': declaration.episode_id, 'protocol_sha256': declaration.protocol_sha256,
            'genesis_sha256': genesis_digest(w), 'history': 3+declaration.seed % 3,
            'maintained': 3, 'clearance_cases': list(CASES),
            'horizon': [renewal_case(declaration.seed, n) for n in range(100)]}


def run_reference_policy(tim, seed, regime, *, evaluation=False):
    spec = protocol()
    if seed in spec['evaluation']['evaluation_seeds'] and not evaluation:
        raise ValueError('fresh held-out seeds are reserved for R21C')
    w, history = make_contract_world(tim, seed, regime)
    meta = {'policy_id': POLICY_ID, 'construction': 'independent_from_genesis',
            'scope': episode_scope(w), 'stage': 'development', 'cuts': {},
            'opportunities': [], 'resource_stop': None}
    # The environment's original maintenance item is fixed by its history,
    # not obtained from the clearance assessor.
    item = Ref(Kind.ENTITY, 'tool:'+str(history), 1)
    try:
        with bounded(w):
            acquire_conversion(w, history, 3)
            meta['cuts']['conversion'] = len(w._journal)
            acquire_aspects(w)
            meta['cuts']['aspects'] = len(w._journal)
            do(w, '', w.config.actors[2], 'support', flag=False)
            begin(w, allocate=False)
            meta['stage'] = 'clearance'
            for case in CASES:
                challenge(w, case, allocate=False, permutation=permutation(seed, case), original_item=item)
            meta['cuts']['clearance'] = len(w._journal)
            meta['stage'] = 'continuation'
            # Evaluator status is deliberately not consulted here.
            for n in range(100):
                case = renewal_case(seed, n)
                start = len(w._journal)
                fs, physical_item = challenge(w, case, allocate=False, assess=False,
                    prefix=f'r21:{seed}:renew:{n}', permutation=permutation(seed, f'renew:{n}'),
                    original_item=item)
                meta['opportunities'].append({'number': n+1, 'case': case, 'start': start,
                    'stop': len(w._journal), 'orders': [f.key for f in fs], 'item': physical_item.key})
            meta['cuts']['horizon'] = len(w._journal)
            meta['stage'] = 'finished'
    except BudgetStop as exc:
        meta['resource_stop'] = str(exc)
    except Exception as exc:
        meta['error'] = type(exc).__name__+': '+str(exc)
    meta['events'] = len(w._journal)
    return w, meta
