#!/usr/bin/env python3
"""Replay the bounded R9 lifecycle with the predeclared ample resource levels."""
import argparse,json,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.organization import OrganizationWorld
from hle.organization_demo import run_organization_demo
from hle.contracts import WorkStatus


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    base,summary,_=run_organization_demo();rows=[]
    for amount in (5000,20000):
        cfg=replace(base.config,wallets=tuple(replace(x,energy=amount,time=amount) for x in base.config.wallets))
        w=OrganizationWorld(cfg,base.profiles,base.policy,base.agents,base.organization_policies)
        for tx in base._journal[1:]:
            w.execute(tx.command)
            assert w._journal[-1].event.outcome==tx.event.outcome
            assert getattr(w._journal[-1],'extra',())==getattr(tx,'extra',())
        rows.append({'initial_energy_and_time_per_actor':amount,'events':len(w._journal),
            'same_local_decisions_and_physical_outcomes':True,'remaining_energy':{a.key:w._wallets[a].energy for a in cfg.actors}})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'scope':'two ample-resource command replays; zero/one-unit shortage and continuation controls are unit tests; not R10 resource robustness','cases':rows},indent=2)+'\n')
    print(json.dumps({'resource_cases':len(rows),'passed':True}))

if __name__=='__main__':main()
