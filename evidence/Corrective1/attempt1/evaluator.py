"""Prospectively declared real recurrent bypass arms; evaluator only."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from hle_unified import codec
from tests_workflow_longitudinal_shell.fixtures import prepared_typed, run, dev, ALICE
from tests_workflow_interruption.fixtures import Uninterrupted
from tools.evaluate_workflow_selection import manifest, save
from tools.verify_longitudinal_shell import read, forge_recurrent_status


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / 'source_freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    source = ROOT / 'evidence/FB5.6/attempt4/matrix/iee-04-same-target-recurrence.json.gz'
    raw, txs, _, _ = read(source)
    forged = forge_recurrent_status(txs, raw['access'])
    p = out / 'forged-status-transactions.json.gz'
    p.write_bytes(gzip.compress(codec.dumps((forged, raw['access'])).encode(), mtime=0))
    rows = {'forged': {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                      'source': str(source.relative_to(ROOT)),
                      'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}, 'pairs': []}
    for tim in ('iee', 'sli'):
        e, pattern, request = prepared_typed(tim)
        _, consequence = run(e, request, 'initial')
        assert consequence == 'unavailable'
        dev.release8(e, 'history-off-target-release', pattern, target=dev.SAW2)
        checkpoint = e.checkpoint()
        ordinary = type(e).restore(checkpoint)
        bypass = Uninterrupted.restore(checkpoint)
        assert ordinary.checkpoint() == bypass.checkpoint() == checkpoint
        _, blocked = run(ordinary, request, 'history-same-recurrence')
        _, answer = run(bypass, request, 'history-same-recurrence')
        assert blocked == 'unavailable' and answer == 'handover'
        d = bypass.job_status(ALICE, 'history-same-recurrence')
        assert d['status'] == 'succeeded' and d['spent'] == d['required'] > 0
        rows['pairs'].append({'type': tim, 'checkpoint': save(out, tim + '-checkpoint', e),
                             'ordinary': save(out, tim + '-ordinary', ordinary),
                             'bypass': save(out, tim + '-bypass', bypass)})
        (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert manifest() == freeze
    print('EXPORTED corrective longitudinal: one status forgery, two paid bypass pairs')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
