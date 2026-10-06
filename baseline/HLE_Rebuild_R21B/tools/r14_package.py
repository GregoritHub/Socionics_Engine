"""Build source, then finalize evidence only after full fresh-source verification."""
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
def files(root):return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp'))
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')

def archive(root,dest,prefix):
    temp=dest.with_suffix(dest.suffix+'.tmp')
    with ZipFile(temp,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for p in files(root):
            info=ZipInfo(prefix+'/'+p.relative_to(root).as_posix(),(2026,9,17,0,0,0));info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
    with ZipFile(temp) as z:
        if z.testzip() is not None:raise ValueError('archive CRC failed')
    temp.replace(dest)


def source(out):
    v=json.loads((ROOT/'evidence/r14/validation/summary.json').read_text());panel=json.loads((ROOT/'evidence/r14/panels/summary.json').read_text())
    if not v['passed'] or v['distinct_tests']!=573 or not panel['passed']:raise ValueError('R14 gates not established')
    old=json.loads((ROOT/'evidence/r13/acceptance_overlay.json').read_text())
    expected={
      'R14.1':['test_success_creates_two_later_different_demands','test_remove_wear_consequence_removes_maintenance_demand','test_no_loan_means_no_generated_return_obligation','test_net_reversal_before_discovery_is_not_persistent_new_demand'],
      'R14.2':['test_hidden_ownership_change_keeps_complete_local_view_and_choice_identical','test_visible_inspection_changes_subsequent_available_response','test_pure_policy_has_no_world_truth_evaluator_or_history_access'],
      'R14.3':['test_satisfied_ground_state_is_quiet_under_clock_only','test_holder_refuses_and_requester_exhausts_without_forced_transfer','test_resource_censored_initialization_is_not_clearance_or_development','test_absent_tool_exhausts_finite_known_repertoire_not_universe']}
    log=(ROOT/'evidence/r14/validation/r14_autonomy.log').read_text()
    # No gate overlay may cite a test absent from the actual passing run.
    for names in expected.values():
        for name in names:
            if not any(name+' (' in line and line.rstrip().endswith('... ok') for line in log.splitlines()):raise ValueError('missing passed gate witness '+name)
    new=[]
    for c in old['checks']:
        c=dict(c)
        if c['id'] in expected:c.update(status='established',evidence=expected[c['id']])
        new.append(c)
    write(ROOT/'evidence/r14/acceptance_overlay.json',{'schema':'hle-r14-acceptance-overlay-v1','parent_sha256':sha(ROOT/'docs/r12/acceptance_v1.json'),
        'r14_protocol_sha256':sha(ROOT/'docs/r14/Protocol_R14_v1.json'),'checks':new,
        'scope':'R14 finite generated instances and selected work. R13 gates preserved from their evidence; no R15-R21 verdict.','r21_planned_cases':480,'r21_executed_cases':0})
    write(ROOT/'evidence/r14/summary.json',{'schema':'hle-r14-release-result-v1','milestone':'R14','complete':True,'progress':{'complete':3,'total':10,'remaining':7,'next':'R15'},
        'tests':573,'new_tests':53,'changed_inherited_test_sources':0,'oig_reference_comparisons':9216,'population_cases':48,'population_passed':48,
        'effect_controls':9,'resource_cases':5,'checkpoint_prefixes':188,'fresh_actor_schedulers':5,'frozen_parent_unchanged':v['parent_acceptance_unchanged'],
        'future_milestones':'R15-R21 unassessed','r21_cases_executed':0})
    entries=[]
    for p in files(ROOT):
        rel=p.relative_to(ROOT)
        if rel.as_posix()=='release_manifest.json' or 'evidence' in rel.parts:continue
        if rel.as_posix() in ('baseline/crossing/results/r10.json','baseline/crossing/results/r11.json'):continue
        entries.append({'path':rel.as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    write(ROOT/'release_manifest.json',{'schema':'hle-r14-source-manifest-v1','release':'R14 generated demands and participant-selected work','version':'1.4.0','files':entries})
    p=subprocess.run([sys.executable,'tools/validate_release.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    (ROOT/'evidence/r14/source_integrity.json').write_text(p.stdout)
    target=out/'HolonicLivingEngine_Rebuild_R14_v1.zip';archive(ROOT,target,'HLE_Rebuild_R14')
    print(json.dumps({'path':str(target),'sha256':sha(target),'bytes':target.stat().st_size}),flush=True)


def evidence(out,fresh):
    checked=json.loads((fresh/'summary.json').read_text());reproduced=json.loads((fresh/'panel_reproduction.json').read_text())
    if not checked['passed'] or checked['distinct_tests']!=573 or not reproduced['passed']:raise ValueError('fresh source not fully verified')
    engine=out/'HolonicLivingEngine_Rebuild_R14_v1.zip'
    with ZipFile(engine) as z:
        if z.testzip() is not None:raise ValueError('corrupt source archive')
        manifest=json.loads(z.read('HLE_Rebuild_R14/release_manifest.json'))
        for e in manifest['files']:
            if hashlib.sha256(z.read('HLE_Rebuild_R14/'+e['path'])).hexdigest()!=e['sha256']:raise ValueError('manifest mismatch')
    saved_pin=json.loads((fresh/'archive_pin.json').read_text())
    if saved_pin['sha256']!=sha(engine):raise ValueError('fresh verification is of a different archive')
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);shutil.copytree(ROOT/'evidence/r14',root/'executed');shutil.copytree(fresh,root/'fresh_extraction_verification');shutil.copytree(ROOT/'docs/r14',root/'declarations_and_reports')
        shutil.copy2(ROOT/'release_manifest.json',root/'release_manifest.json')
        for name in ('acceptance_v1.json','declaration_lock_v1.json'):
            p=root/'frozen_parent'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'docs/r12'/name,p)
        write(root/'engine_pin.json',{'filename':engine.name,'sha256':sha(engine),'bytes':engine.stat().st_size,'manifest_files':len(manifest['files']),
            'crc_passed':True,'fresh_tests_passed':573,'fresh_behavior_reproduced':True})
        (root/'README.md').write_text('# R14 evidence\n\nengine_pin.json identifies the exact paired engine. Executed and fresh-extraction suites pass 573 tests.\nThe fresh behavioral panel matches the packaged deterministic outputs; host timing is separately measured, not required identical.\nOriginal failures and the incomplete early prefix run remain visible. R15-R21 remain unassessed.\n')
        target=out/'HLE_New_Build_Step_R14_Evidence_v1.zip';archive(root,target,'HLE_R14_Evidence_v1')
    shutil.copy2(ROOT/'docs/r14/Step_R14_Report.md',out/'HLE_New_Build_Step_R14_Report_v1.md')
    shutil.copy2(ROOT/'docs/r14/Progress_After_R14.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R14.md')
    for p in (engine,target,out/'HLE_New_Build_Step_R14_Report_v1.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R14.md'):
        print(json.dumps({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('source','evidence'));p.add_argument('--out',type=Path,default=Path('/mnt/data'));p.add_argument('--fresh',type=Path)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.mode=='source':source(args.out)
    else:
        if args.fresh is None:p.error('--fresh verification required')
        evidence(args.out,args.fresh)

if __name__=='__main__':main()
