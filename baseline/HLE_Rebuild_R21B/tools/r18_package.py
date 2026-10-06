"""Deterministic R18 source package with exact complete file manifest."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args();dest=a.archive.resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    files=sorted(x for x in ROOT.rglob('*') if x.is_file() and '__pycache__' not in x.parts
        and x.suffix not in ('.pyc','.pyo') and x!=ROOT/'release_manifest.json' and x.resolve()!=dest)
    manifest=ROOT/'release_manifest.json'
    manifest.write_text(json.dumps({'milestone':'R18','version':'1.8.0','parent_R18_complete':True,
        'files':[{'path':str(x.relative_to(ROOT)),'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in files]},indent=2)+'\n')
    with ZipFile(dest,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for x in sorted(files+[manifest]):
            info=ZipInfo('HLE_Rebuild_R18/'+str(x.relative_to(ROOT)),date_time=(2026,9,18,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,x.read_bytes())
    with ZipFile(dest) as z:
        if z.testzip():raise ValueError('archive CRC failed')
    print(json.dumps({'archive':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'manifest_files':len(files)}))
if __name__=='__main__':main()
