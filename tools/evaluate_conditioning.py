"""Standalone observations from historical raw transactions, never execution."""
import gzip,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.conditioning_audit import observations
from hle_unified.selection_records import dumps
from run_energy_regression import manifest

def engine_text(obj):
    if isinstance(obj,str):
        parsed=json.loads(obj)
        if isinstance(parsed.get('payload'),dict) and 'world' in parsed['payload']:return obj
        obj=parsed
    if isinstance(obj.get('payload'),dict) and 'world' in obj['payload']:
        return json.dumps(obj,sort_keys=True,separators=(',',':'))
    for key in ('engine','population'):
        if key in obj:return engine_text(obj[key])
    raise ValueError('no raw engine envelope')

def main(out):
    out.mkdir(parents=True,exist_ok=False)
    freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    inputs=json.loads((ROOT/'evidence/FB7.1/Historical_Conditioning_Inputs.json').read_text())
    histories={};rejected=[]
    for entry in inputs:
        p=ROOT/entry['path'];b=p.read_bytes()
        assert hashlib.sha256(b).hexdigest()==entry['sha256'],entry['path']
        raw=gzip.decompress(b) if p.suffix=='.gz' else b
        try:
            text=engine_text(raw.decode());digest=hashlib.sha256(text.encode()).hexdigest()
            if digest not in histories:
                envelope=json.loads(text);payload=unseal(text,envelope['schema'])
                txs=OperationStore.restore(payload['world']).journal()
                rows=json.loads(dumps(observations(txs)))
                histories[digest]=dict(engine_sha256=digest,transactions=len(txs),actors=rows,aliases=[])
            histories[digest]['aliases'].append(entry)
        except Exception as exc:rejected.append(dict(**entry,error=repr(exc)))
    forbidden=[x for x in sys.modules if x.startswith('hle_unified.') and ('execution' in x or x.endswith('.population') or x.endswith('.workflow_agenda'))]
    result=dict(passed=not rejected and manifest()==freeze and not forbidden,input_count=len(inputs),unique_histories=len(histories),source_unchanged=manifest()==freeze,execution_imports=forbidden,rejected=rejected,histories=list(histories.values()))
    (out/'observations.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='histories'}),flush=True)
    return result
if __name__=='__main__':sys.exit(not main(pathlib.Path(sys.argv[1]).resolve())['passed'])
