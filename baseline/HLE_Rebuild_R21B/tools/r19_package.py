"""Deterministic R19 source package and exact file manifest."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args();dest=a.archive.resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    files=sorted(f for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in f.parts
        and f.suffix not in ('.pyc','.pyo') and f!=ROOT/'release_manifest.json' and f.resolve()!=dest)
    manifest=ROOT/'release_manifest.json'
    manifest.write_text(json.dumps({'milestone':'R19','version':'1.9.0','parent_R19_complete':True,
        'files':[{'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files]},indent=2)+'\n')
    with ZipFile(dest,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(files+[manifest]):
            info=ZipInfo('HLE_Rebuild_R19/'+str(f.relative_to(ROOT)),date_time=(2026,9,18,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,f.read_bytes())
    with ZipFile(dest) as z:
        if z.testzip():raise ValueError('source archive CRC failure')
        for row in json.loads(z.read('HLE_Rebuild_R19/release_manifest.json'))['files']:
            data=z.read('HLE_Rebuild_R19/'+row['path'])
            if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('source manifest mismatch')
    print(json.dumps({'archive':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'manifest_files':len(files),'verified':True}))
if __name__=='__main__':main()
