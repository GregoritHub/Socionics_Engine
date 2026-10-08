"""New prospective native-boundary worlds, never historical replacements."""
import gzip
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from tests_c2 import fixtures as c2
from tests_c2.test_self_routes import make, NAMES
from tests_c3 import fixtures as c3
from tests_c7_workflow import fixtures as wf
from tools.evaluate_workflow_selection import manifest


def save(out, key, engine):
    p = out / (key + '.json.gz')
    p.write_bytes(gzip.compress(engine.checkpoint().encode(), mtime=0))
    return {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def write(out, rows):
    (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / 'source_freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    rows = {'evidence_status': 'newly_evaluated_not_historical_recovery', 'comparisons': [], 'negatives': []}
    panels = [('canonical', 'c2', NAMES, make, c2.cell),
              ('canonical', 'c3', c3.PATHS, lambda n, f: c3.setup_c3(), c3.cell),
              ('workflow', 'workflow', wf.PATHS, lambda n, f: wf.setup_workflow(), wf.cell)]
    try:
        for setting, family, names, factory, cell in panels:
            for name in names:
                for face in ('accumulation', 'expenditure'):
                    for boundary in range(3):
                        key = '-'.join((setting, name, face, str(boundary)))
                        e = factory(name, face)
                        r = cell(e, name, face, prepare_only=True)['request']
                        e.start('start-case' if family == 'c2' else 'begin', r)
                        d = e.job_status(c2.ALICE, r.key)
                        first = d['recall_units'] + sum(c2.indexed(d, 'route.0.charges.')) + d['route.0.content_units']
                        e.advance('partial', c2.ALICE, r.key, (1, first, d['required'])[boundary])
                        original = e.checkpoint()
                        q = type(e).restore(original)
                        assert q.checkpoint() == original
                        row = {'key': key, 'setting': setting, 'family': family, 'route': name,
                               'polarity': face, 'boundary': boundary,
                               'inherited_boundary_index': (0, 1, 3)[boundary] if family == 'c2' else boundary,
                               'boundary_world': save(out, key + '-boundary', e),
                               'restored_boundary': save(out, key + '-restored-boundary', q)}
                        for branch in (e, q):
                            if branch.job_status(c2.ALICE, r.key)['status'] != 'ready':
                                branch.advance('finish-work' if family == 'c2' else 'resume', c2.ALICE, r.key, 100000)
                            branch.commit('finish', c2.ALICE, r.key)
                        assert e.checkpoint() == q.checkpoint()
                        row.update(original_terminal=save(out, key + '-original-terminal', e),
                                   restored_terminal=save(out, key + '-restored-terminal', q))
                        rows['comparisons'].append(row)
                        write(out, rows)
            print('EXPORTED', setting, family, len(rows['comparisons']), flush=True)
        for setting in ('canonical', 'workflow'):
            setup, cell = (c2.setup_c2, c2.cell) if setting == 'canonical' else (wf.setup_workflow, wf.cell)
            route = 'Contemplate' if setting == 'canonical' else 'Theorize'
            for kind in ('cancelled', 'exhausted', 'stale_dependency'):
                budget = 200000
                if kind == 'exhausted':
                    probe = setup(); cell(probe, route, 'accumulation', prepare_only=True)
                    wallet = probe.wallet(c2.ALICE)
                    budget = wallet['initial_energy'] - wallet['energy'] + 1
                e = setup(budget=budget)
                negative_route = 'Express' if setting == 'workflow' and kind == 'stale_dependency' else route
                face = 'expenditure' if negative_route == 'Express' else 'accumulation'
                r = cell(e, negative_route, face, prepare_only=True)['request']
                prefix = save(out, setting + '-' + kind + '-prefix', e)
                if setting == 'workflow' and kind == 'stale_dependency':
                    wf.observe(e, 'earlier-maintenance', primitive='care')
                e.start('begin', r)
                e.advance('paid', c2.ALICE, r.key, 1 if kind == 'cancelled' else 100000)
                error = None
                if kind == 'cancelled':
                    e.cancel('cancel', c2.ALICE, r.key)
                elif kind == 'exhausted':
                    try:
                        e.commit('free', c2.ALICE, r.key)
                    except ValueError as exc:
                        error = str(exc)
                    else:
                        raise AssertionError('exhausted commit accepted')
                else:
                    if setting == 'canonical':
                        e.declare('changed-claim', (c2.next_version(e.world.resolve(r.input), label='Revised prior'),))
                    e.commit('finish', c2.ALICE, r.key)
                d = e.job_status(c2.ALICE, r.key)
                assert d['spent'] > 0 and d['status'] != 'succeeded' and d.get('binding') is None
                if kind == 'stale_dependency':
                    assert d['failure'] == 'stale_dependency'
                rows['negatives'].append({'setting': setting, 'family': 'c2' if setting == 'canonical' else 'workflow',
                                         'kind': kind, 'prefix': prefix, 'commit_error': error,
                                         'world': save(out, setting + '-' + kind, e)})
                write(out, rows)
        assert len(rows['comparisons']) == 192 and len(rows['negatives']) == 6
        assert manifest() == freeze
        print('EXPORTED 192 new native comparisons and six negative worlds', flush=True)
    except Exception:
        (out / 'failure.txt').write_text(traceback.format_exc())
        if 'e' in locals():
            save(out, 'failed-current-world', e)
        raise


if __name__ == '__main__':
    main(Path(sys.argv[1]))
