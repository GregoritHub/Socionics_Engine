"""Full inherited compatibility plus R21A contract controls."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT/'evidence/r21a/validation')
    args = parser.parse_args();out = args.out.resolve();out.mkdir(parents=True, exist_ok=True)
    prior = subprocess.run([sys.executable, 'tools/r20_validate.py', '--out', str(out/'inherited')], cwd=ROOT)
    inherited = json.loads((out/'inherited/summary.json').read_text())
    suites = []
    for directory in ('tests_r21', 'tests_r21a'):
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-t', '.', '-v'],
                             cwd=ROOT, capture_output=True, text=True)
        log = run.stdout+run.stderr;(out/(directory+'.log')).write_text(log)
        match = re.search(r'Ran (\d+) tests', log)
        suites.append({'suite': directory, 'count': int(match.group(1)) if match else 0,
                       'passed': run.returncode==0 and log.rstrip().endswith('OK')})
        print(json.dumps(suites[-1]), flush=True)
    result = {'schema': 'r21a-validation-v1', 'inherited_through_r20': inherited['total'],
        'suites': suites, 'total': inherited['total']+sum(s['count'] for s in suites),
        'passed': prior.returncode==0 and inherited['passed'] and inherited['total']==859
                  and all(s['passed'] for s in suites)}
    (out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':raise SystemExit(main())
