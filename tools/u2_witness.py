"""Save inspectable deterministic native and legacy U2 witnesses.

These are structural development fixtures, not a population experiment, a new
paid-work policy, or evidence of autonomous institution formation.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "baseline/HLE_Rebuild_R21B"
sys.path[:0] = [str(ROOT), str(BASE), str(BASE / "tools")]
sys.dont_write_bytecode = True

from hle_unified import codec, legacy
from hle_unified.records import (
    ObjectVersion, Role, Relation, Endpoint, Attribute, Account, Occurrence,
    Definition, SourceStatus, Memory, Governance, Composition, Material, Attitude,
    Assessment, EvidenceStatus, ClaimStatus, Moment, TimeScope, Proposition)
from hle_unified.store import ObjectStore, next_version
from tests_u2.fixtures import base, bowl, event, ref, ident, ALICE, BOB, ROOM, RULE, LAW, UNIT, WRITER, active_quantities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    s = base()
    left, right, stock = bowl("left"), bowl("right"), bowl("stock", 12)
    s.create("material", WRITER, (left, right, stock))
    origin = event("agreement", referent=left.ref)
    s.create("event", WRITER, (origin,))
    relation = Relation("owes_return", (Endpoint("debtor", ALICE), Endpoint("creditor", BOB), Endpoint("item", left.ref)),
        True, ROOM, TimeScope(Moment(1, 0), Moment(9, 0)), (Attribute("deadline", 9),))
    obligation = ObjectVersion(ref("obligation"), WRITER, "Return the identified bowl", (Role.RELATION, Role.COMMITMENT), (relation,), definition=RULE)
    s.create("obligation", WRITER, (obligation,), evidence=(origin.ref,))
    revised_obligation = next_version(obligation, facets=(replace(relation,
        scope=TimeScope(Moment(1, 0), Moment(12, 0)), terms=(Attribute("deadline", 12),)),))
    s.revise("deadline", WRITER, revised_obligation, evidence=(origin.ref,), reason="Explicit fixture extension of the obligation")
    s.transfer("give-left", WRITER, left.ref, BOB.identity, actor=ALICE.identity, evidence=(origin.ref,))
    old_memory = ObjectVersion(ref("memory"), "actor.alice", "Original rule account", (Role.CLAIM,),
        (Account(RULE, (), Moment(2, 0), ALICE.identity, (origin.ref,)),), occurrence=Occurrence.REMEMBERED_CLAIM)
    s.create("remember", "actor.alice", (old_memory,), actor=ALICE.identity)
    old_rule = s.resolve(RULE)
    s.revise("revise-rule", WRITER, next_version(old_rule, facets=(Definition("Return before tick 5.", SourceStatus.ENGINEERING),)), reason="Prospective definition revision")
    false = Proposition(right.ref, "condition", "broken", ROOM, TimeScope(Moment(8, 0), None))
    prediction = ObjectVersion(ref("prediction"), "actor.alice", "Prediction that remains hypothetical", (Role.CLAIM,),
        (Account(right.ref, (false,), Moment(3, 0), ALICE.identity),), occurrence=Occurrence.HYPOTHETICAL)
    s.create("predict", "actor.alice", (prediction,), actor=ALICE.identity)
    stance = ObjectVersion(ref("endorsement"), "actor.alice", "Personal endorsement", (Role.ATTITUDE,),
        (Attitude(ALICE.identity, prediction.ref, ClaimStatus.ENDORSED, 100),))
    s.create("endorse", "actor.alice", (stance,), actor=ALICE.identity)
    inspection = event("inspection", at=8, referent=right.ref, content=(replace(false, object="intact"),))
    s.create("actual-inspection", WRITER, (inspection,))
    judgment = ObjectVersion(ref("assessment"), "evaluator", "Contradicted forecast", (Role.ASSESSMENT,),
        (Assessment(prediction.ref, "factual_agreement", EvidenceStatus.FAILED, (inspection.ref,), "Declared inspection at forecast time reports intact condition."),))
    s.create("assess", "evaluator", (judgment,))
    a, b = bowl("part-a", 5), bowl("part-b", 7)
    s.restructure("divide", WRITER, (stock.ref,), (a, b), actor=ALICE.identity, rule=LAW, reason="Divide twelve into five and seven")
    joined = bowl("joined", 12)
    s.restructure("combine", WRITER, (a.ref, b.ref), (joined,), actor=ALICE.identity, rule=LAW, reason="Recombine owned quanta")
    replacement = bowl("replacement", 12)
    s.restructure("replacement", WRITER, (joined.ref,), (replacement,), actor=ALICE.identity, rule=LAW, reason="Explicit replacement identity")
    delegate = ObjectVersion(ref("delegate"), WRITER, "Delegate", (Role.PERSON,),
        (Memory(ident("delegate")),), attributes=(Attribute("represents", ref("group")),))
    group = ObjectVersion(ref("group"), WRITER, "Workshop group", (Role.COLLECTIVE,),
        (Composition((delegate.ref.identity,), "Declared voluntary membership", summary_dependencies=(delegate.ref,)), Governance((RULE,))))
    s.create("cyclic-pair", WRITER, (delegate, group))
    s.revise("membership", WRITER, next_version(group, facets=(Composition((BOB.identity,), "Declared voluntary membership", summary_dependencies=(BOB,)), Governance((RULE,)))), reason="Declared membership succession; no automatic personal learning")
    native_text = s.checkpoint()
    (out / "native.checkpoint.json").write_text(native_text)
    (out / "native.transactions.jsonl").write_text("\n".join(codec.dumps(tx) for tx in s.journal()) + "\n")
    checks = {
        "distinct_equal_forms": left.ref != right.ref and left.facets == right.facets and left.definition == right.definition,
        "independent_custody": s.head(left.ref.identity).facet(Material).owner == BOB.identity and s.head(right.ref.identity).facet(Material).owner == ALICE.identity,
        "relation_history": s.resolve(obligation.ref).facet(Relation).terms[0].value == 9 and s.resolve(revised_obligation.ref).facet(Relation).terms[0].value == 12,
        "hypothesis_not_actual": prediction.ref not in {v.ref for v in s.actual_events()} and len(s.actual_events()) == 2,
        "past_meaning": s.resolve(s.resolve(old_memory.ref).facet(Account).referent).facet(Definition) == old_rule.facet(Definition),
        "conservation": active_quantities(s) == {(ALICE.identity, UNIT): 13, (BOB.identity, UNIT): 1},
        "finite_cycle": s.resolve(delegate.ref).attributes[0].value == group.ref and delegate.ref.identity in s.resolve(group.ref).facet(Composition).members,
        "native_replay_exact": ObjectStore.restore(native_text).checkpoint() == native_text,
    }

    from hle.demo import config, request, ALICE as LA, BOB as LB, BOX
    from hle.world_records import Attempt, Credit, TRANSFER, Tick
    bridge = legacy.LegacyWorldBridge(config(energy=1, time=8))
    bridge.execute(Attempt("start", "job", request(LA, TRANSFER, (BOX, LB))))
    partial = bridge.checkpoint()
    (out / "legacy_r2_partial.original.json").write_text(bridge.legacy_checkpoint())
    (out / "legacy_r2_partial.u2.json").write_text(codec.dumps(partial))
    restored = legacy.LegacyWorldBridge.restore(codec.loads(codec.dumps(partial)))
    checks["legacy_partial_exact"] = restored.legacy_checkpoint() == bridge.legacy_checkpoint()
    for command in (Credit("credit", LA, 1, 0, "Explicit R2 fixture supply"), Attempt("finish", "job", request(LA, TRANSFER, (BOX, LB)))):
        bridge.execute(command)
        restored.execute(command)
    checks["legacy_paid_continuation_exact"] = bridge.legacy_checkpoint() == restored.legacy_checkpoint()
    (out / "legacy_r2_completed.original.json").write_text(restored.legacy_checkpoint())

    from r21b_policy import run_candidate
    from hle.closure import ClosureWorld
    world, _ = run_candidate("iee", 12, "inadequate")
    text = world.checkpoint()
    converted = legacy.checkpoint_object(text, "v4-zero")
    (out / "legacy_v4_zero.original.json").write_text(text)
    (out / "legacy_v4_zero.u2.json").write_text(codec.dumps(converted))
    recovered = legacy.checkpoint_text(codec.loads(codec.dumps(converted)))
    restored_v4 = ClosureWorld.restore(recovered)
    checks["legacy_v4_roundtrip_exact"] = text == recovered == restored_v4.checkpoint()
    world.execute(Tick("continue")); restored_v4.execute(Tick("continue"))
    checks["legacy_v4_continuation_exact"] = world.checkpoint() == restored_v4.checkpoint()
    manifest = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(out.iterdir()) if p.is_file()}
    summary = {"schema": "hle-unified-u2-witness-v1", "passed": all(checks.values()), "checks": checks,
               "native_transactions": len(s.journal()), "native_versions": sum(len(tx.versions) for tx in s.journal()),
               "actual_events": len(s.actual_events()), "files": manifest,
               "scope": "Deterministic development witnesses; not additional test counts or held-out evaluation."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
