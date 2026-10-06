#!/usr/bin/env python3
"""Run the current finite-content and retained-capacity experiment on R11."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor" / "r11"))
from experiments.crossing import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "crossing.json")
    args = parser.parse_args()
    data = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"Content identity: {data['content_identity']['stable_pairs']}/{data['content_identity']['matched_pairs']} matched pairs stable")
    for row in data["conditions"]:
        print(f"{row['condition']}: {row['successes']}/{row['held_out_trials']} successful returns; {row['assessment']['status']}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
