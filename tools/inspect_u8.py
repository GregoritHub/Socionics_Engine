"""Inspect owned development; optional offline assessment is explicitly separate."""
import argparse
from dataclasses import asdict,is_dataclass
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from hle_unified.development import DevelopmentEngine
from hle_unified.development_assessment import assess


def main():
    p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('--actor',default='alice');p.add_argument('--assess',action='store_true')
    args=p.parse_args();e=DevelopmentEngine.restore(args.checkpoint.read_text())
    actors=[a for a in e._profiles if a.key==args.actor]
    if len(actors)!=1:raise ValueError('unique actor key required')
    result={'actor_development':e.development_view(actors[0])}
    if args.assess:result['offline_assessment']=assess(e.world.journal())
    print(json.dumps(result,indent=2,default=lambda o:asdict(o) if is_dataclass(o) else str(o)))


if __name__=='__main__':main()
