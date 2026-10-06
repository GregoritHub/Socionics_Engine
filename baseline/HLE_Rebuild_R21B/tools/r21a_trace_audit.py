"""Recheck actual physical horizon facts directly from retained raw traces."""
import gzip
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.codec import loads
from hle.individuation_records import CircuitTransaction
from hle.resource_contracts import BUDGETS
from r21_workloads import make_world
from r21a_audit import horizon_audit
from r21_evidence import save


def main():
    out = ROOT/'evidence/r21a/development'
    summary = json.loads((out/'summary.json').read_text())
    results = []
    for case in summary['rows']:
        report = json.loads((out/(case['name']+'.json')).read_text())
        for kind, meta_key, assessment_key in (('episode', 'meta', 'assessment'),
                                              ('independent', 'independent_meta', 'independent_assessment')):
            meta = report[meta_key];scope = meta['scope'];item = report['traces'][kind]
            world, _ = make_world(scope['tim'], scope['seed'], BUDGETS[scope['regime']])
            journal = [];digest = hashlib.sha256();records = {}
            with gzip.open(out/item['path'], 'rt') as stream:
                for line in stream:
                    digest.update(line.encode());tx = loads(line);journal.append(tx)
                    if type(tx) is CircuitTransaction and tx.signal is not None:records[tx.signal.ref] = tx.signal
            # This view supplies only genesis inputs, decoded transactions and
            # raw signal records. No live clearance or participant state.
            view = SimpleNamespace(config=world.config, release=world.release, _journal=journal, _records=records)
            result = horizon_audit(view, meta['opportunities'], scope['seed'], meta['cuts'].get('clearance'))
            previous = report[assessment_key]['sustained']
            ok = (digest.hexdigest()==item['sha256'] and not result['errors']
                  and result['eligible']==previous['eligible'] and result['passed']==previous['passed'])
            results.append({'case': case['name'], 'execution': kind, 'trace_sha256': digest.hexdigest(),
                'completed_windows': len(meta['opportunities']), 'errors': result['errors'],
                'eligible': result['eligible'], 'full_horizon': result['passed'], 'passed': ok})
            print(json.dumps(results[-1]), flush=True)
    data = {'schema': 'r21a-raw-physical-horizon-audit-v1', 'executions': len(results),
            'windows': sum(x['completed_windows'] for x in results),
            'passed': len(results)==36 and all(x['passed'] for x in results), 'rows': results}
    save(ROOT/'evidence/r21a/horizon_physical_audit.json', data)
    return 0 if data['passed'] else 1


if __name__ == '__main__':raise SystemExit(main())
