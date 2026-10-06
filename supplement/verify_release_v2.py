"""Versioned reassessment: preserve the failed expectation, verify stronger controls."""
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from u14_support import write_json,verify_freeze,digest
from verify_u14_release import artifact_exact
from run_exhaustion import verify_supplement


def fallback_evidence(path):
    from hle_unified import codec
    from hle_unified.records import Material
    transactions=codec.loads(gzip.decompress((path/'final.transactions.json.gz').read_bytes()).decode())
    heads={};rows=[]
    for tx in transactions:
        for v in tx.versions:
            d={a.name:a.value for a in v.attributes}
            if d.get('record_type')=='operation' and d.get('status')=='succeeded' and d.get('primitive')=='repair':
                target=d.get('target');actor=d['actor']
                if target is not None and target.identity.key.startswith('u12-'):
                    care=next((value for key,value in heads.items() if key.key=='u11-care-'+actor.key),None)
                    if care is not None:
                        values={a.name:a.value for a in care.attributes}
                        if care.facet(Material).quantity==values['consumed']:
                            rows.append(dict(operation=v.ref.identity.key,actor=actor.key,spent=d['spent'],
                                             target=target.identity.key,exhausted_care_revision=care.ref.revision))
        for v in tx.versions:heads[v.ref.identity]=v
    if not rows or any(r['spent']<=0 for r in rows):raise ValueError('scarcity completion lacks paid fallback evidence')
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence
    base_identity=verify_freeze();identity=verify_supplement()
    original=json.loads((out/'acceptance_summary_v1.json').read_text())
    if original['source_identity']!=base_identity:raise ValueError('original source identity differs')
    unexpected=[k for k,v in original['gates'].items() if not v and k!='population:mandatory']
    gates=dict(original_nonpopulation_gates=not unexpected)
    protocol=json.loads((ROOT/'contracts/U14_Protocol_v1.json').read_text())
    failed_expectations=[];fallbacks={};population_invariants=True
    for case in protocol['panels']['population']:
        path=out/'population'/case['id'];r=json.loads((path/'summary.json').read_text())
        population_invariants=population_invariants and r['case']==case and all(
            v for k,v in r.get('checks',{}).items() if k!='declared_scarcity_visible') and bool(r.get('checks'))
        if not r['checks']['declared_scarcity_visible']:
            if case['regime']!='scarce':raise ValueError('wrong failed-control regime')
            failed_expectations.append(dict(id=case['id'],original_status='failed',failed_gate='declared_scarcity_visible',completed_practices=r['successes']))
            fallbacks[case['id']]=fallback_evidence(path)
    gates['all_original_population_invariants']=population_invariants
    gates['failed_expectations_retained_and_explained']=bool(failed_expectations) and set(fallbacks)=={r['id'] for r in failed_expectations}
    supplement=json.loads((ROOT/'supplement/protocol_v2.json').read_text())
    result=json.loads((out/'exhaustion/summary.json').read_text());cases=supplement['cases']
    gates['stronger_controls_complete']=result['passed'] and result['planned']==len(cases)==result['executed']==10
    gates['stronger_control_source']=result['source_identity']==identity and result['source_unchanged']
    controls=[]
    for case in cases:
        path=out/'exhaustion'/case['id'];r=json.loads((path/'summary.json').read_text())
        passed=r['case']==case and r['passed'] and all(r['checks'].values()) and r['source_identity']==identity and artifact_exact(path,r['artifact'])
        gates[case['id']]=passed;controls.append(dict(id=case['id'],successes=r['successes'],opportunities=case['opportunities']))
    summary=dict(schema='hle-u14-final-release-reassessment-v2',passed=all(gates.values()),gates=gates,
        original_assessment_passed=original['passed'],original_failed_expectations=failed_expectations,
        original_failed_gates=[k for k,v in original['gates'].items() if not v],paid_fallback_evidence=fallbacks,
        original_release_cases=original['release_cases'],additional_controls=len(cases),total_cases=original['release_cases']+len(cases),
        distinct_tests=original['distinct_tests'],panels=original['panels'],exhaustion_controls=controls,
        performance=original['performance'],original_execution_manifest_sha256=original['execution_manifest_sha256'],
        supplemental_manifest_sha256=digest((ROOT/'U14_Supplement_Manifest_v1.json').read_bytes()),
        source_identity=identity,scope='Versioned finite-workshop reassessment. The original must-fail care-scarcity expectation is explicitly failed, not retroactively passed. New stricter resource controls preserve successful paid adaptation and test actual exhaustion.')
    write_json(out/'acceptance_summary.json',summary);print(json.dumps(summary),flush=True)
    return 0 if summary['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
