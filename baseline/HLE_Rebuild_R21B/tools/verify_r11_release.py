#!/usr/bin/env python3
"""Verify R11 release manifest, acceptance results, and evaluated source identity."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tests',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    tests=json.loads(args.tests.read_text()); env=json.loads((args.evidence/'environment.json').read_text())
    summary=json.loads((args.evidence/'summary.json').read_text())
    manifest=json.loads((ROOT/'release_manifest.json').read_text())
    inherited=json.loads((ROOT/'docs/inherited_R10_sha256.json').read_text())
    declaration=json.loads((ROOT/'docs/acceptance_plan_R11.json').read_text())
    failures=[]
    for row in manifest['files']:
        if sha(ROOT/row['path'])!=row['sha256']: failures.append({'manifest_mismatch':row['path']})
    if not tests['successful'] or tests['tests_run']!=353: failures.append('353 passing tests required')
    if not summary['passed'] or summary['cases']!=24: failures.append('R11 panel not accepted')
    if sha(ROOT/'docs/r11/acceptance.md')!=declaration['declaration_sha256']: failures.append('declaration changed')
    if env['plan_sha256']!=sha(ROOT/'docs/acceptance_plan_R11.json'): failures.append('panel plan mismatch')
    # Only these files execute in the panel. CLI/report/release tooling changes do
    # not affect recorded simulation or oracle behavior; full suite uses final bytes.
    footprint=[p for p in env['source_hashes'] if p.startswith('hle/') and p!='hle/__main__.py']
    footprint+=['tools/r11_evidence.py','tools/r11_workloads.py','tools/r11_controls.py',
        'tools/r11_oracle.py','tools/r10_oracle.py','tests/reference_processing.py','tests/stack_fixture.json',
        'docs/r11/acceptance.md','docs/acceptance_plan_R11.json']
    for name in footprint:
        if sha(ROOT/name)!=env['source_hashes'][name]: failures.append({'evaluated_source_mismatch':name})
    for name,digest in tests['source_hashes'].items():
        if name.startswith(('hle/','tests/')) and sha(ROOT/name)!=digest:
            failures.append({'tested_source_mismatch':name})
    edited_tests={'tests/test_language.py','tests/test_organization.py','tests/test_composition.py'}
    changed_tests=[]; references=0
    for name,digest in inherited.items():
        if name.startswith('reference/'):
            references+=1
            if sha(ROOT/name)!=digest: failures.append({'governing_reference_changed':name})
        if name.startswith('tests/') and sha(ROOT/name)!=digest:
            changed_tests.append(name)
            if name not in edited_tests: failures.append({'undocumented_inherited_test_change':name})
    journals=[]
    for row in json.loads((args.evidence/'main-panel.json').read_text()):
        h=hashlib.sha256()
        with gzip.open(args.evidence/row['journal_file'],'rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
        if h.hexdigest()!=row['checkpoint']['sha256']: failures.append({'journal_mismatch':row['case']})
        journals.append(row['case'])
    result={'milestone':'R11','gate':'M07','passed':not failures,'failures':failures,
        'tests':tests['tests_run'],'historical_tests':340,'new_tests':13,
        'modified_inherited_test_files':sorted(changed_tests),'unchanged_governing_files':references,
        'manifest_files':len(manifest['files']),'verified_journals':len(journals),
        'evaluated_files_verified':len(footprint),'panel_gates':summary['gates'],
        'declaration_sha256':declaration['declaration_sha256'],
        'provenance_scope':'All simulation modules except the unexecuted CLI; exact panel/workload/controls/oracles and positional fixture. Final tests checked against all delivered runtime/tests.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
    return 0 if result['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
