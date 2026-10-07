"""Read saved raw worlds independently, never importing drivers or engines."""
import gzip, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs
from hle_unified.selection_records import loads
from hle_unified.workflow_continuation_audit import audit_continuation
from hle_unified.workflow_selection_audit import audit
from hle_unified.workflow_reference import decode
from hle_unified.records import Account


def verify(folder):
    reports = []
    for row in json.loads((folder / 'rows.json').read_text()):
        path = folder / row['file']; assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        state = loads(gzip.decompress(path.read_bytes()).decode())
        raw = unseal(state['population']['engine'], 'hle-full-crux-c7-workflow-selection-v4')
        txs = OperationStore.restore(raw['world']).journal()
        native = audit(txs, raw['access'])
        if row['case'] == 'withheld-generated-handoff':
            try: audit_continuation(txs, state)
            except ValueError as exc:
                assert 'provenance' in str(exc); report = dict(rejected=str(exc))
            else: raise AssertionError('withheld provenance accepted')
        else: report = audit_continuation(txs, state)
        if row['case'] == 'generated-chain':
            recipes = [x['recipe'] for x in native['selection_rows']]
            assert recipes == ['workflow-'+n+'-expenditure-v1' for n in ('theorize','apply','embody')]
            assert native['physical_commits'] == 1
            decisions = [decode(v.facet(Account).content[0].object) for tx in txs for v in tx.versions
                         if v.ref.identity.namespace == 'c7w.output' and v.facet(Account)]
            assert any(x.get('next_action') == 'use' and x.get('kind') == 'decision' for x in decisions)
        reports.append(dict(case=row['case'], continuation=report, native_passed=native['passed'],
                            native_selections=native['workflow_selections']))
    result = dict(passed=True, cases=len(reports), participant_replay=False, reports=reports)
    (folder/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',len(reports),'independent raw cases',flush=True)

if __name__ == '__main__': verify(Path(sys.argv[1]))
