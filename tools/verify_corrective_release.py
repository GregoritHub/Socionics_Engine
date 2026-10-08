"""Assess FB6.2 evidence without importing its runner or participant code."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_methods(ids, accepted):
    assert len(ids) == len(set(ids)) == len(accepted) == 742, 'duplicate or missing method'
    assert set(ids) == set(accepted), 'exact method identity differs'


def verify(out):
    out = out.resolve()
    protocol = read(ROOT / 'contracts/C7_Corrective_Evaluation_Protocol_v1.json')
    freeze_path = ROOT / 'C7_Corrective_Final_Source_Freeze_v1.json'
    freeze = read(freeze_path)
    assert freeze and all(sha(ROOT / p) == h for p, h in freeze.items())
    assert all(str(p.relative_to(ROOT)) in freeze for p in ROOT.rglob('*.py')
               if 'evidence' not in p.relative_to(ROOT).parts and '.git' not in p.parts)
    inherited_protocol = read(ROOT / protocol['inherited_protocol']['path'])
    assert sha(ROOT / protocol['inherited_protocol']['path']) == protocol['inherited_protocol']['sha256']
    jobs = {j['id']: j for j in protocol['jobs']}
    assert len(jobs) == len(protocol['jobs']) == 54
    assert all(jobs.get(j['id']) == j for j in inherited_protocol['jobs'])
    required = {str(p.relative_to(ROOT)) for folder in ('tools','contracts') for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert required <= set(freeze)
    assert {p.stem for p in (out / 'commands').glob('*.json')} == set(jobs)
    commands = []
    records = {}
    for job in protocol['jobs']:
        row = read(out / 'commands' / (job['id'] + '.json'))
        expected_argv = [s.replace('{out}', str(out)) for s in job['argv']]
        assert Path(row['argv'][0]).name.startswith('python')
        assert row['argv'][1:] == expected_argv[1:]
        assert row['exit_code'] == 0 and row['passed'] and row['source_unchanged']
        assert row['freeze_sha256'] == sha(freeze_path)
        if 'result' in job:
            result_path = Path(job['result'].replace('{out}', str(out)))
            result = read(result_path)
            assert sha(result_path) == row['result_sha256']
            assert result['passed'] is True
            assert all(result.get(k) == v for k, v in job.get('expected_counts', {}).items())
        records[job['id']] = row
        commands.append({'id': job['id'], 'record_sha256': sha(out / 'commands' / (job['id'] + '.json')),
                         'stdout_sha256': sha(out / 'commands' / (job['id'] + '.stdout.log'))})
    from datetime import datetime
    for job in protocol['jobs']:
        assert all(datetime.fromisoformat(records[dep]['finished_at']) <= datetime.fromisoformat(records[job['id']]['started_at']) for dep in job['depends_on']), 'job dependency order differs'
    evaluation_end = max(datetime.fromisoformat(records[j['id']]['finished_at']) for j in protocol['jobs'] if j['lane'] != 'measurements')
    previous = evaluation_end
    for job in [j for j in protocol['jobs'] if j['lane'] == 'measurements']:
        row = records[job['id']]
        assert datetime.fromisoformat(row['started_at']) >= previous, 'measurement overlap'
        previous = datetime.fromisoformat(row['finished_at'])
    inherited = read(out / 'inherited/summary.json')
    methods = []
    for package in inherited['packages']:
        saved = read(out / 'inherited' / package['package'] / 'summary.json')
        assert saved == package['summary'] and saved['passed']
        methods.extend(saved['rows'])
    assert len(methods) == 602
    methods.extend(read(out / 'additional/summary.json')['rows'])
    methods.extend(read(out / 'corrective-tests/summary.json')['rows'])
    ids = [row['test_id'] for row in methods]
    accepted = read(ROOT / protocol['accepted_method_inventory'])['method_ids']
    check_methods(ids, accepted)
    assert protocol['required_unique_methods'] == 742
    assert all(row['status'] == 'passed' for row in methods)
    prior = read(ROOT / 'evidence/FB6.2/Accepted_Method_Inventory.json')['method_ids']
    assert set(prior) <= set(accepted)
    kernel = read(ROOT / protocol['probes']['kernel_reference'])
    kernel_root = ROOT / 'baseline/HLE_Rebuild_R21B'
    assert all(sha(kernel_root / name) == digest for name, digest in kernel.items())
    for name, count in [('closure', 10), ('below_dcnh', 17)]:
        stdout = (out / 'commands' / (name + '-probe.stdout.log')).read_text()
        assert f'{count}/{count} passed  (R21B kernel; pyref rerun owed)' in stdout
    native = read(out / 'native-costs/summary.json')
    assert native['reference_ratio'] <= 2 and native['history_ratio'] <= 3
    assert native['matched_direct_world_and_access']
    costs = {'native_reference_ratio': native['reference_ratio'], 'native_history_ratio': native['history_ratio']}
    for name in ('workflow-costs', 'population-costs'):
        result = read(out / name / 'summary.json')
        costs[name] = {k: v['largest_smallest_ratio'] for k, v in result['history_panel'].items()}
        assert all(v <= 3 for v in costs[name].values())
    inventory = {'passed': True, 'distinct_methods': len(ids), 'executions': len(ids),
                 'method_ids': sorted(ids), 'missing_prior_methods': [], 'added_methods': sorted(set(ids)-set(prior))}
    (out / 'Accepted_Method_Inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    raw = [{'archive': 'fb6.2', 'member': str(p.relative_to(ROOT)),
            'sha256': sha(p), 'bytes': p.stat().st_size}
           for p in sorted(out.rglob('*.json.gz'))]
    assert raw
    result = {'schema': 'srl-corrective-full-evaluation-v1', 'batch': '6.2', 'passed': True,
              'source_unchanged': True, 'freeze': {'path': str(freeze_path.relative_to(ROOT)), 'sha256': sha(freeze_path), 'files': len(freeze)},
              'protocol_sha256': sha(ROOT / 'contracts/C7_Corrective_Evaluation_Protocol_v1.json'),
              'commands': commands, 'required_jobs': len(commands), 'distinct_methods': len(ids),
              'kernel_identical_to_intake': kernel, 'probes': {'closure': '10/10', 'below_dcnh': '17/17', 'pyref': 'owed'},
              'measurement_workers': 81, 'costs': costs, 'raw_files': len(raw), 'raw_worlds': raw,
              'release_decision': 'pending batch 6.3', 'phase_7_authorized': False}
    (out / 'Acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('raw_worlds', 'commands', 'kernel_identical_to_intake')}), flush=True)
    return result


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
