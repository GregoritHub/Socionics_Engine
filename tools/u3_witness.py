"""Retain inspectable U3 access, sharing, partial processing and replay evidence."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from hle_unified import codec
from hle_unified.records import Definition, SourceStatus
from hle_unified.store import ObjectStore, next_version
from hle_unified.compact import CompactStore, VersionIndex
from hle_unified.particulars import AccessLedger, DetailAddress, Selector
from tests_u3.fixtures import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--u2-checkpoint", type=Path)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    world, access = setup()
    for actor in (ALICE.identity, BOB.identity):
        basics(access, actor)
    shared = (access.view(ALICE.identity).detail(DetailAddress("cue", "meaning")).value
        is access.view(BOB.identity).detail(DetailAddress("cue", "meaning")).value)
    first = bind(access, ALICE.identity, "alice-belief", meaning="Assistance threatens my control.", confidence=89)
    bind(access, BOB.identity, "bob-belief", meaning="Assistance can respect an agreement.", confidence=61)
    show_procedure(access, ALICE.identity)
    acquired = receipt(world, "acquisition", ALICE.identity, "acquire", "repair", (REPAIR, ROOM))
    access.acquire(ALICE.identity, REPAIR, ROOM, "repair", acquired)
    before = access.view(ALICE.identity)
    before_sequence = len(before.snapshot.history)
    snapshots = {"alice_before_hidden": before, "bob_before_hidden": access.view(BOB.identity)}
    decisions = {"before_hidden": choose(before)}
    world.transfer("hidden-transfer", WRITER, SAW, BOB.identity, actor=ALICE.identity)
    world.revise("hidden-anchor-revision", WRITER, next_version(world.resolve(CUE),
        facets=(Definition("Later wording, still undelivered to either participant.", SourceStatus.ENGINEERING),)))
    snapshots["alice_after_hidden"] = access.view(ALICE.identity)
    decisions["after_hidden"] = choose(snapshots["alice_after_hidden"])
    disclose(access, ALICE.identity, "new-owner", ref("saw", 2),
        (Selector("owner", "ownership", ("facets", "0", "owner")),), completed=1)
    partial = access.checkpoint()
    (out / "situated.partial.checkpoint.json").write_text(partial)
    snapshots["alice_partial_processing"] = access.view(ALICE.identity)
    decisions["partial_processing"] = choose(snapshots["alice_partial_processing"])
    continued = AccessLedger.restore(partial)
    # Apply the same continuation on the original and restored states.
    for ledger in (access, continued):
        work = receipt(ledger.world, "read-final", ALICE.identity, "read", "new-owner", (ref("saw", 2),))
        ledger.process(ALICE.identity, "new-owner", work)
        bind(ledger, ALICE.identity, "alice-belief", addresses=(DetailAddress("new-owner", "owner"),),
            meaning="The tool now belongs to Bob; assistance needs agreed terms.", confidence=68, previous=first)
    snapshots["alice_after_processing"] = access.view(ALICE.identity)
    snapshots["bob_after_processing"] = access.view(BOB.identity)
    decisions["after_processing"] = choose(snapshots["alice_after_processing"])
    saved = access.checkpoint()
    (out / "situated.completed.checkpoint.json").write_text(saved)
    (out / "native.compact.checkpoint.json").write_text(world.checkpoint())
    (out / "native.full_reference.checkpoint.json").write_text(world.canonical_checkpoint())
    (out / "native.transactions.jsonl").write_text("\n".join(codec.dumps(t) for t in world.journal()) + "\n")
    for name, view in snapshots.items():
        (out / (name + ".json")).write_text(json.dumps(asdict(view.snapshot), indent=2) + "\n")
        (out / (name + ".exact.json")).write_text(view.bytes())
    (out / "decisions.json").write_text(json.dumps(decisions, indent=2) + "\n")
    full = ObjectStore.restore(world.canonical_checkpoint())
    restored = AccessLedger.restore(saved)
    checks = {
        "physical_shared_definition": shared,
        "independent_interpretations": snapshots["alice_before_hidden"].snapshot.bindings[0].meaning != snapshots["bob_before_hidden"].snapshot.bindings[0].meaning,
        "no_shared_acquisition": snapshots["alice_before_hidden"].can_use(REPAIR, ROOM) and not snapshots["bob_before_hidden"].can_use(REPAIR, ROOM),
        "hidden_view_equal": before.bytes() == snapshots["alice_after_hidden"].bytes(),
        "hidden_decision_and_reasons_equal": decisions["before_hidden"] == decisions["after_hidden"],
        "partial_processing_no_new_owner_decision": decisions["partial_processing"] == decisions["before_hidden"],
        "completed_processing_changes_choice": decisions["after_processing"]["choice"] == "request-use",
        "other_actor_unchanged": snapshots["bob_before_hidden"].bytes() == snapshots["bob_after_processing"].bytes(),
        "old_definition_meaning_retained": snapshots["alice_after_processing"].detail(DetailAddress("cue", "meaning")).value == world.resolve(CUE).facet(Definition),
        "original_binding_retained": restored.world.resolve(first) == world.resolve(first),
        "exact_historical_actor_view": restored.view(ALICE.identity, through=before_sequence).bytes() == before.bytes(),
        "exact_situated_replay": restored.checkpoint() == saved,
        "exact_partial_continuation": continued.checkpoint() == saved,
        "full_snapshot_reference_agrees": CompactStore.from_store(full).checkpoint() == world.checkpoint(),
    }
    if args.u2_checkpoint:
        text = args.u2_checkpoint.read_text()
        u2 = ObjectStore.restore(text)
        u3 = CompactStore.from_store(u2)
        (out / "u2_native_reencoded.compact.json").write_text(u3.checkpoint())
        checks["complete_u2_native_witness_reconstructs"] = CompactStore.restore(u3.checkpoint()).canonical_checkpoint() == text
    compact_text, full_text = world.checkpoint(), world.canonical_checkpoint()
    sizes = {"compact_raw": len(compact_text.encode()), "full_raw": len(full_text.encode()),
        "compact_gzip": len(gzip.compress(compact_text.encode(), mtime=0)),
        "full_gzip": len(gzip.compress(full_text.encode(), mtime=0)),
        "version_rows": len(world._versions.rows), "stored_delta_fields": sum(len(v[1]) for v in world._versions.rows.values()),
        "full_snapshot_equivalent_fields": len(world._versions.rows) * len(VersionIndex.NAMES),
        "world_structural_nodes": len(world.pool.nodes), "access_structural_nodes": len(access.pool.nodes)}
    manifest = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(out.iterdir()) if p.is_file()}
    summary = {"schema": "hle-unified-u3-witness-v1", "passed": all(checks.values()), "checks": checks,
        "sizes": sizes, "files": manifest,
        "scope": "Declared deterministic fixture. Processing/acquisition receipts are imported fixture evidence; U4 execution and U13 performance acceptance remain open."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
