"""Verify release records and package the C4 source/evidence delivery."""
import argparse,collections,hashlib,json,platform,re,shutil,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence_c4'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def files(root):return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def archive(path,entries):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(entries):
            item=zipfile.ZipInfo(name,date_time=(2026,9,23,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o100644<<16
            z.writestr(item,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    t=read(E/'tests_final/summary.json');w=read(E/'witnesses/summary.json');m=read(E/'measurements/summary.json')
    verification=read(E/'delivery_verification.json');ui=read(E/'inspector_qa.json')
    assert all(x['passed'] for x in (t,w,m,verification,ui))
    assert t['tests']==len(t['rows'])==554 and w['witnesses']==15 and m['workers']==36
    log_text='\n'.join((E/'tests_final'/n).read_text() for n in ('tests.log','continuation.log'))
    raw_passes=set(re.findall(r'test\w+ \(([^)]+)\) \.\.\. ok',log_text))
    assert all(r['test_id'] in raw_passes and r['status']=='passed' for r in t['rows'])
    for folder in ('tests_final','witnesses','measurements'):
        assert all(sha(ROOT/n)==h for n,h in read(E/folder/'execution_source.json').items())
    assert all(sha(ROOT/n)==h for n,h in read(E/'tests_final/continuation_source.json').items())
    old=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v5.md').read_text()
    new=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v6.md').read_text()
    for start,end in (('## 2.','## 3.'),('## 5.','## 6.'),('## 6.','## 7.')):
        assert old.split(start,1)[1].split(end,1)[0]==new.split(start,1)[1].split(end,1)[0]
    ledger=read(ROOT/'C4_Progress_Ledger_v1.json')
    assert len(ledger['cells'])==32 and not any(c['full_release_complete'] for c in ledger['cells'])
    groups=dict(sorted(collections.Counter(r['test_id'].split('.')[0] for r in t['rows']).items()))
    execution=dict(version='C4-v1',date='2026-09-23',python=sys.version,platform=platform.platform(),
        status='C4 bounded gate complete',milestones_complete=4,milestones_total=7,next='C5',full_release_cells_complete=0,
        tests=dict(total=554,groups=groups,run_form=t['run_form'],raw_log_passes_verified=True,
                   untimed_methods=sum(r['seconds'] is None for r in t['rows']),total_run_seconds=None),
        evidence=dict(tests='evidence_c4/tests_final',witnesses='evidence_c4/witnesses',measurements='evidence_c4/measurements',
                      verification='evidence_c4/delivery_verification.json',inspector='evidence_c4/inspector_qa.json'),
        counts=dict(circuit_type_cases=80,causal_pairs=7,raw_witnesses=15,recipe_continuation_configurations=24,
                    timing_workers=30,trace_workers=6),
        delivery_tools={str(q.relative_to(ROOT)):sha(q) for q in sorted((ROOT/'tools').glob('*c4*')) if q.is_file()},
        disclosure='Measurements ran after regression and witness export. Recorded method durations are diagnostic, not a performance benchmark. Inspector view logic checked without browser layout measurement.')
    write(ROOT/'C4_Execution_Manifest_v1.json',execution)
    write(E/'release_integrity.json',dict(passed=True,raw_test_log_coverage=554,continuation_source_verified=True,
        execution_source_manifests_verified=True,formal_map_contracts_and_nesting_spec_unchanged=True,
        full_release_cells_open=32,inspector_logic_passed=True))
    manifest_path=ROOT/'C4_Source_File_Manifest_v1.json'
    population=[q for q in files(ROOT) if q!=manifest_path]
    manifest=dict(version='C4-v1',excluded=['this manifest itself','__pycache__','*.pyc'],
        file_count=len(population),files={str(q.relative_to(ROOT)):dict(bytes=q.stat().st_size,sha256=sha(q)) for q in population})
    write(manifest_path,manifest)
    source_name='HLE_Full_Crux_C4_Source_v1'
    archive(a.out/(source_name+'.zip'),[(source_name+'/'+str(q.relative_to(ROOT)),q) for q in files(ROOT)])
    evidence_name='HLE_Full_Crux_C4_Evidence_v1'
    entries=[(evidence_name+'/'+str(q.relative_to(E)),q) for q in files(E)]
    for q in (manifest_path,ROOT/'C4_Execution_Manifest_v1.json',ROOT/'contracts/C4_Protocol_v1.json',ROOT/'contracts/C4_Review_Amendment_v1.json',ROOT/'docs/C4_Development_Record_v1.md'):
        entries.append((evidence_name+'/'+q.name,q))
    archive(a.out/(evidence_name+'.zip'),entries)
    names=['HLE_Full_Crux_C4_Report_v1.md','HLE_Full_Crux_C4_Inspector_v1.html','HLE_Full_Crux_Build_Specification_v6.md']
    for name in names:shutil.copyfile(ROOT/'docs'/name,a.out/name)
    delivered=[source_name+'.zip',evidence_name+'.zip',*names]
    checksums=dict(version='C4-v1',date='2026-09-23',status='Bounded C4 complete; C5–C7 remain open',
        sha256={name:sha(a.out/name) for name in delivered},bytes={name:(a.out/name).stat().st_size for name in delivered},
        source_file_manifest='C4_Source_File_Manifest_v1.json inside the source and evidence archives',
        archive_crc_verified=True)
    write(a.out/'HLE_Full_Crux_C4_Delivery_Checksums_v1.json',checksums)
    print(json.dumps(dict(saved_files=delivered+['HLE_Full_Crux_C4_Delivery_Checksums_v1.json'],source_files=manifest['file_count']+1,
                         source_bytes=(a.out/(source_name+'.zip')).stat().st_size,evidence_bytes=(a.out/(evidence_name+'.zip')).stat().st_size),indent=2))

if __name__=='__main__':main()
