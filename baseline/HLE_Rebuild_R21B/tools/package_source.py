#!/usr/bin/env python3
"""Package this source deterministically, excluding execution byproducts."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def source_files():
    paths=[ROOT/'README.md']
    for folder in ('hle','tests','tools','docs','reference'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    return sorted(paths)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path)
    args=parser.parse_args();args.archive.parent.mkdir(parents=True,exist_ok=True)
    paths=source_files()
    manifest={'milestone':'R11','version':'1.1.0','files':[
        {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
         'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    manifest_path=ROOT/'release_manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    with ZipFile(args.archive,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(paths+[manifest_path]):
            info=ZipInfo('HLE_Rebuild_R11/'+str(p.relative_to(ROOT)),date_time=(2026,9,17,0,0,0))
            info.compress_type=ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes())
    with ZipFile(args.archive) as z:
        bad=z.testzip()
        if bad:raise ValueError('damaged archive member: '+bad)
    print(json.dumps({'archive':str(args.archive.resolve()),'members':len(paths)+1,
        'bytes':args.archive.stat().st_size,'sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
