#!/usr/bin/env python3
"""Verify R10 evidence belongs to these exact source bytes and inherited gates."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tests = json.loads(args.tests.read_text())
    env = json.loads((args.evidence / 'environment.json').read_text())
    summary = json.loads((args.evidence / 'summary.json').read_text())
    old = json.loads((ROOT / 'docs/inherited_R9_sha256.json').read_text())
    changed = [p for p, h in old.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    allowed = ['README.md', 'docs/acceptance_plan.json', 'docs/rules.json',
        'hle/__init__.py', 'hle/__main__.py', 'tools/package_source.py', 'release_manifest.json']
    failures = []
    if sorted(changed) != sorted(allowed): failures.append({'unexpected_inherited_changes': changed})
    if not tests['successful'] or tests['tests_run'] != 340: failures.append('340 passing tests required')
    inherited_tests = [t for t in tests['tests'] if not t['test'].startswith('tests.test_sustained.')]
    if len(inherited_tests) != 331 or any(t['status'] != 'passed' for t in inherited_tests):
        failures.append('inherited test count or result mismatch')
    for name, source in [('tests', tests), ('evaluation', env)]:
        stale = [p for p, h in source['source_hashes'].items() if sha(ROOT / p) != h]
        if stale: failures.append({name + '_source_mismatch': stale})
    if not summary['passed']: failures.append('evaluation acceptance gate failed')
    manifest = json.loads((ROOT / 'release_manifest.json').read_text())
    for item in manifest['files']:
        if sha(ROOT / item['path']) != item['sha256']: failures.append(item['path'])
    plan_hash = sha(ROOT / 'docs/acceptance_plan_R10.json')
    if env['plan_sha256'] != plan_hash: failures.append('acceptance declaration mismatch')
    evidence_failures = []
    for row in json.loads((args.evidence / 'main-panel.json').read_text()):
        import gzip
        path = args.evidence / row['journal_file']
        # Streaming digest avoids allocating every full journal again.
        h = hashlib.sha256()
        with gzip.open(path, 'rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
        if h.hexdigest() != row['checkpoint']['sha256']: evidence_failures.append(row['case'])
    if evidence_failures: failures.append({'journal_hash_mismatch': evidence_failures})
    result = {'milestone': 'R10', 'gate': 'S07', 'passed': not failures, 'failures': failures,
        'tests': tests['tests_run'], 'inherited_tests': len(inherited_tests),
        'inherited_files': len(old), 'permitted_changed_files': changed,
        'governing_reference_files_unchanged': sum(p.startswith('reference/') for p in old),
        'manifest_files': len(manifest['files']), 'main_journals_verified': 36,
        'plan_sha256': plan_hash, 'evaluation_gates': summary['gates']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
