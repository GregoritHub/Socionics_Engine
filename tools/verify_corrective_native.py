"""Independent native-boundary reconstruction; no executors or fixtures."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from hle_unified import codec
from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs
from hle_unified.operation_audit import indexed
from hle_unified.self_audit import audit as audit_c2
from hle_unified.crossing_audit import audit as audit_c3
from hle_unified.workflow_audit import audit as audit_workflow
from hle_unified.self_records import SELF_NAMES
from hle_unified.crossing_records import PATHS as CROSSINGS
from hle_unified.workflow_records import PATHS as WORKFLOWS

SCHEMAS = {'c2': 'hle-full-crux-c2-engine-v1', 'c3': 'hle-full-crux-c3-engine-v1',
           'workflow': 'hle-full-crux-c7-workflow-v1'}
AUDITORS = {'c2': audit_c2, 'c3': audit_c3, 'workflow': audit_workflow}


def expected_keys():
    return {(s, name, face, b) for s, names in
            (('canonical', tuple(SELF_NAMES) + tuple(CROSSINGS)), ('workflow', tuple(WORKFLOWS)))
            for name in names for face in ('accumulation', 'expenditure') for b in range(3)}


def validate_keys(rows):
    keys = [(r['setting'], r['route'], r['polarity'], r['boundary']) for r in rows]
    if len(keys) != 192 or len(set(keys)) != 192 or set(keys) != expected_keys():
        raise ValueError('native comparison keys differ from required 192')


def read(base, ref, family):
    p = base / ref['file']
    if p.resolve().parent != base.resolve():
        raise ValueError('nonlocal raw reference')
    blob = p.read_bytes()
    if hashlib.sha256(blob).hexdigest() != ref['sha256']:
        raise ValueError('raw digest differs')
    raw = unseal(gzip.decompress(blob).decode(), SCHEMAS[family])
    txs = OperationStore.restore(raw['world']).journal()
    result = AUDITORS[family](txs, raw['access'])
    assert result['passed']
    heads = {v.ref.identity: v for tx in txs for v in tx.versions}
    versions = {v.ref: v for tx in txs for v in tx.versions}
    return blob, txs, heads, versions


def focus(world):
    jobs = [v for i, v in world[2].items() if i.namespace == 'u4.operation'
            and attrs(v).get('key') == 'case' and attrs(v).get('actor').key == 'alice']
    assert len(jobs) == 1
    return jobs[0], attrs(jobs[0])


def compare_worlds(boundary, restored_boundary, original, restored, row):
    assert boundary[0] == restored_boundary[0]
    assert original[0] == restored[0]
    bv, b = focus(boundary)
    ov, o = focus(original)
    rv, r = focus(restored)
    assert bv.ref.identity == ov.ref.identity == rv.ref.identity
    assert original[1][:len(boundary[1])] == boundary[1]
    assert restored[1][:len(restored_boundary[1])] == restored_boundary[1]
    assert b['movement'] == o['movement'] == r['movement'] == row['route']
    assert b['polarity'] == o['polarity'] == r['polarity'] == row['polarity']
    first = b['recall_units'] + sum(indexed(b, 'route.0.charges.')) + b['route.0.content_units']
    units = (1, first, b['required'])[row['boundary']]
    assert b['spent'] == b['completed'] == units
    assert b['status'] in ('partial', 'ready')
    if row['boundary'] >= 1:
        assert b['steps_completed'] >= 1 and b['last_step'] in boundary[3]
    if row['boundary'] == 2:
        assert b['status'] == 'ready'
    assert o == r and o['status'] == 'succeeded'
    assert o['spent'] == o['completed'] == o['required'] >= units
    assert o['steps_completed'] == o['route_count']
    outputs = [v for k, v in o.items() if k in ('binding', 'result') or k.startswith('public.')]
    outputs = list(dict.fromkeys(v for v in outputs if v is not None))
    assert outputs and all(v in original[3] for v in outputs)
    return {'key': row['key'], 'operation': codec.encode(ov.ref), 'boundary_spent': units,
            'terminal_spent': o['spent'], 'remaining_paid_units': o['spent'] - units,
            'first_boundary_equals_ready': first == b['required'],
            'paid_steps': o['steps_completed'],
            'semantic_outputs': [{'ref': codec.encode(v), 'sha256': hashlib.sha256(
                codec.dumps(original[3][v]).encode()).hexdigest()} for v in outputs],
            'ordinary_raw_audits': 4, 'exact_restore': True, 'exact_terminal': True}


def verify(base):
    rows = json.loads((base / 'rows.json').read_text())
    assert rows['evidence_status'] == 'newly_evaluated_not_historical_recovery'
    validate_keys(rows['comparisons'])
    reports = []
    for row in rows['comparisons']:
        family = 'workflow' if row['setting'] == 'workflow' else ('c2' if row['route'] in SELF_NAMES else 'c3')
        assert family == row['family']
        assert row['inherited_boundary_index'] == ((0, 1, 3)[row['boundary']] if family == 'c2' else row['boundary'])
        assert row['key'] == '-'.join((row['setting'], row['route'], row['polarity'], str(row['boundary'])))
        worlds = [read(base, row[k], family) for k in
                  ('boundary_world', 'restored_boundary', 'original_terminal', 'restored_terminal')]
        reports.append(compare_worlds(*worlds, row))
        if len(reports) % 24 == 0:
            print('RECONSTRUCTED', len(reports), flush=True)
    wanted = {(s, k) for s in ('canonical', 'workflow') for k in ('cancelled', 'exhausted', 'stale_dependency')}
    actual = [(r['setting'], r['kind']) for r in rows['negatives']]
    assert len(actual) == len(set(actual)) == 6 and set(actual) == wanted
    negatives = []
    for row in rows['negatives']:
        prefix = read(base, row['prefix'], row['family'])
        world = read(base, row['world'], row['family'])
        assert world[1][:len(prefix[1])] == prefix[1]
        _, d = focus(world)
        assert d['spent'] > 0 and d['status'] != 'succeeded' and d.get('binding') is None
        if row['kind'] == 'cancelled':
            assert d['status'] == 'cancelled'
        elif row['kind'] == 'stale_dependency':
            assert d['status'] == 'failed' and d['failure'] == 'stale_dependency'
        else:
            wallets = [attrs(v) for i, v in world[2].items() if i.namespace == 'u4.wallet'
                       and attrs(v)['actor'].key == 'alice']
            assert len(wallets) == 1 and wallets[0]['energy'] == wallets[0]['time'] == 0
            assert d['spent'] < d['required'] and row['commit_error']
        negatives.append({'setting': row['setting'], 'kind': row['kind'], 'status': d['status'],
                          'spent': d['spent'], 'failure': d.get('failure'), 'ordinary_raw_audits': 2})
    result = {'passed': True, 'comparisons': len(reports), 'negative_worlds': negatives,
              'ordinary_raw_audits': 4 * len(reports) + 12,
              'historical_recovery_claimed': False, 'participant_replay': False,
              'comparison_evidence': reports}
    (base / 'independent_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS independently reconstructed 192 new native comparisons and six negative worlds', flush=True)
    return result


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
