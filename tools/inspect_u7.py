"""Inspect a saved actor's own attributions; optional separate offline assessment."""
import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from hle_unified.shell import ShellEngine
from hle_unified.records import ObjectId
from hle_unified.shell_assessment import assess


def main():
    p=argparse.ArgumentParser(); p.add_argument('checkpoint',type=Path); p.add_argument('--actor',default='alice')
    p.add_argument('--assess',action='store_true',help='Include separate evaluator output, never fed to the actor')
    args=p.parse_args(); e=ShellEngine.restore(args.checkpoint.read_text())
    actor=ObjectId('workshop',args.actor)
    result={'actor':actor,'attributions':e.pattern_view(actor),
        'situated_bindings':e.participant_view(actor).snapshot.bindings,
        'energy':e.wallet(actor)['energy'],'time':e.wallet(actor)['time']}
    if args.assess:result['offline_evaluator']=assess(e.world.journal())
    print(json.dumps(result,indent=2,default=lambda o:asdict(o) if is_dataclass(o) else str(o)))


if __name__=='__main__':main()
