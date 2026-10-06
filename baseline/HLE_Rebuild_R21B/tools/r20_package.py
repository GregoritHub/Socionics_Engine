"""Deterministic R20 source/evidence archives with verified byte manifests."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_archive(dest,entries,prefix):
    dest.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(dest,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(entries):
            info=ZipInfo(prefix+'/'+name,date_time=(2026,9,18,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,path.read_bytes())
    with ZipFile(dest) as z:
        if z.testzip():raise ValueError('archive CRC failure')
        for name,path in entries:
            if hashlib.sha256(z.read(prefix+'/'+name)).hexdigest()!=sha(path):raise ValueError('archive bytes differ: '+name)
    return {'archive':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'files':len(entries),'verified':True}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if not json.loads((ROOT/'evidence/r20/validation/summary.json').read_text())['passed']:raise ValueError('validation gate open')
    if not json.loads((ROOT/'evidence/r20/panel/summary.json').read_text())['passed']:raise ValueError('panel gate open')
    keep=lambda f:f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.pyo')
    entries=[]
    for folder in ('evidence/r20','docs/r20','tests_r20'):
        entries.extend((str(f.relative_to(ROOT)),f) for f in sorted((ROOT/folder).rglob('*')) if keep(f))
    entries.extend(('runtime/'+f.name,f) for f in sorted((ROOT/'hle').glob('*.py')))
    entries.extend(('tools/'+f.name,f) for f in sorted((ROOT/'tools').glob('r20_*.py')))
    for name in ('Plan_v1.md','acceptance_v1.json','source_ledger_v1.json'):
        f=ROOT/'docs/r12'/name
        if f.exists():entries.append(('frozen_parent/'+name,f))
    em=ROOT/'evidence/r20/evidence_manifest.json'
    entries=[pair for pair in entries if pair[1]!=em]
    em.write_text(json.dumps({'schema':'r20-evidence-package-v1','files':[{'path':name,'bytes':f.stat().st_size,'sha256':sha(f)} for name,f in sorted(entries)]},indent=2)+'\n')
    files=sorted(f for f in ROOT.rglob('*') if keep(f) and f!=ROOT/'release_manifest.json')
    manifest={'milestone':'R20','version':'1.10.0','parent_R20_complete':True,'remaining':['R21'],
        'files':[{'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]}
    m=ROOT/'release_manifest.json';m.write_text(json.dumps(manifest,indent=2)+'\n')
    source=write_archive(out/'HolonicLivingEngine_Rebuild_R20_v1.zip',[(str(f.relative_to(ROOT)),f) for f in files+[m]],'HLE_Rebuild_R20')
    evidence=write_archive(out/'HLE_New_Build_Step_R20_Evidence_v1.zip',entries+[('evidence_manifest.json',em)],'HLE_R20_Evidence')
    print(json.dumps({'source':source,'evidence':evidence},indent=2))
if __name__=='__main__':main()
