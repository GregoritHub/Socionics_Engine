"""Execute the prospectively declared FB6.2 commands on one immutable freeze.

This harness supplies paths and scheduling only; each panel retains its own
fixtures, semantic auditors and controls. Measurements never overlap the pool.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'contracts/C7_Corrective_Evaluation_Protocol_v1.json'
FREEZE = ROOT / 'C7_Corrective_Final_Source_Freeze_v1.json'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def changed(freeze):
    return [name for name, sha in freeze.items()
            if not (ROOT / name).is_file()
            or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha]


def execute(job, out, freeze):
    key = job['id']
    record = out / 'commands' / (key + '.json')
    if record.exists():
        previous = json.loads(record.read_text())
        if previous.get('passed'):
            return previous
        raise RuntimeError('Failed/incomplete command retained; use a new attempt: ' + key)
    args = [str(out) if word == '{out}' else word.replace('{out}', str(out))
            for word in job['argv']]
    args[0] = sys.executable
    before = changed(freeze)
    if before:
        raise RuntimeError('Frozen source changed: ' + repr(before))
    row = {'id': key, 'argv': args, 'cwd': str(ROOT),
           'started_at': datetime.now(timezone.utc).isoformat(),
           'status': 'running', 'passed': False,
           'freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest()}
    write(record, row)
    started = time.monotonic()
    print('START', key, flush=True)
    try:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        with (out / 'commands' / (key + '.stdout.log')).open('w') as stdout:
            proc = subprocess.run(args, cwd=ROOT, env=env, stdout=stdout,
                                  stderr=subprocess.STDOUT)
        row['exit_code'] = proc.returncode
        if job.get('result'):
            result = Path(job['result'].replace('{out}', str(out)))
            data = json.loads(result.read_text())
            row['result'] = str(result.relative_to(ROOT))
            row['result_sha256'] = hashlib.sha256(result.read_bytes()).hexdigest()
            row['result_passed'] = data.get('passed') is True
            row['counts'] = {k: data.get(k) for k in job.get('expected_counts', {})}
            row['counts_match'] = all(data.get(k) == v for k, v in job.get('expected_counts', {}).items())
        if key.endswith('-probe'):
            count = 10 if key == 'closure-probe' else 17
            log = (out / 'commands' / (key + '.stdout.log')).read_text()
            row['probe_count'] = count
            row['probe_passed'] = f'{count}/{count} passed  (R21B kernel; pyref rerun owed)' in log
        row['source_changes'] = changed(freeze)
        row['source_unchanged'] = not row['source_changes']
        row['passed'] = (proc.returncode == 0 and row['source_unchanged']
                         and row.get('result_passed', True)
                         and row.get('counts_match', True)
                         and row.get('probe_passed', True))
    except Exception:
        row['exception'] = traceback.format_exc()
        row['passed'] = False
    row['seconds'] = time.monotonic() - started
    row['finished_at'] = datetime.now(timezone.utc).isoformat()
    row['status'] = 'passed' if row['passed'] else 'failed'
    write(record, row)
    print('END', key, row['status'], round(row['seconds'], 2), flush=True)
    return row


def validate_protocol(protocol):
    inherited = json.loads((ROOT / protocol['inherited_protocol']['path']).read_text())
    assert hashlib.sha256((ROOT / protocol['inherited_protocol']['path']).read_bytes()).hexdigest() == protocol['inherited_protocol']['sha256']
    jobs = {j['id']: j for j in protocol['jobs']}
    assert len(jobs) == len(protocol['jobs']) == 54
    assert all(jobs.get(j['id']) == j for j in inherited['jobs']), 'inherited job changed or missing'
    assert all(set(j['depends_on']) <= set(jobs) for j in jobs.values())
    pending = set(jobs); done = set()
    while pending:
        ready = {k for k in pending if set(jobs[k]['depends_on']) <= done}
        assert ready, 'cyclic job dependency'
        pending -= ready; done |= ready
    inventory = json.loads((ROOT / protocol['accepted_method_inventory']).read_text())
    ids = inventory['method_ids']
    assert len(ids) == len(set(ids)) == protocol['required_unique_methods'] == 742
    prior = json.loads((ROOT / 'evidence/FB6.2/Accepted_Method_Inventory.json').read_text())['method_ids']
    assert set(inventory['inherited_method_ids']) == set(prior)
    assert set(ids) == set(prior) | set(inventory['prior_corrective_method_ids']) | set(inventory['new_preparation_method_ids'])
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    parser.add_argument('--check-plan', action='store_true')
    parser.add_argument('--stage', choices=('all', 'evaluation', 'measurements'), default='all')
    args = parser.parse_args()
    out = args.out.resolve()
    out.relative_to(ROOT)
    protocol = json.loads(PROTOCOL.read_text())
    validate_protocol(protocol)
    if args.check_plan:
        print(json.dumps({'plan_valid': True, 'jobs': 54, 'methods': 742, 'evaluation_run': False}))
        return
    out.mkdir(parents=True, exist_ok=True)
    freeze = json.loads(FREEZE.read_text())
    assert not changed(freeze), 'source differs from freeze'
    required = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*.py') if '.git' not in p.parts and not any(x.startswith('evidence') for x in p.relative_to(ROOT).parts)}
    required |= {str(p.relative_to(ROOT)) for folder in ('tools', 'contracts') for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert required <= set(freeze), 'incomplete release freeze'
    assert str(PROTOCOL.relative_to(ROOT)) in freeze
    protocol = json.loads(PROTOCOL.read_text())
    jobs = protocol['jobs']
    assert len({j['id'] for j in jobs}) == len(jobs)
    done = {}
    for path in (out / 'commands').glob('*.json'):
        row = json.loads(path.read_text())
        assert row.get('passed'), 'failed/incomplete command must not be silently retried'
        assert row['freeze_sha256'] == hashlib.sha256(FREEZE.read_bytes()).hexdigest()
        assert row['id'] in {j['id'] for j in jobs}, 'unknown resumed command'
        if row.get('result'):
            assert hashlib.sha256((ROOT / row['result']).read_bytes()).hexdigest() == row['result_sha256'], 'resumed result changed'
        done[row['id']] = row
    evaluation = [j for j in jobs if j['lane'] != 'measurements']
    if args.stage != 'measurements':
        pending = [j for j in evaluation if j['id'] not in done]
        active = {}
        failed = False
        with ThreadPoolExecutor(max_workers=protocol['workers']['evaluation_max_concurrent_commands']) as pool:
            while pending or active:
                if not failed:
                    for job in pending[:]:
                        if len(active) >= protocol['workers']['evaluation_max_concurrent_commands']:
                            break
                        if all(dep in done and done[dep]['passed'] for dep in job['depends_on']):
                            active[pool.submit(execute, job, out, freeze)] = job
                            pending.remove(job)
                if not active:
                    if pending:
                        raise RuntimeError('Unfinished dependencies or prior failure: ' + repr([j['id'] for j in pending]))
                    break
                completed, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in completed:
                    job = active.pop(future)
                    row = future.result()
                    done[job['id']] = row
                    failed |= not row['passed']
                write(out / 'progress.json', {'passed_jobs': sorted(k for k, v in done.items() if v['passed']),
                      'failed_jobs': sorted(k for k, v in done.items() if not v['passed']),
                      'running_jobs': [j['id'] for j in active.values()],
                      'pending_jobs': [j['id'] for j in pending]})
                if failed and not active:
                    raise RuntimeError('Failed evaluation retained; no measurement started')
    assert all(j['id'] in done and done[j['id']]['passed'] for j in evaluation)
    if args.stage != 'evaluation':
        for job in [j for j in jobs if j['lane'] == 'measurements']:
            row = execute(job, out, freeze)
            done[job['id']] = row
            if not row['passed']:
                raise RuntimeError('Failed measurement retained: ' + job['id'])
    write(out / 'run_summary.json', {'passed': len(done) == len(jobs) and not changed(freeze) and all(v['passed'] for v in done.values()),
          'completed_jobs': sorted(done), 'required_jobs': len(jobs),
          'complete': len(done) == len(jobs), 'source_unchanged': not changed(freeze),
          'stage': args.stage, 'python': sys.version})


if __name__ == '__main__':
    main()
