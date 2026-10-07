"""Independent raw verifier: no agenda, fixture, selector or executor imports."""
import gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore,attrs
from hle_unified.selection_records import loads
from hle_unified.workflow_agenda_audit import audit_agenda,address
from hle_unified.workflow_selection_audit import audit
from hle_unified.workflow_reference import decode
from hle_unified.records import Account

EXPECTED={'theorize-apply-embody':('theorize-expenditure','apply-expenditure','embody-expenditure'),
'share-commune-identify':('share-expenditure','commune-expenditure','identify-expenditure'),
'coordinate-mobilize':('coordinate-expenditure','mobilize-expenditure','embody-expenditure'),
'institutionalize-educate':('institutionalize-accumulation','institutionalize-expenditure','educate-expenditure'),
'organize-integrate-apply':('theorize-accumulation','organize-expenditure','integrate-expenditure','apply-expenditure')}


def verify(folder):
    reports=[];producers={}
    for row in json.loads((folder/'rows.json').read_text()):
        path=folder/row['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        raw=loads(gzip.decompress(path.read_bytes()).decode());state=raw['state']
        engine=unseal(raw['engine'],'hle-full-crux-c7-workflow-selection-v4')
        txs=OperationStore.restore(engine['world']).journal();native=audit(txs,engine['access'])
        try:result=audit_agenda(txs,engine['access'],state)
        except ValueError as exc:
            assert row['control'] and 'provenance' in str(exc)
            result=dict(rejected=str(exc))
        else:
            assert not row['control'];result={k:v for k,v in result.items() if k!='native'}
        if 'family' in row:
            actor=state['template']['actor'];heads={v.ref.identity:v for tx in txs for v in tx.versions}
            first=attrs(heads[address('u4.operation',actor,'agenda:family:0:movement').identity])
            producers[row['family'],row['control']]=(first['spent'],first['recipe_key'])
            if not row['control']:
                assert [x['recipe'] for x in native['selection_rows']]==['workflow-'+n+'-v1' for n in EXPECTED[row['family']]]
                choices=[decode(v.facet(Account).content[0].object) for tx in txs for v in tx.versions
                         if v.ref.identity.namespace=='c7w.output' and v.facet(Account)]
                assert any(x.get('kind')=='decision' and x.get('next_task') is not None for x in choices)
                if row['family']=='share-commune-identify':
                    def output(key):
                        return decode(heads[address('c7w.output',actor,key).identity].facet(Account).content[0].object)
                    before=output('agenda-renewal-before');after=output('agenda-renewal-after');final=output('agenda-fixed-query')
                    assert before['next_task']=='handover' and after['next_task'] is None and final['next_task'] is None
                    assert before['completed']==after['completed']==final['completed']==('maintain',)
                    assert before['clock']==after['clock']==final['clock']==3
                    shared_values=[decode(attrs(heads[ref.identity])['payload']) for ref in state['results'][:2]]
                    windows=[next(t[4] for t in x['tasks'] if t[0]=='handover') for x in shared_values]
                    assert windows==[4,2]
                    assert before['source']==state['results'][0] and after['source']==state['results'][1]
                    assert final['source']==state['results'][2]

        reports.append(dict(case=row['case'],agenda=result,native_passed=native['passed'],selections=native['workflow_selections']))
    assert all(producers[name,False]==producers[name,True] for name in EXPECTED)
    result=dict(passed=True,cases=len(reports),families=5,controls=5,matched_producer_costs=True,participant_replay=False,reports=reports)
    (folder/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',len(reports),'raw cases; five generated families and matched controls',flush=True)

if __name__=='__main__':verify(Path(sys.argv[1]))
