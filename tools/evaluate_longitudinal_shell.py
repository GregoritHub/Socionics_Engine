"""Build the prospectively fixed FB5.6 longitudinal Shell panel."""
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]

from tests_workflow_longitudinal_shell.fixtures import (
    longitudinal, undeformed, unsupported_longitudinal, exhaustion, failed_work)
from tools.evaluate_workflow_selection import manifest, save


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(path):
    try:
        name = str(path.relative_to(ROOT))
    except ValueError:
        name = str(path.resolve())
    return {'path': name, 'sha256': digest(path)}


def build_ledger(out, ledger, summary, raw):
    rows = []
    for batch in ('5.3', '5.4', '5.5'):
        acceptance = ROOT / 'evidence' / ('FB' + batch) / 'Acceptance.json'
        index = ROOT / 'evidence' / ('FB' + batch) / 'Raw_Evidence_Index.json'
        data = json.loads(acceptance.read_text())
        assert data['passed'] and data['source_unchanged']
        rows.append({'batch': batch, 'accepted': True, 'acceptance': reference(acceptance),
                     'raw_index': reference(index), 'gates': data})
    rows.append({'batch': '5.6', 'accepted': summary['passed'],
                 'acceptance': reference(out / 'summary.json'),
                 'raw_index': reference(out / 'rows.json'),
                 'gates': {k: summary[k] for k in ('raw_worlds', 'types', 'longitudinal_histories',
                     'unsupported_clearances', 'exhaustion_worlds', 'cancelled_work_worlds',
                     'exact_restore_pairs', 'source_unchanged')},
                 'raw_worlds': raw})
    value = {'schema': 'srl-c7-sustained-extension-ledger-v1', 'rows': rows,
             'complete_batches': ['5.3', '5.4', '5.5', '5.6'],
             'goal_complete': False, 'next_batch': '6.1',
             'limits': 'Bounded engineered continuation and Shell evidence; no Phase 7 or people claim.'}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(value, indent=2) + '\n')
    return value


def main(out, ledger):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / 'source_freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    rows, raw = [], []
    try:
        for tim in ('iee', 'sli'):
            worlds = {}
            _, detail = longitudinal(tim, worlds)
            saved = {}
            for stage, engine in worlds.items():
                ref = save(out, tim + '-' + stage, engine)
                saved[stage] = ref
                raw.append({'kind': 'longitudinal', 'type': tim, 'stage': stage, **ref})
            comparison = detail['comparison']
            rows.append({'kind': 'longitudinal', 'type': tim, 'worlds': saved,
                         'restore_equal': detail['restore_equal'],
                         'correction_required': comparison['witness']['required'],
                         'correction_spent': comparison['witness']['spent'],
                         'control_required': comparison['control']['required'],
                         'control_spent': comparison['control']['spent'],
                         'terminal': comparison['terminal']})
            ref = save(out, tim + '-undeformed', undeformed(tim))
            rows.append({'kind': 'undeformed', 'type': tim, 'world': ref})
            raw.append({'kind': 'undeformed', 'type': tim, **ref})

        for effect in ('forecast', 'salience', 'exclude_route'):
            worlds = {}
            _, detail = unsupported_longitudinal(effect, worlds)
            saved = {}
            for stage, engine in worlds.items():
                ref = save(out, 'unsupported-' + effect + '-' + stage, engine)
                saved[stage] = ref
                raw.append({'kind': 'unsupported', 'effect': effect, 'stage': stage, **ref})
            rows.append({'kind': 'unsupported', 'effect': effect, 'worlds': saved, **detail})

        engine, detail = exhaustion()
        ref = save(out, 'finite-exhaustion', engine)
        rows.append({'kind': 'exhaustion', 'world': ref, **detail})
        raw.append({'kind': 'exhaustion', **ref})

        engine, detail = failed_work()
        ref = save(out, 'cancelled-paid-work', engine)
        rows.append({'kind': 'cancelled_work', 'world': ref, **detail})
        raw.append({'kind': 'cancelled_work', **ref})
    except Exception:
        (out / 'failure.txt').write_text(traceback.format_exc())
        raise

    unchanged = manifest() == freeze
    assert len(raw) == 29
    summary = {'passed': unchanged, 'raw_worlds': len(raw), 'types': ['iee', 'sli'],
               'longitudinal_histories': 2, 'unsupported_clearances': 3,
               'exhaustion_worlds': 1, 'cancelled_work_worlds': 1,
               'exact_restore_pairs': 2, 'source_unchanged': unchanged}
    (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    build_ledger(out, ledger, summary, raw)
    assert manifest() == freeze
    print('PASS longitudinal Shell raw worlds', len(raw), flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
