"""Fail-closed release decision from the complete frozen execution panel."""
import argparse
import gzip
from zipfile import ZipFile
from u14_support import *
from verify_baseline import verify


def artifact_exact(path,artifact,name='final'):
    for kind in ('checkpoint','transactions'):
        data=gzip.decompress((path/f'{name}.{kind}.json.gz').read_bytes())
        if digest(data)!=artifact[kind+'_sha256']:return False
    return True


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence;identity=verify_freeze();protocol=json.loads((ROOT/'contracts/U14_Protocol_v1.json').read_text())
    gates={};details={};total=0
    for panel,cases in protocol['panels'].items():
        root=out/panel;summary=json.loads((root/'summary.json').read_text());planned=[c['id'] for c in cases]
        gates[panel+':complete']=bool(cases) and summary['planned']==len(cases) and summary['executed']==len(cases) and [r['id'] for r in summary['rows']]==planned
        gates[panel+':source']=summary['source_identity']==identity and summary['source_unchanged']
        exact=True;passed=True;outcomes={};successes=0
        for case in cases:
            path=root/case['id'];r=json.loads((path/'summary.json').read_text())
            passed=passed and r['passed'] and bool(r.get('checks')) and all(r['checks'].values()) and r['case']==case and r['source_identity']==identity
            artifacts=r.get('artifacts',{'final':r.get('artifact')})
            for name,artifact in artifacts.items():
                exact=exact and artifact is not None and artifact_exact(path,artifact,name)
            outcome=r.get('outcome','completed');outcomes[outcome]=outcomes.get(outcome,0)+1
            successes+=r.get('successes',0)
        gates[panel+':mandatory']=passed and summary['passed'];gates[panel+':raw_artifacts']=exact
        details[panel]=dict(cases=len(cases),outcomes=outcomes,sustained_successes=successes);total+=len(cases)
    count=0
    for stage,expected in [('native_tests',454),('legacy_tests',840),('fidelity',72)]:
        summary=json.loads((out/stage/'summary.json').read_text())
        gates[stage]=summary['passed'] and summary['tests']==expected
        if stage!='fidelity':gates[stage+':source']=summary['source_identity']==identity and summary['source_unchanged']
        count+=summary['tests']
    measurement=json.loads((out/'measurements/summary.json').read_text())
    gates['fresh_performance']=measurement['passed'] and all(measurement['gates'].values())
    gates['performance_source']=measurement['source_identity']==identity and measurement['source_unchanged']
    witness=json.loads((out/'witness/summary.json').read_text())
    gates['complete_witness_and_archive']=witness['passed'] and all(witness['checks'].values())
    inherited=json.loads((ROOT/'U13_Runtime_Manifest_v1.json').read_text())
    gates['u13_runtime_exact']=all(digest((ROOT/k).read_bytes())==v for k,v in inherited.items())
    prior_members=json.loads((ROOT/'U13_Source_Manifest_v1.json').read_text())['members']
    protected={k:v for k,v in prior_members.items() if k.startswith(('reference_u12/','tests_u','contracts/')) or k in ('tools/u13_benchmark.py','tools/u13_interaction_benchmark.py')}
    gates['u13_fixtures_protocols_reference_exact']=all(digest((ROOT/k).read_bytes())==v for k,v in protected.items())
    with ZipFile(out/'inherited/HLE_Unified_U13_Evidence_v1.zip') as z:
        old=json.loads(z.read('HLE_Unified_U13_Evidence_v1/final_measurements/summary.json'))
    gates['retained_u13_measurement_gates']=old['passed'] and len(old['gates'])==95 and all(old['gates'].values())
    baseline=verify();write_json(out/'baseline_final.json',baseline);gates['frozen_baseline']=baseline['passed']
    result=dict(schema='hle-unified-u14-release-decision-v1',passed=all(gates.values()),gates=gates,
        release_cases=total,distinct_tests=count,panels=details,performance=measurement['geomeans'],
        retained_u13_gate_count=len(old['gates']),source_identity=identity,execution_manifest_sha256=digest((ROOT/'U14_Execution_Manifest_v1.json').read_bytes()),
        scope='Bounded workshop release only. R21C certification, unrestricted development/language/population and empirical psychological validation remain open.')
    write_json(out/'acceptance_summary.json',result)
    print(json.dumps(result),flush=True);return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
