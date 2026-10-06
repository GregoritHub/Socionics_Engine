"""Inspect a restored U5 participant view or independently audit its raw history."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from hle_unified.cognition import CognitiveEngine
from hle_unified.cognitive_audit import audit

parser = argparse.ArgumentParser()
parser.add_argument("checkpoint", type=Path)
parser.add_argument("--actor")
args = parser.parse_args()
engine = CognitiveEngine.restore(args.checkpoint.read_text())
if args.actor:
    candidates = [a for a in engine._wallets if a.key == args.actor]
    if len(candidates) != 1:
        parser.error("actor key must identify exactly one participant")
    print(engine.participant_view(candidates[0]).bytes())
else:
    print(json.dumps(audit(engine.world.journal()), indent=2))
