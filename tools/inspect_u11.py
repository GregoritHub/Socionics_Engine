"""Inspect received collective facts; optional audit is strictly read-only."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from hle_unified.collective import CollectiveEngine
from hle_unified import codec
from inspect_u10 import readable


def main():
    p=argparse.ArgumentParser();p.add_argument("checkpoint",type=Path)
    p.add_argument("--actor",default="alice");p.add_argument("--assess",action="store_true")
    args=p.parse_args();e=CollectiveEngine.restore(args.checkpoint.read_text())
    actors=[a for a in e._wallets if a.key==args.actor]
    if len(actors)!=1:raise ValueError("actor name is absent or ambiguous")
    view=e.participant_view(actors[0]);received={}
    for item in view.snapshot.particulars:
        if item.source.identity.namespace.startswith("u11.") and item.address.key=="payload":
            d=dict(codec.loads(item.value));prior=received.get(item.source.identity)
            if prior is None or prior["ref"].revision<d["ref"].revision:received[item.source.identity]=d
    result={"actor":args.actor,"received_collective_records":readable(list(received.values())),
        "own_acquired_procedures":readable([x.procedure for x in view.snapshot.acquired]),
        "pending_deliveries":len(view.snapshot.pending),
        "note":"These are received historical accounts. Internal invalidation cannot refresh them."}
    if args.assess:
        from hle_unified.collective_audit import audit
        result["offline_assessment"]=audit(e.world.journal())
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
