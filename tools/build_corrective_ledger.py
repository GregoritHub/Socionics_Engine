"""Prospective corrected ledger mapping; no historical regeneration or acceptance."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from tools import evaluate_c7_final as historical


def read(p):
    return json.loads(p.read_text())


def historical_inventory(root, objects):
    missing = []
    for archive, member, digest, size in objects:
        p = root / member
        if not p.is_file() or p.stat().st_size != size or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            missing.append(member)
    if missing:
        raise FileNotFoundError('Historical bytes missing/mismatched: ' + repr(missing))


def native_mapping(rows, setting, route, polarity):
    selected = [r for r in rows if (r['setting'], r['route'], r['polarity']) == (setting, route, polarity)]
    assert len(selected) == 3 and {r['boundary'] for r in selected} == {0, 1, 2}, 'native cell mapping differs'
    return sorted(selected, key=lambda r: r['boundary'])


def build(root, run):
    prior = read(ROOT / 'C7_Final_Ledger_v2.json')
    historical_inventory(root, prior['evidence_objects'])
    old = historical.build(root, ROOT / 'contracts/C7_Final_Protocol_v1.json')
    native = read(run / 'corrective-native/rows.json')
    parents = read(run / 'corrective-parents/rows.json')
    longitudinal = read(run / 'corrective-longitudinal/rows.json')
    rows = []
    for row in old['rows']:
        settings = {}
        for setting in ('canonical', 'workflow'):
            settings[setting] = {
                'native_continuations': native_mapping(native['comparisons'], setting, row['route'], row['polarity']),
                'negative_worlds': [r for r in native['negatives'] if r['setting'] == setting],
                'parent_worlds': [r for r in parents if r['setting'] == setting],
                'longitudinal_controls': longitudinal,
                'inherited_sections': row['settings'][setting],
                'complete': False}
        rows.append({'route': row['route'], 'polarity': row['polarity'], 'settings': settings, 'full_release_complete': False})
    return {'schema': 'srl-corrective-ledger-candidate-v1', 'rows': rows, 'evidence_objects': old['evidence_objects'],
            'historical_ledger_sha256': hashlib.sha256((ROOT / 'C7_Final_Ledger_v2.json').read_bytes()).hexdigest(),
            'historical_registry': prior['evidence_objects'], 'run_directory': str(run.resolve()),
            'mapping_protocol_sha256': hashlib.sha256((ROOT / 'contracts/C7_Corrective_Evaluation_Protocol_v1.json').read_bytes()).hexdigest(),
            'release_decision': 'pending independent assessment and clean delivery', 'goal_complete': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('historical_root', type=Path); p.add_argument('run', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); result = build(a.historical_root.resolve(), a.run.resolve())
    a.output.write_text(json.dumps(result, indent=2) + '\n')
