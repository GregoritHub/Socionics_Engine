#!/usr/bin/env python3
"""Check the shipped engine bytes against pinned upstream manifest hashes."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    provenance=json.loads((ROOT/'sources/provenance.json').read_text())
    checked=0
    for release in ('r10','r11'):
        pin=provenance[release]
        manifest=ROOT/'sources'/(release+'_release_manifest.json')
        assert hashlib.sha256(manifest.read_bytes()).hexdigest()==pin['release_manifest_sha256']
        upstream={x['path']:x['sha256'] for x in json.loads(manifest.read_text())['files']}
        for name,expected in pin['modules'].items():
            path=ROOT/name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
            assert upstream['hle/'+path.name]==expected,name
            checked+=1
        assert {str(p.relative_to(ROOT)) for p in (ROOT/'vendor'/release/'hle').glob('*.py')}==set(pin['modules'])
    original=ROOT/'sources/active_element_probe_original.py'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==provenance['input_hashes'][original.name]
    print(f'Verified {checked} original runtime modules, two release manifests, and the original active-element probe.')


if __name__=='__main__':main()
