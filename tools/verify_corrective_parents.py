"""Raw parent reconstruction and real forgery controls; no fixtures/executors."""
import gzip
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from hle_unified import codec
from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs, attributes
from hle_unified.operations import indexed
from hle_unified.records import Account, Composition
from hle_unified.crossing_audit import encode, decode
from hle_unified.crux_composition_audit import audit as canonical_audit
from hle_unified.workflow_nesting_audit import audit_parent as workflow_audit

AUDITORS = {'canonical': canonical_audit, 'workflow': workflow_audit}
SCHEMAS = {'canonical': 'hle-full-crux-c4-engine-v1', 'workflow': 'hle-full-crux-c7-workflow-nesting-v1'}
CATEGORIES = ('normal', 'unsuccessful-child', 'membership-change', 'withdrawal')


def payload(v):
    account = v.facet(Account)
    return decode(account.content[0].object if account else attrs(v)['payload'])


def validate_keys(rows):
    keys = [(r['setting'], r['category']) for r in rows]
    if len(keys) != 8 or len(set(keys)) != 8 or set(keys) != {(s, c) for s in AUDITORS for c in CATEGORIES}:
        raise ValueError('eight distinct parent scenarios required')


def read(base, ref, setting):
    path = base / ref['file']
    assert path.resolve().parent == base.resolve()
    blob = path.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == ref['sha256']
    raw = unseal(gzip.decompress(blob).decode(), SCHEMAS[setting])
    txs = OperationStore.restore(raw['world']).journal()
    assert AUDITORS[setting](txs, raw['access'])['passed']
    return blob, raw, txs


def reject(txs, access, auditor):
    try:
        auditor(txs, access)
    except ValueError as exc:
        return str(exc)
    raise AssertionError('forged parent success accepted by ordinary auditor')


def forged_success(txs, parent):
    data = attrs(parent)
    blocked_summary = data['status'] == 'succeeded'
    target = data['binding'] if blocked_summary else parent.ref
    changed = 0
    forged = []
    for tx in txs:
        versions = []
        for v in tx.versions:
            if v.ref == target:
                if blocked_summary:
                    value = payload(v)
                    assert value['complete'] is False and value['status'] == 'blocked'
                    value.update(complete=True, status='complete')
                    account = v.facet(Account)
                    modified = replace(account, content=(replace(account.content[0], object=encode(value)),))
                    v = replace(v, facets=tuple(modified if f == account else f for f in v.facets))
                else:
                    d = dict(attrs(v))
                    assert d['status'] == 'failed' and d.get('binding') is None
                    d['status'] = 'succeeded'
                    v = replace(v, attributes=attributes(d))
                changed += 1
            versions.append(v)
        forged.append(replace(tx, versions=tuple(versions)))
    assert changed == 1
    assert sum(a != b for tx, other in zip(txs, forged) for a, b in zip(tx.versions, other.versions)) == 1
    return tuple(forged), ('blocked-summary-complete' if blocked_summary else 'failed-parent-status-success')


def payment(txs, ref, versions):
    """Sum only positive deltas for one identity; match each same-tx wallet debit."""
    amount = 0
    payments = []
    for tx in txs:
        for v in tx.versions:
            if v.ref.identity != ref.identity:
                continue
            d = attrs(v)
            before = 0 if v.previous is None else attrs(versions[v.previous])['spent']
            delta = d['spent'] - before
            assert delta >= 0
            if delta:
                wallets = [w for w in tx.versions if w.ref.identity.namespace == 'u4.wallet'
                           and attrs(w)['actor'] == d['actor']]
                assert len(wallets) == 1
                wallet = wallets[0]
                old, new = attrs(versions[wallet.previous]), attrs(wallet)
                assert old['energy'] - new['energy'] == old['time'] - new['time'] == delta
                amount += delta
                payments.append({'transaction': tx.key, 'paid': delta})
    assert amount == attrs(versions[ref])['spent']
    return amount, payments


def reconstruct(txs, row):
    versions = {v.ref: v for tx in txs for v in tx.versions}
    heads = {v.ref.identity: v for tx in txs for v in tx.versions}
    times = {v.ref: tx.at.tick for tx in txs for v in tx.versions}
    parents = [v for i, v in heads.items() if i.namespace == 'u4.operation'
               and attrs(v).get('key') == row['parent_key'] and attrs(v)['actor'].key == 'alice']
    assert len(parents) == 1
    parent = parents[0]; d = attrs(parent)
    assert d.get('c4') if row['setting'] == 'canonical' else d.get('c7n')
    children = decode(d['children_payload'])['children']
    assert len(children) == len({op.identity for op, _ in children})
    cited = {}
    child_rows = []
    start = min(times[v.ref] for v in versions.values() if v.ref.identity == parent.ref.identity)
    for op, output in children:
        child = attrs(versions[op])
        assert heads[op.identity].ref == op and child['actor'] == d['actor'] and child['context'] == d['context']
        assert times[op] < start and times[output] < start
        assert child.get('content_target', child.get('target')).identity == d['content_target'].identity
        assert op in indexed(d, 'dependency.')
        paid, receipts = payment(txs, op, versions)
        cited[op] = paid
        if output.identity.namespace == 'u4.observation':
            assert attrs(versions[output])['event'] == child['result']
        else:
            assert output in (child.get('binding'), *indexed(child, 'public.'))
            value = payload(versions[output])
            for nested_ref, spent in value.get('operations', ()):
                assert nested_ref not in cited or cited[nested_ref] == spent
                actual, _ = payment(txs, nested_ref, versions)
                assert actual == spent
                cited[nested_ref] = spent
        child_rows.append({'operation': codec.encode(op), 'output': codec.encode(output),
                           'status': child['status'], 'spent': paid, 'wallet_payments': receipts,
                           'output_sha256': hashlib.sha256(codec.dumps(versions[output]).encode()).hexdigest()})
    own, receipts = payment(txs, parent.ref, versions)
    assert own > 0 and parent.ref.identity not in {op.identity for op in cited}
    stale = [ref for ref in indexed(d, 'dependency.') if heads[ref.identity].ref != ref]
    category = row['category']; summary = None; change = None
    if category in ('normal', 'unsuccessful-child'):
        assert d['status'] == 'succeeded' and d['spent'] == d['required'] and d['binding'] is not None
        summary = payload(versions[d['binding']])
        assert summary['competence'] is False
        assert summary.get('authority') is None and not summary.get('executable', False)
        assert summary['children'] == children
        listed = summary['operations']
        assert len(listed) == len({op.identity for op, _ in listed})
        assert dict(listed) == cited and summary['cited_spending'] == sum(cited.values())
        assert summary['complete'] == (category == 'normal')
        assert summary['status'] == ('complete' if category == 'normal' else 'blocked')
        if category == 'normal':
            assert all(x['status'] == 'succeeded' for x in child_rows)
        else:
            expected = 'cancelled' if row['setting'] == 'canonical' else 'failed'
            assert sum(x['status'] == expected for x in child_rows) == 1
            assert row['native_scenario'] == ('cancelled-child' if expected == 'cancelled' else 'failed-child')
    else:
        assert d['status'] == 'failed' and d['failure'] == 'stale_dependency' and d.get('binding') is None
        assert stale
        if category == 'membership-change':
            old = versions[d['group']]; new = heads[d['group'].identity]
            old_members, new_members = old.facet(Composition).members, new.facet(Composition).members
            removed = set(old_members) - set(new_members)
            assert len(removed) == 1 and next(iter(removed)).key == 'bob'
            assert d['group'] in stale and start < times[new.ref] < times[parent.ref]
            change = {'old': codec.encode(old.ref), 'new': codec.encode(new.ref), 'removed': ['bob']}
        else:
            key = 'case-renew-b' if row['setting'] == 'canonical' else 'parent-social-exchange-peer'
            candidates = [ref for ref in stale if ref.identity.key == key]
            assert len(candidates) == 1
            old = versions[candidates[0]]; new = heads[old.ref.identity]
            assert payload(old)['consent'] is True and payload(new)['consent'] is False
            assert start < times[new.ref] < times[parent.ref]
            retention_key = 'retain-withdrawal' if row['setting'] == 'canonical' else 'parent-retain-withdrawal'
            retain = [v for i, v in heads.items() if i.namespace == 'u4.operation' and attrs(v).get('key') == retention_key]
            assert len(retain) == 1
            rd = attrs(retain[0]); assert rd['actor'].key == 'bob' and rd['status'] == 'succeeded' and rd['spent'] > 0
            assert new.ref in rd.values()
            change = {'old': codec.encode(old.ref), 'new': codec.encode(new.ref), 'consent': False,
                      'paid_retention': codec.encode(retain[0].ref), 'retention_spent': rd['spent']}
    result = {'setting': row['setting'], 'category': category, 'native_scenario': row['native_scenario'],
              'parent': codec.encode(parent.ref), 'parent_status': d['status'], 'parent_failure': d.get('failure'),
              'parent_binding': codec.encode(d.get('binding')), 'parent_review_spent': own,
              'parent_wallet_payments': receipts, 'children': child_rows, 'unique_child_operations': len(cited),
              'cited_child_spending': sum(cited.values()), 'combined_review_and_cited_spending': own + sum(cited.values()),
              'complete': None if summary is None else summary['complete'], 'change': change,
              'stale_dependencies': [codec.encode(ref) for ref in stale], 'exact_restore': True}
    return parent, result


def verify(base):
    rows = json.loads((base / 'rows.json').read_text())
    validate_keys(rows); results = []; rejections = []
    for row in rows:
        blob, raw, txs = read(base, row['world'], row['setting'])
        restored, _, _ = read(base, row['restored'], row['setting'])
        assert blob == restored
        parent, result = reconstruct(txs, row)
        if row['category'] != 'normal':
            forged, mode = forged_success(txs, parent)
            reason = reject(forged, raw['access'], AUDITORS[row['setting']])
            p = base / (row['setting'] + '-' + row['native_scenario'] + '-forged.json.gz')
            p.write_bytes(gzip.compress(codec.dumps((forged, raw['access'])).encode(), mtime=0))
            saved_txs, saved_access = codec.loads(gzip.decompress(p.read_bytes()).decode())
            assert saved_txs == forged and saved_access == raw['access']
            assert reject(saved_txs, saved_access, AUDITORS[row['setting']]) == reason
            try:
                reject(saved_txs, saved_access, lambda t, a: {'passed': True})
            except AssertionError:
                pass
            else:
                raise AssertionError('accepting-auditor regression failed')
            rejections.append({'setting': row['setting'], 'native_scenario': row['native_scenario'], 'mode': mode,
                               'reason': reason, 'raw': {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}})
        results.append(result)
        print('RECONSTRUCTED', row['setting'], row['native_scenario'], flush=True)
    assert len(results) == 8 and len(rejections) == 6
    result = {'passed': True, 'new_parent_scenarios': 8, 'raw_restore_checks': 8,
              'forged_parent_controls': rejections, 'parents': results,
              'historical_recovery_claimed': False, 'participant_replay': False}
    (base / 'independent_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS eight fresh parent scenarios and six real forged-success rejections', flush=True)
    return result


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
