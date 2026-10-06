"""Inspect a U9 checkpoint's owned constructive work and optional offline audit."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from hle_unified.composition import CompositionEngine
from hle_unified import codec


def readable(value):
    if isinstance(value,tuple):return [readable(x) for x in value]
    if isinstance(value,dict):return {k:readable(v) for k,v in value.items()}
    if hasattr(value,"identity"):return {"namespace":value.identity.namespace,"key":value.identity.key,"revision":value.revision}
    if hasattr(value,"namespace"):return {"namespace":value.namespace,"key":value.key}
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument("checkpoint",type=Path);p.add_argument("--actor",default="alice");p.add_argument("--assess",action="store_true")
    args=p.parse_args();e=CompositionEngine.restore(args.checkpoint.read_text())
    actors=[a for a in e._wallets if a.key==args.actor]
    if len(actors)!=1:raise ValueError("actor name is absent or ambiguous")
    rows=e.composition_view(actors[0])
    print(json.dumps({"actor":args.actor,"owned_work":[readable({k:v for k,v in r.items() if k in
        ("ref","kind","status","program","goal","guard","split","trace","index","remaining","considered","depth","reason","failure_kind")}) for r in rows]},indent=2))
    if args.assess:
        from hle_unified.composition_audit import audit
        print(json.dumps({"offline_assessment":audit(e.world.journal())},indent=2))


if __name__=="__main__":main()
