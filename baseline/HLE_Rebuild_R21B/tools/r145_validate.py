"""Inherited behavioral gates plus declared R14.5 integration tests."""
import sys,subprocess,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'evidence/r145/validation'
    out.mkdir(parents=True,exist_ok=True)
    baseline=subprocess.run([sys.executable,'tools/r14_validate.py','--out',str(out/'inherited')],cwd=ROOT)
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r145','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    text=tests.stdout+tests.stderr;(out/'r145.log').write_text(text)
    match=re.search(r'Ran (\d+) tests',text);count=int(match.group(1)) if match else 0
    inherited=json.loads((out/'inherited/summary.json').read_text())
    report={'passed':baseline.returncode==0 and tests.returncode==0 and count==28 and text.rstrip().endswith('OK'),
        'inherited_tests':inherited['distinct_tests'],'r145_tests':count,'total':inherited['distinct_tests']+count}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
