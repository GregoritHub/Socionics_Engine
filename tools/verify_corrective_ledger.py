"""Independent corrected mapping assessment; never imports corrected builder."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from tools import verify_c7_final as inherited
from tools import verify_corrective_native as native
from tools import verify_corrective_parents as parents
from tools import verify_longitudinal_shell as longitudinal
from tools import verify_corrective_release as release


def read(p):
    return json.loads(p.read_text())


def verify(root, run, candidate):
    ledger = read(candidate)
    assert ledger['schema'] == 'srl-corrective-ledger-candidate-v1'
    assert ledger['goal_complete'] is False
    assert ledger['run_directory'] == str(run.resolve())
    assert ledger['mapping_protocol_sha256'] == hashlib.sha256((ROOT / 'contracts/C7_Corrective_Evaluation_Protocol_v1.json').read_bytes()).hexdigest()
    old_path = ROOT / 'C7_Final_Ledger_v2.json'; old = read(old_path)
    assert ledger['historical_ledger_sha256'] == hashlib.sha256(old_path.read_bytes()).hexdigest()
    assert ledger['historical_registry'] == old['evidence_objects']
    for archive, member, digest, size in ledger['historical_registry']:
        assert inherited.identity(root / member) == (digest, size), member
    # All inherited applicable semantics remain necessary. Native partial and parent
    # gates below replace the defective historical mappings, not their raw history.
    inherited.composition_and_nesting(root)
    actual = [(r['route'], r['polarity']) for r in ledger['rows']]
    expected = {(r, p) for r in inherited.ROUTES for p in inherited.FACES}
    assert len(actual) == len(set(actual)) == 32 and set(actual) == expected
    nrows = read(run / 'corrective-native/rows.json')
    prows = read(run / 'corrective-parents/rows.json')
    lrows = read(run / 'corrective-longitudinal/rows.json')
    native.validate_keys(nrows['comparisons']); parents.validate_keys(prows)
    checked = set()
    for row in ledger['rows']:
        route, face = row['route'], row['polarity']
        for check in (inherited.canonical_semantics, inherited.workflow_semantics, inherited.all_types,
                      inherited.selection, inherited.shell, inherited.sustained):
            check(root, route, face)
        inherited.faces(root, route)
        assert set(row['settings']) == {'canonical', 'workflow'}
        for setting, entry in row['settings'].items():
            mapped = entry['native_continuations']
            assert len(mapped) == 3 and {r['boundary'] for r in mapped} == {0, 1, 2}
            assert all((r['setting'], r['route'], r['polarity']) == (setting, route, face) for r in mapped)
            assert sorted(mapped, key=lambda r:r['boundary']) == sorted([r for r in nrows['comparisons'] if (r['setting'],r['route'],r['polarity']) == (setting,route,face)], key=lambda r:r['boundary'])
            assert entry['negative_worlds'] == [r for r in nrows['negatives'] if r['setting'] == setting]
            assert entry['parent_worlds'] == [r for r in prows if r['setting'] == setting]
            assert len(entry['parent_worlds']) == 4
            assert entry['longitudinal_controls'] == lrows
            assert entry['complete'] is False and row['full_release_complete'] is False
            sections = entry['inherited_sections']['requirements']
            assert set(sections) == {f'9.{i}' for i in range(1,13)}
            for i in range(1,12):
                expected_status = 'not_applicable' if i == 5 and (route, face) not in inherited.FAMILY_CELLS else 'passed'
                assert sections[f'9.{i}']['status'] == expected_status
            inherited.check_declared_refs(root, entry['inherited_sections'], checked, ledger['evidence_objects'])
    # Reread and reconstruct real saved worlds independently, rather than accept
    # a summary or the mapping builder's flags. These calls are mandatory.
    n = native.verify(run / 'corrective-native')
    p = parents.verify(run / 'corrective-parents')
    l = longitudinal.verify_corrective(run / 'corrective-longitudinal')
    full = release.verify(run)
    assert all(v['passed'] for v in (n, p, l, full))
    return {'passed': True, 'rows_reconstructed': 32, 'independent_of_corrected_builder': True,
            'native_comparisons': n['comparisons'], 'parent_worlds': p['new_parent_scenarios'],
            'historical_members_checked': len(ledger['historical_registry']),
            'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
            'complete_release_evaluation': True, 'release_decision': 'pending clean durable delivery',
            'goal_complete': False, 'historical_delivery_gate_verified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('historical_root', type=Path); p.add_argument('run', type=Path); p.add_argument('candidate', type=Path); p.add_argument('output', type=Path)
    a=p.parse_args(); result=verify(a.historical_root.resolve(),a.run.resolve(),a.candidate)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
