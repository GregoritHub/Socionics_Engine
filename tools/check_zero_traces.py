"""Audit zero-budget raw traces without counting new experimental episodes."""
import argparse
import gzip
import json
from pathlib import Path

def audit(directory):
    rows = []
    for tim, seed in (("iee", 12), ("sli", 11)):
        for suffix in ("", ".independent"):
            path = directory / f"{tim}_{seed}_inadequate{suffix}.transactions.jsonl.gz"
            with gzip.open(path, "rt") as stream:
                transactions = [json.loads(line) for line in stream]
            records = []
            def visit(value):
                if isinstance(value, dict):
                    if "record" in value:
                        records.append(value["record"])
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(transactions)
            acquisitions = [name for name in records if "Capacity" in name or "Acquisition" in name]
            rows.append({"case": f"{tim}_{seed}_inadequate",
                         "side": "independent" if suffix else "candidate",
                         "raw_transactions": len(transactions), "acquisition_records": acquisitions,
                         "passed": len(transactions) == 3 and not acquisitions})
    return {"schema": "u1-zero-budget-raw-check-v1",
            "scope": "Direct structural scan of four existing zero-budget raw journals; supplementary readout, not additional episodes.",
            "rows": rows, "passed": all(row["passed"] for row in rows)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.traces)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "journals_checked": len(result["rows"])}))
    raise SystemExit(0 if result["passed"] else 1)

