"""Inspect a U6 checkpoint, including participant-owned continuation state."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.autonomy import AutonomousEngine
from hle_unified.autonomy_audit import audit


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('checkpoint',type=Path)
    parser.add_argument('--actor')
    args=parser.parse_args()
    engine=AutonomousEngine.restore(args.checkpoint.read_text())
    if args.actor:
        actors=[a for a in engine._configs if a.key==args.actor]
        if len(actors)!=1:raise ValueError('one configured actor must match')
        a=actors[0]
        result={'state':asdict(engine.state(a)),'wallet':engine.wallet(a),
            'processed_particulars':len(engine.participant_view(a).snapshot.particulars),
            'acquired_procedures':len(engine.participant_view(a).snapshot.acquired)}
        result['wallet'].pop('actor',None)
    else:
        result=audit(engine.world.journal())
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
