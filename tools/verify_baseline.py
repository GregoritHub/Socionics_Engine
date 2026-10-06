"""Verify every frozen baseline member and its original release manifest."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def verify():
    manifest = json.loads((ROOT / "contracts/Input_Manifest.json").read_text())
    failures = []
    for row in manifest["members"]:
        path = ROOT / "baseline" / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            failures.append(row["path"])
    baseline = ROOT / "baseline/HLE_Rebuild_R21B"
    original = json.loads((baseline / "release_manifest.json").read_text())
    digest = hashlib.sha256()
    for path in sorted((baseline / "hle").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(sha(path)))
    protocol = ROOT / "contracts/U1_Protocol_v1.json"
    expected_protocol = (ROOT / "contracts/U1_Protocol_v1.sha256").read_text().split()[0]
    result = {"schema": "u1-frozen-baseline-verification-v1",
              "members_checked": len(manifest["members"]),
              "runtime_modules": len(list((baseline / "hle").glob("*.py"))),
              "legacy_runtime_sha256": digest.hexdigest(),
              "legacy_digest_matches": digest.hexdigest() == original["runtime_sha256"],
              "u1_protocol_digest_matches": sha(protocol) == expected_protocol,
              "failures": failures}
    result["passed"] = not failures and result["legacy_digest_matches"] and result["u1_protocol_digest_matches"]
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    raise SystemExit(0 if result["passed"] else 1)

