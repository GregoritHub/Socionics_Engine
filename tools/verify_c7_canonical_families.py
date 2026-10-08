"""Reconstruct the rerun C4 raw families without importing their builder."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from hle_unified import codec
from hle_unified.crux_composition_audit import audit
from hle_unified.crossing_audit import payload
from hle_unified.material import attrs


def verify(base):
    folders = sorted(p for p in base.iterdir() if p.is_dir())
    assert len(folders) == 15
    rows, pairs = [], {}
    for folder in folders:
        control = folder.name.endswith('-control')
        row = json.loads((folder / 'result.json').read_text())
        assert row['control'] == control
        txs = codec.loads(gzip.decompress((folder / 'transactions.json.gz').read_bytes()).decode())
        access = gzip.decompress((folder / 'access.checkpoint.json.gz').read_bytes()).decode()
        cp = gzip.decompress((folder / 'engine.checkpoint.json.gz').read_bytes())
        assert hashlib.sha256(cp).hexdigest() == row['checkpoint_sha256']
        rejection = None
        try:
            report = audit(txs, access)
        except ValueError as exc:
            if not control:
                raise
            rejection = str(exc)
        else:
            assert not control, 'semantic ablation passed ordinary audit'
            assert report['passed'] and report['c4_independent_content_check']
        versions = {v.ref: v for tx in txs for v in tx.versions}
        decision = codec.decode(row['refs']['decision'])
        outcome = payload(versions[decision])['amount']
        jobs = [attrs(v) for tx in txs for v in tx.versions
                if v.ref.identity.namespace == 'u4.operation' and attrs(v).get('key') == 'case']
        assert jobs[-1]['spent'] == row['focus_spent'] and outcome == row['outcome']
        if row['failed_child']:
            assert folder.name == '08-cancelled-child' and outcome == 0
            parent = dict(codec.decode(row['parent']))
            assert parent['complete'] is False
        else:
            pairs.setdefault(row['name'], {})[control] = (jobs[-1]['spent'], outcome)
        rows.append({'folder': folder.name, 'control': control, 'expected_rejection': rejection,
                     'outcome': outcome, 'raw_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                       for p in folder.glob('*.json.gz')}})
    assert len(pairs) == 7
    for good_and_bad in pairs.values():
        good, bad = good_and_bad[False], good_and_bad[True]
        assert good[0] == bad[0] and good[1] != bad[1]
    result = {'passed': True, 'raw_worlds': 15, 'causal_pairs': 7,
              'participant_replay': False, 'rows': rows}
    (base / 'independent_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS canonical raw families and bounded parents', flush=True)


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
