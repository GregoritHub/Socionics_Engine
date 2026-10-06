"""Complete C3 decision: original gate plus source-binding transfer supplement."""
import argparse,contextlib,hashlib,io,json,sys
from pathlib import Path
import verify_c3 as base
from hle_unified import codec
from hle_unified.crossing_audit import audit,payload


def main():
 p=argparse.ArgumentParser(); p.add_argument('--evidence',type=Path,required=True); a=p.parse_args()
 output=io.StringIO()
 with contextlib.redirect_stdout(output): base.main()
 decision=json.loads(output.getvalue())
 folder=a.evidence/'source_transfer'; q=base.read(folder/'summary.json')
 assert q['passed'] and q['source_unchanged'] and q['tests']==2 and q['type_cases']==96
 assert not (q['failures'] or q['errors'] or q['skipped']) and all(r['status']=='passed' for r in q['rows'])
 base.check(base.read(folder/'execution_source.json'))
 pairs={}
 for result_file in folder.glob('*/result.json'):
  row=base.read(result_file); here=result_file.parent
  txs=codec.loads(base.raw(here/'transactions.json.gz')); access=base.raw(here/'access.checkpoint.json.gz')
  versions={v.ref:v for tx in txs for v in tx.versions}; rejected=False
  try: audit(txs,access)
  except ValueError: rejected=True
  assert rejected==row['control']
  for key,field in (('before','before'),('after','after')):
   assert payload(versions[codec.decode(row['refs'][key])])['amount']==row[field]
  assert payload(versions[codec.decode(row['refs']['prior'])])['cap']==row['own_cap']==5
  assert row['before']==4 and row['exact_restore']
  assert hashlib.sha256(base.raw(here/'engine.checkpoint.json.gz').encode()).hexdigest()==row['checkpoint_sha256']
  if row['control']: assert row['after']==4
  else: assert row['after']==(2 if row['route']=='Educate' else 1)
  pairs.setdefault((row['route'],row['polarity']),{})[row['control']]=row
 assert len(pairs)==6
 for pair in pairs.values():
  assert pair[False]['main_work']==pair[True]['main_work'] and pair[False]['after']!=pair[True]['after']
 decision.update(distinct_tests=decision['distinct_tests']+2,source_transfer_tests=2,source_transfer_type_cases=96,
  source_transfer_pairs=6,source_transfer_raw_witnesses=12,total_raw_witnesses=60)
 print(json.dumps(decision),flush=True)

if __name__=='__main__': main()
