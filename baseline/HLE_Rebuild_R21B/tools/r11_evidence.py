#!/usr/bin/env python3
"""Execute the predeclared R11 panel and retain every result and full journal."""
import argparse
import gc
import gzip
import hashlib
import itertools
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.organization import OrganizationWorld
from hle.organization_records import Formulate, OrganizationCommand
from hle.socion_records import AgentPolicy, ConfigureAgent
from hle.world_records import INSPECT, Tick
from tools.r10_oracle import check_world as check_protocol
from tools.r11_oracle import check_world as check_routing
from tools.r11_controls import causal_panel
from tests.reference_processing import route_oracle

def check_world(w):
    return check_protocol(w) | {"routing":check_routing(w)}
from tools.r11_workloads import Driver, make_world, prepare_candidates, run_case, snapshot


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def stats(values):
    values = sorted(values)
    return {'n': len(values), 'total_ms': sum(values), 'median_ms': statistics.median(values),
        'p95_ms': values[math.ceil(.95 * len(values)) - 1], 'max_ms': max(values)}


def save(out, name, value):
    path = out / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def checkpoint_metrics(w, prefix=None):
    start = time.perf_counter(); cp = w.checkpoint(); save_ms = (time.perf_counter() - start) * 1000
    begin = time.perf_counter()
    restored = OrganizationWorld.restore(prefix or cp)
    prefix_events = len(restored._journal)
    for tx in w._journal[prefix_events:]:
        restored.execute(tx.command)
        assert restored._journal[-1] == tx, 'suffix transaction mismatch'
    replay_ms = (time.perf_counter() - begin) * 1000
    assert restored.checkpoint() == cp, 'final checkpoint differs after continuation'
    events = len(w._journal)
    result = {'events': events, 'bytes': len(cp.encode()), 'bytes_per_event': len(cp.encode()) / events,
        'save_ms': save_ms, 'replay_ms': replay_ms, 'restored_prefix_events': prefix_events,
        'continued_events': events - prefix_events, 'exact': True, 'sha256': digest(cp),
        'timing_passed': save_ms <= 2 * events + 1000 and replay_ms <= 5 * events + 1000,
        'bytes_passed': len(cp.encode()) <= 20000 * events}
    return cp, result


def semantic_signature(row):
    return [{k: v for k, v in cycle.items() if k != 'diagnostics'} for cycle in row['cycles']]


def evaluate_main(out, plan):
    spec = plan['main_panel']; rows = []
    for n, prefix, resource, seed in itertools.product(spec['populations'],
            spec['initial_inspection_prefixes'], spec['resources'], spec['workload_seeds']):
        name = f'n{n}-h{prefix}-{resource}-s{seed}'
        begin = time.perf_counter()
        d, row, continuation = run_case(n, prefix, resource, seed, spec['cycles'],
            spec['initial_rounds'], spec['revised_rounds'], spec['successor_rounds'])
        assert not row['blocked'] and len(row['cycles']) == spec['cycles'], row
        begin_oracle = time.perf_counter(); oracle = check_world(d.w)
        oracle_ms = (time.perf_counter() - begin_oracle) * 1000
        cp, persistence = checkpoint_metrics(d.w, continuation)
        quarter = max(1, len(d.timings) // 4)
        timing = {**stats(d.timings), 'first_quarter': stats(d.timings[:quarter]),
            'last_quarter': stats(d.timings[-quarter:]),
            'by_action': {k: stats(v) for k, v in sorted(d.by_action.items())}}
        timing['passed'] = timing['p95_ms'] <= 20 and timing['last_quarter']['median_ms'] <= max(
            4 * timing['first_quarter']['median_ms'], 2)
        expected_runs = spec['cycles'] * (n - 1) * (
            spec['initial_rounds'] + spec['revised_rounds'] + spec['successor_rounds'])
        actual_runs = sum(c['initial_fulfilled'] + c['revised_fulfilled'] + c['successor_fulfilled'] for c in row['cycles'])
        row.update({'case': name, 'oracle': oracle, 'oracle_ms': oracle_ms,
            'oracle_timing_passed': oracle_ms <= 5 * persistence['events'] + 1000,
            'checkpoint': persistence, 'active_timing': timing,
            'fulfilled_organization_runs': actual_runs, 'expected_organization_runs': expected_runs,
            'duration_seconds': time.perf_counter() - begin,
            'journal_file': 'journals/' + name + '.checkpoint.json.gz'})
        row['passed'] = (actual_runs == expected_runs and timing['passed'] and
            persistence['timing_passed'] and persistence['bytes_passed'] and row['oracle_timing_passed'])
        path = out / row['journal_file']; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(cp.encode(), compresslevel=6, mtime=0))
        row['compressed_journal_bytes'] = path.stat().st_size
        save(out, 'cases/' + name + '.json', row); rows.append(row)
        print(json.dumps({'case': name, 'events': persistence['events'], 'fulfilled': actual_runs,
            'deferrals': row['deferrals'], 'passed': row['passed']}), flush=True)
        del d, cp, continuation; gc.collect()
    pairs = []
    for n, prefix, seed in itertools.product(spec['populations'], spec['initial_inspection_prefixes'], spec['workload_seeds']):
        pair = [r for r in rows if (r['population'], r['prefix'], r['seed']) == (n, prefix, seed)]
        assert len(pair) == 2
        matched = semantic_signature(pair[0]) == semantic_signature(pair[1])
        debit_match = pair[0]['debits'] == pair[1]['debits']
        pairs.append({'population': n, 'prefix': prefix, 'seed': seed,
            'same_lifecycle_decisions_and_outcomes': matched, 'same_total_energy_debits': debit_match})
    save(out, 'resource-pairs.json', pairs)
    save(out, 'main-panel.json', rows)
    return rows, pairs


def evaluate_controls(out):
    rows = []
    for label, energy, time_budget in (('zero-energy', 0, 1000000),
            ('zero-time', 1000000, 0), ('finite-400', 400, 400)):
        d, row, _ = run_case(energy=energy, time_budget=time_budget, capture_prefix=False)
        assert row['blocked'] is not None, 'finite-budget control unexpectedly completed'
        oracle = check_world(d.w)
        cp, persistence = checkpoint_metrics(d.w)
        (out / 'journals' / (label + '.checkpoint.json.gz')).write_bytes(gzip.compress(cp.encode(), mtime=0))
        rows.append({'control': label, 'row': row, 'oracle': oracle, 'checkpoint': persistence,
            'expected_incomplete': True, 'passed': True})
    for n in (4, 16):
        w, actors, items = make_world(n); d = Driver(w)
        access = d.acquire(actors[0], items[0], 'no-history:access')
        ref = d.operation(actors[0], Formulate(access), 'no-history:formulate')
        assert w.organization_record(actors[0], ref).status == 'unresolved'
        rows.append({'control': 'no-history', 'population': n, 'status': 'unresolved',
            'oracle': check_world(w), 'passed': True})
        d, actors, items, _ = prepare_candidates(cohort=n - 1)
        d.emit(ConfigureAgent('refusal:configure', AgentPolicy(actors[1], response='silent'),
            'R11 matched voluntary-refusal control'))
        proposal = d.propose(actors[0], items[0], 'refusal:proposal')
        _, statuses = d.agree(actors[0], proposal, 'refusal:agreement', expect=False)
        assert set(statuses) == {'unagreed'}, statuses
        cp = d.w.checkpoint()
        (out / 'journals' / f'refusal-{n}.checkpoint.json.gz').write_bytes(gzip.compress(cp.encode(), mtime=0))
        rows.append({'control': 'refusal', 'population': n, 'statuses': statuses,
            'oracle': check_world(d.w), 'passed': True})
    save(out, 'controls.json', rows)
    return rows


def measure_selector(d, actor, access, spec):
    w = d.w; times = []; units = []; visits = []
    choices = w.practices(actor)
    for i in range(spec['warmups'] + spec['measurements']):
        cmd = OrganizationCommand(f'measure:{i}', f'measure:{i}', actor,
            Formulate(access), spec['command_work_limit'])
        balance = w._wallets[actor].energy; count = w.organization_candidate_visits
        start_active = w.processing_state(actor).active
        start = time.perf_counter_ns(); w.execute(cmd); elapsed = (time.perf_counter_ns() - start) / 1e6
        r = w.organization_record(actor, w.organization_job(actor, f'measure:{i}').result)
        assert r.status == 'proposed'
        expected = 2 + sum(1 + len(p.steps) + len(p.partners) for p in choices) + len(r.terms.members) + len(r.terms.steps)
        expected_route = route_oracle(w._profiles[actor].tim,start_active,'ne',False,expected,
            w.policy.typed_routing,w.policy.positional_prices)
        expected = sum(expected_route[4])+expected_route[5]
        cost = balance - w._wallets[actor].energy
        seen = w.organization_candidate_visits - count
        assert cost == expected and seen == len(choices), (cost, expected, seen, len(choices))
        if i >= spec['warmups']:
            times.append(elapsed); units.append(cost); visits.append(seen)
    return {'timing': stats(times), 'charges': sorted(set(units)), 'candidate_visits': sorted(set(visits)),
        'candidate_count': len(choices), 'selected_members': len(r.terms.members),
        'formula_expected_units': expected}


def evaluate_profiles(out, plan):
    spec = plan['profiles']; inactive = []; active = []
    for kind, count in itertools.product(spec['history_kinds'], spec['inactive_histories']):
        d, actors, items, access = prepare_candidates()
        before = snapshot(d.w); visits = d.w.organization_candidate_visits
        for i in range(count):
            if kind == 'tick':
                d.emit(Tick('history:' + str(i)))
            else:
                d.physical(actors[-1], INSPECT, (items[0],), 'history:' + str(i))
        after = snapshot(d.w)
        assert visits == d.w.organization_candidate_visits
        assert before['evaluator_visits'] == after['evaluator_visits']
        measurement = measure_selector(d, actors[0], access, spec)
        cp, persistence = checkpoint_metrics(d.w)
        row = {'kind': kind, 'inactive_events': count, **measurement,
            'checkpoint': persistence, 'before': before, 'after_history': after}
        inactive.append(row)
        del d, cp; gc.collect()
    for row in inactive:
        base = next(r for r in inactive if r['kind'] == row['kind'] and r['inactive_events'] == 0)
        row['passed'] = (row['charges'] == base['charges'] and row['candidate_visits'] == [1]
            and row['timing']['median_ms'] <= max(3 * base['timing']['median_ms'], 2)
            and row['timing']['p95_ms'] <= 10 and row['checkpoint']['timing_passed']
            and row['checkpoint']['bytes_passed'])
    for axis, values in (('repertoire', spec['active_repertoires']), ('cohort', spec['cohort_sizes'])):
        for value in values:
            d, actors, _, access = prepare_candidates(count=value if axis == 'repertoire' else 1,
                cohort=value if axis == 'cohort' else 3)
            measurement = measure_selector(d, actors[0], access, spec)
            row = {'axis': axis, 'extent': value, **measurement, 'diagnostics': snapshot(d.w)}
            row['passed'] = measurement['timing']['median_ms'] <= 5 + .25 * value
            row['oracle'] = check_world(d.w)
            active.append(row)
            del d; gc.collect()
    save(out, 'profiles.json', {'inactive': inactive, 'active': active})
    return inactive, active


def hash_panel(out, plan):
    code = ('from tools.r11_workloads import run_case; import hashlib; '
        'w=run_case(capture_prefix=False)[0].w; print(hashlib.sha256(w.checkpoint().encode()).hexdigest())')
    rows = []
    for seed in plan['replay']['hash_seeds']:
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=60, check=True)
        rows.append({'python_hash_seed': seed, 'sha256': result.stdout.strip()})
    assert len({r['sha256'] for r in rows}) == 1
    save(out, 'hash-seeds.json', rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--section', choices=('all', 'main', 'controls', 'profiles', 'hash', 'causal'), default='all')
    args = parser.parse_args(); out = args.output; out.mkdir(parents=True, exist_ok=True)
    (out / 'journals').mkdir(exist_ok=True)
    plan_path = ROOT / 'docs/acceptance_plan_R11.json'
    declaration = json.loads(plan_path.read_text())
    spec = declaration['panel']
    plan = {'main_panel': {'populations':spec['populations'],'initial_inspection_prefixes':spec['prefixes'],
        'resources':spec['resources'],'workload_seeds':spec['seeds'],'cycles':spec['cycles'],
        'initial_rounds':spec['initial_rounds'],'revised_rounds':spec['revised_rounds'],'successor_rounds':spec['successor_rounds']},
        'profiles': {'history_kinds':['tick','unrelated_paid_inspection'],'inactive_histories':[0,1000,10000],
            'warmups':3,'measurements':21,'command_work_limit':1000000,'active_repertoires':[],'cohort_sizes':[]},
        'replay':{'hash_seeds':[0,1,77]},'scope':'R11 local Model A routing; finite language/institutions and supplied lifecycle opportunities.'}

    source_hashes = {str(p.relative_to(ROOT)): digest(p.read_bytes())
        for folder in ('hle', 'tests', 'tools', 'docs') for p in sorted((ROOT / folder).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts}
    environment = {'python': sys.version, 'platform': platform.platform(),
        'cpu_count': os.cpu_count(), 'command': sys.argv, 'isolated': bool(sys.flags.isolated),
        'plan_sha256': digest(plan_path.read_bytes()), 'source_hashes': source_hashes}
    if Path('/proc/cpuinfo').exists():
        environment['cpu_model'] = next((line.split(':', 1)[1].strip() for line in
            Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), 'unknown')
    save(out, 'environment.json', environment)
    try:
        if args.section in ('all','causal'):
            save(out,'causal-controls.json',causal_panel())
        if args.section in ('all', 'main'):
            evaluate_main(out, plan)
        if args.section in ('all', 'controls'):
            evaluate_controls(out)
        if args.section in ('all', 'profiles'):
            evaluate_profiles(out, plan)
        if args.section in ('all', 'hash'):
            hash_panel(out, plan)
        if args.section == 'all':
            rows = json.loads((out / 'main-panel.json').read_text())
            pairs = json.loads((out / 'resource-pairs.json').read_text())
            controls = json.loads((out / 'controls.json').read_text())
            profiles = json.loads((out / 'profiles.json').read_text())
            causal=json.loads((out/'causal-controls.json').read_text())
            gates = {
                'M02': causal['passed'] and causal['cases']==512,
                'M05': len(rows)==24 and all(len(r['cycles'])==3 and not r['blocked'] for r in rows)
                    and all(p['same_lifecycle_decisions_and_outcomes'] for p in pairs)
                    and all(r['checkpoint']['exact'] and r['checkpoint']['continued_events']>0 for r in rows),
                'M06': all(r['oracle']['mismatches']==0 and r['oracle']['routing']['mismatches']==0
                    and r['oracle']['routing']['processing_owners']==0 and r['oracle_timing_passed'] and r['passed'] for r in rows)
                    and all(r['passed'] for r in profiles['inactive']) and all(r['passed'] for r in controls),
            }
            summary = {'milestone':'R11','gates':gates,'passed':all(gates.values()),
                'additional_gates':'M01/M03/M04 checked by full test suite; M07 on final extracted package',
                'cases':len(rows),'cycles':sum(len(r['cycles']) for r in rows),
                'events':sum(r['checkpoint']['events'] for r in rows),
                'organization_fulfillments':sum(r['fulfilled_organization_runs'] for r in rows),
                'semantic_transactions':sum(r['oracle']['routing']['counts']['semantic_transactions'] for r in rows),
                'activation_changes':sum(r['oracle']['routing']['counts']['activation_changes'] for r in rows),
                'controls':len(controls),'resource_pairs':len(pairs),'causal_cases':causal['cases'],'scope':plan['scope']}
            save(out, 'summary.json', summary)
            print(json.dumps(summary), flush=True)
            return 0 if summary['passed'] else 1
    except Exception:
        save(out, 'failure.json', {'section': args.section, 'traceback': traceback.format_exc()})
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
