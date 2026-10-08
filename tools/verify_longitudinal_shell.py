"""Independent FB5.6 raw verifier; no executor, selector, scheduler or fixtures."""
import gzip
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs, attributes
from hle_unified.workflow_longitudinal_shell_audit import audit, compare_correction_control


SCHEMA = 'hle-full-crux-c7-workflow-interruption-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    raw = unseal(gzip.decompress(path.read_bytes()).decode(), SCHEMA)
    store = OperationStore.restore(raw['world'])
    txs = store.journal()
    return raw, txs, {v.ref: v for tx in txs for v in tx.versions}, store


def checked(path, expected):
    if sha(path) != expected:
        raise ValueError('evidence digest differs: ' + str(path))
    return path


def resolved(name):
    path = Path(name)
    return path if path.is_absolute() else ROOT / path


def verify_ledger(path, base):
    ledger = json.loads(path.read_text())
    if ledger['complete_batches'] != ['5.3', '5.4', '5.5', '5.6'] or ledger['next_batch'] != '6.1':
        raise ValueError('integrated ledger sequence differs')
    for row in ledger['rows']:
        for name in ('acceptance', 'raw_index'):
            ref = row[name]
            checked(resolved(ref['path']), ref['sha256'])
        if not row['accepted']:
            raise ValueError('integrated ledger includes unaccepted row')
        if row['batch'] == '5.6':
            if len(row['raw_worlds']) != 29:
                raise ValueError('FB5.6 raw denominator differs')
            for ref in row['raw_worlds']:
                checked(base / ref['file'], ref['sha256'])
    return ledger


def reports(base, rows):
    result = {}
    for row in rows:
        if row['kind'] == 'longitudinal':
            result[row['type']] = {}
            for stage, ref in row['worlds'].items():
                raw, txs, versions, store = read(checked(base / ref['file'], ref['sha256']))
                result[row['type']][stage] = (audit(txs, raw['access']), raw, txs, versions, store)
    return result


def require_rejection(transactions, access_text, auditor=None):
    """Count only rejection returned by an actual ordinary-auditor call."""
    auditor = audit if auditor is None else auditor
    try:
        auditor(transactions, access_text)
    except ValueError as exc:
        return str(exc)
    raise AssertionError('forged recurrent completion accepted by auditor')


def forge_recurrent_status(txs, access_text):
    """Copy one exact latest cancelled child; retain all paid work and access."""
    txs = tuple(txs)
    report = audit(txs, access_text)
    assert not report['longitudinal_consumers']
    heads = {v.ref.identity: v for tx in txs for v in tx.versions}
    candidates = [v for v in heads.values() if v.ref.identity.namespace == 'u4.operation'
                  and attrs(v).get('c7w') and attrs(v).get('key') == 'history-same-recurrence']
    assert len(candidates) == 1
    target = candidates[0]
    d = attrs(target)
    assert d['status'] == 'cancelled' and d['steps_completed'] == 1
    assert d['spent'] > 0 and d['last_step'] in report['longitudinal_retained_intermediates']
    assert d.get('binding') is None
    forged = []
    mutations = 0
    for tx in txs:
        versions = []
        for v in tx.versions:
            if v.ref == target.ref:
                changed = dict(attrs(v)); changed['status'] = 'succeeded'
                v = replace(v, attributes=attributes(changed))
                mutations += 1
            versions.append(v)
        forged.append(replace(tx, versions=tuple(versions)))
    assert mutations == 1
    differences = [(a, b) for tx, ft in zip(txs, forged)
                   for a, b in zip(tx.versions, ft.versions) if a != b]
    assert len(differences) == 1
    before, after = map(attrs, differences[0])
    assert {k for k in before if before[k] != after[k]} == {'status'}
    return tuple(forged)


def verify(base, ledger_path):
    summary = json.loads((base / 'summary.json').read_text())
    rows = json.loads((base / 'rows.json').read_text())
    assert summary == {'passed': True, 'raw_worlds': 29, 'types': ['iee', 'sli'],
        'longitudinal_histories': 2, 'unsupported_clearances': 3,
        'exhaustion_worlds': 1, 'cancelled_work_worlds': 1,
        'exact_restore_pairs': 2, 'source_unchanged': True}
    ledger = verify_ledger(ledger_path, base)
    histories = reports(base, rows)
    tamper_rejections = 0

    for tim in ('iee', 'sli'):
        rs = histories[tim]
        assert set(rs) == {'01-initial-interruption', '02-exact-correction-witness',
            '03-off-target-correction', '04-same-target-recurrence',
            '05-changed-target-recurrence', '06-exact-correction-and-use',
            '07-changed-target-residual', '08-restored-final'}
        initial = rs['01-initial-interruption'][0]
        witness = rs['02-exact-correction-witness'][0]
        control = rs['04-same-target-recurrence'][0]
        final = rs['07-changed-target-residual'][0]
        target = witness['workflow_development_rows'][-1]['target']
        comparison = compare_correction_control(witness, control, target)
        assert comparison['terminal'] == 'handover'
        assert initial['longitudinal_retained_intermediates']
        assert final['longitudinal_recurrence_same'] >= 1
        assert final['longitudinal_recurrence_changed'] >= 1
        assert len(final['longitudinal_originals']) == 1
        a = base / next(r['worlds']['07-changed-target-residual']['file'] for r in rows
                        if r['kind'] == 'longitudinal' and r['type'] == tim)
        b = base / next(r['worlds']['08-restored-final']['file'] for r in rows
                        if r['kind'] == 'longitudinal' and r['type'] == tim)
        assert a.read_bytes() == b.read_bytes()
        unequal = base / next(r['worlds']['01-initial-interruption']['file'] for r in rows
                              if r['kind'] == 'longitudinal' and r['type'] == tim)
        if tim == 'iee':
            try:
                if unequal.read_bytes() != b.read_bytes():
                    raise ValueError('forged restore equality')
            except ValueError:
                tamper_rejections += 1

    for row in (r for r in rows if r['kind'] == 'undeformed'):
        raw, txs, _, _ = read(base / row['world']['file'])
        report = audit(txs, raw['access'])
        assert report['workflow_interruption_deformed'] == 0
        assert report['longitudinal_consumers'][-1]['next_task'] == 'handover'

    for row in (r for r in rows if r['kind'] == 'unsupported'):
        before = base / row['worlds']['before']['file']
        after = base / row['worlds']['after']['file']
        assert before.read_bytes() == after.read_bytes()
        raw, txs, _, _ = read(base / row['worlds']['still-interrupted']['file'])
        report = audit(txs, raw['access'])
        assert report['workflow_interruption_deformed'] == 1
        assert not report['longitudinal_corrections']
        assert row['error'] == 'unsupported, incomplete or scaffolded local correction'

    exhaustion_row = next(r for r in rows if r['kind'] == 'exhaustion')
    raw, txs, versions, store = read(base / exhaustion_row['world']['file'])
    report = audit(txs, raw['access'])
    heads = {v.ref.identity: v for v in versions.values()}
    wallet = next(attrs(v) for i, v in heads.items() if i.namespace == 'u4.wallet' and attrs(v).get('actor').key == 'alice')
    jobs = [attrs(v) for i, v in heads.items() if i.namespace == 'u4.operation'
            and attrs(v).get('u8') and attrs(v).get('purpose') == 'release']
    assert wallet['energy'] == wallet['time'] == 0
    assert len(jobs) == 1 and jobs[0]['status'] == 'partial'
    assert jobs[0]['completed'] == jobs[0]['required'] - 1 and jobs[0]['spent'] > 0
    assert report['longitudinal_retained_intermediates'] and not report['longitudinal_corrections']

    cancelled_row = next(r for r in rows if r['kind'] == 'cancelled_work')
    raw, txs, versions, store = read(base / cancelled_row['world']['file'])
    report = audit(txs, raw['access'])
    heads = {v.ref.identity: v for v in versions.values()}
    jobs = [attrs(v) for i, v in heads.items() if i.namespace == 'u4.operation'
            and attrs(v).get('u8') and attrs(v).get('purpose') == 'release']
    assert len(jobs) == 1 and jobs[0]['status'] == 'cancelled' and jobs[0]['spent'] == 1
    assert report['longitudinal_retained_intermediates'] and not report['longitudinal_corrections']

    # Raw tamper controls: inherited audit rejects missing intermediate and changed origin.
    report, raw, txs, versions, _ = histories['iee']['07-changed-target-residual']
    for mode in ('intermediate', 'origin'):
        forged = []
        changed = False
        for tx in txs:
            out = []
            for v in tx.versions:
                d = attrs(v)
                if not changed and mode == 'intermediate' and v.ref.identity.namespace == 'c7shi.interruption':
                    d['intermediate'] = d['replacement']; v = replace(v, attributes=attributes(d)); changed = True
                if not changed and mode == 'origin' and v.ref.identity.namespace == 'u7.pattern':
                    d['origin'] = d['cue']; v = replace(v, attributes=attributes(d)); changed = True
                out.append(v)
            forged.append(replace(tx, versions=tuple(out)))
        assert changed
        try:
            audit(forged, raw['access'])
        except ValueError:
            tamper_rejections += 1
        else:
            raise AssertionError(mode + ' tamper passed')

    # Summary/correction and ledger digest controls are rejected independently.
    try:
        compare_correction_control(histories['iee']['02-exact-correction-witness'][0],
                                   histories['iee']['02-exact-correction-witness'][0],
                                   histories['iee']['02-exact-correction-witness'][0]['workflow_development_rows'][-1]['target'])
    except ValueError:
        tamper_rejections += 1
    else:
        raise AssertionError('correction control tamper passed')
    try:
        bad = json.loads(ledger_path.read_text())
        bad['rows'][0]['acceptance']['sha256'] = '0' * 64
        checked(resolved(bad['rows'][0]['acceptance']['path']), bad['rows'][0]['acceptance']['sha256'])
    except ValueError:
        tamper_rejections += 1
    else:
        raise AssertionError('ledger digest tamper passed')
    _, recurrent_raw, recurrent_txs, _, _ = histories['iee']['04-same-target-recurrence']
    forged = forge_recurrent_status(recurrent_txs, recurrent_raw['access'])
    forged_rejection = require_rejection(forged, recurrent_raw['access'])
    tamper_rejections += 1

    assert tamper_rejections == 6, tamper_rejections
    result = {'passed': True, 'raw_worlds': 29, 'longitudinal_histories': 2,
              'same_target_recurrence': 2, 'changed_target_recurrence': 2,
              'exact_restore_pairs': 2, 'unsupported_clearances': 3,
              'exhaustion': True, 'cancelled_paid_work': True,
              'tamper_rejections': tamper_rejections, 'integrated_rows': len(ledger['rows']),
              'participant_replay': False, 'forged_status_rejection': forged_rejection,
              'forgery_claim': 'Cancelled paid child falsely marked succeeded; no genuine binding or consumer'}
    (base / 'independent_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS independent longitudinal Shell', json.dumps(result), flush=True)
    return result


def verify_corrective(base):
    from hle_unified import codec
    rows = json.loads((base / 'rows.json').read_text())
    ref = rows['forged']
    raw, txs, _, _ = read(checked(ROOT / ref['source'], ref['source_sha256']))
    forged, access = codec.loads(gzip.decompress(checked(base / ref['file'], ref['sha256']).read_bytes()).decode())
    assert access == raw['access']
    assert forged == forge_recurrent_status(txs, access)
    rejections = {'status_forgery': require_rejection(forged, access)}
    assert {r['type'] for r in rows['pairs']} == {'iee', 'sli'} and len(rows['pairs']) == 2
    for row in rows['pairs']:
        worlds = {k: read(checked(base / row[k]['file'], row[k]['sha256']))
                  for k in ('checkpoint', 'ordinary', 'bypass')}
        prefix = worlds['checkpoint'][1]
        for arm in ('ordinary', 'bypass'):
            assert worlds[arm][1][:len(prefix)] == prefix
        report = audit(worlds['ordinary'][1], worlds['ordinary'][0]['access'])
        assert report['longitudinal_recurrence_same'] > 0 and not report['longitudinal_consumers']
        _, bypass_txs, versions, _ = worlds['bypass']
        heads = {v.ref.identity: v for tx in bypass_txs for v in tx.versions}
        jobs = [attrs(v) for v in heads.values() if v.ref.identity.namespace == 'u4.operation']
        native = [d for d in jobs if d.get('c7w') and d.get('key') == 'history-same-recurrence']
        consumers = [d for d in jobs if d.get('c7w') and d.get('key') == 'history-same-recurrence-consumer']
        assert len(native) == len(consumers) == 1
        for d in native + consumers:
            assert d['status'] == 'succeeded' and d['spent'] == d['required'] > 0
            assert d.get('binding') is not None
        from hle_unified.workflow_audit import payload
        assert payload(versions[consumers[0]['binding']])['next_task'] == 'handover'
        assert native[0]['binding'] in [value for key, value in consumers[0].items() if key.startswith('input.')]
        reason = require_rejection(bypass_txs, worlds['bypass'][0]['access'])
        assert 'escaped first boundary' in reason
        rejections[row['type'] + '_paid_bypass'] = reason
        try:
            require_rejection(bypass_txs, worlds['bypass'][0]['access'], lambda t, a: {'passed': True})
        except AssertionError:
            pass
        else:
            raise AssertionError('accepting-auditor bypass regression failed')
    result = {'passed': True, 'actual_audit_rejections': rejections,
              'status_mutations': 1, 'paid_bypass_pairs': 2, 'participant_replay': False,
              'claim': 'Forged cancelled-success status and real fully paid recurrent interruption bypass are separately rejected'}
    (base / 'independent_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    if sys.argv[1] == '--corrective':
        verify_corrective(Path(sys.argv[2]))
    else:
        verify(Path(sys.argv[1]), Path(sys.argv[2]))
