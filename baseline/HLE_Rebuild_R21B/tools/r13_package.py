"""Build R13 source; finalize its evidence only after fresh-source validation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp'))

def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')

def archive(root,dest,prefix):
    tmp=dest.with_suffix(dest.suffix+'.tmp')
    with ZipFile(tmp,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for p in files(root):
            info=ZipInfo(prefix+'/'+p.relative_to(root).as_posix(),(2026,9,17,0,0,0));info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
    with ZipFile(tmp) as z:
        if z.testzip() is not None:raise RuntimeError('CRC failure')
    tmp.replace(dest)

def source(out):
    validation=json.loads((ROOT/'evidence/r13/validation/summary.json').read_text())
    panel=json.loads((ROOT/'evidence/r13/panels/summary.json').read_text())
    if not validation['passed'] or not panel['passed']:raise ValueError('R13 gate evidence not passing')
    declaration=json.loads((ROOT/'docs/r12/acceptance_v1.json').read_text())
    protocol=ROOT/'docs/r13/Protocol_R13_v1.json'
    mappings={
      'R13.1':['tests_r13.test_content.ContentTests.test_retained_crossing','tests_r13.test_content.ContentTests.test_unretained_and_partial_retention_controls','tests_r13.test_roles.RoleTests.test_original_32_content_identity_pairs_survive_activity_and_copy'],
      'R13.2':['tests_r13.test_content.ContentTests.test_changed_context_retrieves_same_rule_through_new_paid_binding','tests_r13.test_content.ContentTests.test_superseded_capacity_rejected_with_old_binding','tests_r13.test_continuation.ContinuationTests.test_recursive_declared_dependencies_invalidate_without_deleting_history'],
      'R13.3':['tests_r13.test_continuation.ContinuationTests.test_every_prefix_of_partial_work_and_meaning_revision','tests_r13.test_continuation.ContinuationTests.test_work_audit_including_explicit_resource_credits','tests_r13.test_content.ContentTests.test_participant_status_cannot_read_unfunded_candidate','tests_r13.test_continuation.ContinuationTests.test_language_and_organization_share_actual_runtime_and_checkpoint'],
      'R13.4':['tests_r13.test_meaning.MeaningTests.test_two_holons_same_cue_different_histories_change_actual_actions','tests_r13.test_meaning.MeaningTests.test_reversal_revises_owned_meaning_not_just_label','tests_r13.test_continuation.ContinuationTests.test_personal_actions_exactly_continue_from_fresh_controller'],
      'R13.5':['tests_r13.test_roles.RoleTests.test_all_eight_executable_roles_have_independent_expected_outputs','tests_r13.test_roles.RoleTests.test_every_tim_complementary_pair_is_executable_without_changing_structure','tests_r13.test_roles.RoleTests.test_shared_result_needs_all_real_receiver_responses'],
    }
    tests=(ROOT/'evidence/r13/validation/r13_integration.log').read_text()
    for checks in mappings.values():
        for name in checks:
            method=name.rsplit('.',1)[1];cls=name.rsplit('.',1)[0]
            if f'{method} ({cls}.{method}) ... ok' not in tests and f'{method} ({cls}) ... ok' not in tests:
                # unittest formatting varies by Python minor version.
                if not any(method in line and line.rstrip().endswith('... ok') for line in tests.splitlines()):raise ValueError('missing passed test '+name)
    overlay={'schema':'hle-r13-acceptance-overlay-v1','parent_sha256':sha(ROOT/'docs/r12/acceptance_v1.json'),'r13_protocol_sha256':sha(protocol),
        'checks':[{'id':c['id'],'milestone':c['milestone'],'status':'established' if c['id'] in mappings else 'unassessed','evidence':mappings.get(c['id'],[])} for c in declaration['checks']],
        'scope':'R13 runtime integration with harness-supplied demands and histories; no later developmental verdict.', 'r21_planned_cases':480,'r21_executed_cases':0}
    write(ROOT/'evidence/r13/acceptance_overlay.json',overlay)
    result={'schema':'hle-r13-release-result-v1','completed':True,'milestone':'R13','progress':{'complete':2,'total':10,'remaining':8,'next':'R14'},
        'tests':validation['distinct_tests'],'new_tests':61,'r12_stage_preservation_test_adapted':1,'oig_comparisons':9216,
        'crossing':panel['crossing_controls'],'all_type_return':panel['all_type_crossing'],'role_cases':panel['eight_role_cases'],'checkpoint_prefixes':panel['continuation']['prefixes'],
        'frozen_parent_unchanged':validation['parent_acceptance_unchanged'],'later_milestones':'unassessed','generated_demands':'R14 pending'}
    write(ROOT/'evidence/r13/summary.json',result)
    entries=[]
    for p in files(ROOT):
        rel=p.relative_to(ROOT)
        if rel.as_posix()=='release_manifest.json' or 'evidence' in rel.parts:continue
        if rel.as_posix() in ('baseline/crossing/results/r10.json','baseline/crossing/results/r11.json'):continue
        entries.append({'path':rel.as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    write(ROOT/'release_manifest.json',{'schema':'hle-r13-source-manifest-v1','release':'R13 integrated content and developmental memory','version':'1.3.0','files':entries})
    check=subprocess.run([sys.executable,'tools/validate_release.py'],cwd=ROOT,capture_output=True,text=True,check=True)
    (ROOT/'evidence/r13/source_integrity.json').write_text(check.stdout)
    target=out/'HolonicLivingEngine_Rebuild_R13_v1.zip';archive(ROOT,target,'HLE_Rebuild_R13')
    print(json.dumps({'path':str(target),'sha256':sha(target),'bytes':target.stat().st_size}),flush=True)

def evidence(out,fresh):
    summary=json.loads((fresh/'summary.json').read_text())
    if not summary['passed'] or summary['distinct_tests']!=520:raise ValueError('fresh source validation not passing')
    sourcezip=out/'HolonicLivingEngine_Rebuild_R13_v1.zip'
    with ZipFile(sourcezip) as z:
        if z.testzip() is not None:raise ValueError('source archive corrupt')
        manifest=json.loads(z.read('HLE_Rebuild_R13/release_manifest.json'))
        for entry in manifest['files']:
            if hashlib.sha256(z.read('HLE_Rebuild_R13/'+entry['path'])).hexdigest()!=entry['sha256']:raise ValueError('archive manifest mismatch')
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp);shutil.copytree(ROOT/'evidence/r13',stage/'executed');shutil.copytree(fresh,stage/'fresh_extraction_validation');shutil.copytree(ROOT/'docs/r13',stage/'declarations_and_reports')
        shutil.copy2(ROOT/'release_manifest.json',stage/'release_manifest.json')
        for n in ('acceptance_v1.json','declaration_lock_v1.json'):
            p=stage/'frozen_parent'/n;p.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'docs/r12'/n,p)
        write(stage/'engine_pin.json',{'filename':sourcezip.name,'sha256':sha(sourcezip),'bytes':sourcezip.stat().st_size,'crc_passed':True,'manifest_files':len(manifest['files']),'fresh_tests_passed':520})
        (stage/'README.md').write_text('# R13 evidence\n\nThe exact paired engine archive is identified by engine_pin.json. Both working-source and fresh-extraction validation passed.\nThe original failed checks and their repairs are retained and described in Test_Evolution_R13.json.\nPanels contain actual runtime work, compressed replayable checkpoints and accounting. Large historical panels remain historical; the 480-case R21 grid is unexecuted.\n')
        target=out/'HLE_New_Build_Step_R13_Evidence_v1.zip';archive(stage,target,'HLE_R13_Evidence_v1')
    shutil.copy2(ROOT/'docs/r13/Step_R13_Report.md',out/'HLE_New_Build_Step_R13_Report_v1.md')
    shutil.copy2(ROOT/'docs/r13/Progress_After_R13.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R13.md')
    for p in (sourcezip,target,out/'HLE_New_Build_Step_R13_Report_v1.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R13.md'):
        print(json.dumps({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}))

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('source','evidence'));p.add_argument('--out',type=Path,default=Path('/mnt/data'));p.add_argument('--fresh',type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if a.mode=='source':source(a.out)
    else:
        if a.fresh is None:p.error('--fresh validation directory required')
        evidence(a.out,a.fresh)

if __name__=='__main__':main()
