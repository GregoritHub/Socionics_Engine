#!/usr/bin/env python3
"""Validate release bytes and original stack fixture without executing legacy code."""
import ast
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/'release_manifest.json').read_text())
    failures=[]
    for item in manifest['files']:
        path=ROOT/item['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            failures.append(item['path'])
    with ZipFile(ROOT/'reference/originals/HolonicLivingEngine5_2_1_canon.zip') as z:
        tree=ast.parse(z.read('clean/pyref/core.py').decode())
    stacks=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='DEFINITIVE_STACKS' for t in node.targets))
    if stacks!=json.loads((ROOT/'tests/stack_fixture.json').read_text()):failures.append('stack fixture differs from original')
    print(json.dumps({'files_checked':len(manifest['files']),'failures':failures,'passed':not failures}))
    return 1 if failures else 0


if __name__=='__main__':raise SystemExit(main())
