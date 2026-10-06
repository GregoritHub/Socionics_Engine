#!/usr/bin/env python3
"""Standard-library reproduction. Engine releases run in separate processes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',choices=['r10','r11']);p.add_argument('--out',default='results')
    a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    if not a.worker:
        for release in ('r10','r11'):
            subprocess.run([sys.executable,str(__file__),'--worker',release,'--out',str(out)],check=True,timeout=180)
        return
    engine=ROOT/'vendor'/a.worker
    sys.path.insert(0,str(engine))
    from probes.common import write_json
    from probes import active_probe,study_a,study_b
    import hle
    print(a.worker,'active-element probe',flush=True)
    active=active_probe.run(engine)
    print(a.worker,'policy study and coverage controls',flush=True)
    sa=study_a.run()
    print(a.worker,'attention matrix and history controls',flush=True)
    sb=study_b.run()
    write_json(out/(a.worker+'.json'),{'release':hle.__version__,
        'protocol_sha256':hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest(),
        'active_probe':active,'study_a':sa,'study_b':sb})
    print(a.worker,'complete',flush=True)


if __name__=='__main__':main()
