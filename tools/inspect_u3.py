"""Offline inspector for a situated checkpoint; never passed to a policy."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from hle_unified.particulars import AccessLedger
from hle_unified.records import ObjectId

parser = argparse.ArgumentParser()
parser.add_argument("checkpoint", type=Path)
parser.add_argument("--actor", required=True)
parser.add_argument("--namespace", default="workshop")
parser.add_argument("--through", type=int)
args = parser.parse_args()
ledger = AccessLedger.restore(args.checkpoint.read_text())
view = ledger.view(ObjectId(args.namespace, args.actor), through=args.through)
print(json.dumps(asdict(view.snapshot), indent=2))
