"""Retain raw native workshop history and independent accounting witnesses."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from hle_unified import codec
from hle_unified.operations import OperationEngine, NativeAccess
from hle_unified.material import OperationStore, attrs, available
from hle_unified.operation_audit import audit_transactions
from tests_u4.fixtures import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    checks = {}
    def save(name, value):
        (out / name).write_text(value if type(value) is str else json.dumps(value, indent=2) + "\n")
    def check(name, result):
        checks[name] = bool(result)
        if not result:
            raise AssertionError(name)
    engine = setup(quantity=1)
    basics(engine, BOB)
    before_a, before_b = engine.participant_view(ALICE).bytes(), engine.participant_view(BOB).bytes()
    save("alice.before.json", before_a)
    save("bob.before.json", before_b)
    engine.start("repair-a", repair(engine, "repair-a"))
    engine.advance("repair-a-partial", ALICE, "repair-a", 2)
    engine.start("repair-b", repair(engine, "repair-b", SAW2))
    engine.advance("repair-b-wait", ALICE, "repair-b", 10)
    partial = engine.checkpoint()
    save("workshop.partial.checkpoint.json", partial)
    save("audit.partial.json", audit_transactions(engine.world.journal()))
    restored = OperationEngine.restore(partial)
    check("partial_restore_exact", restored.checkpoint() == partial)
    check("partial_repair_has_no_physical_effect", engine.world.head(SAW.identity).ref == SAW)
    check("waiting_contender_spends_zero", engine.job_status(ALICE, "repair-b")["spent"] == 0)
    for current in (engine, restored):
        current.advance("repair-a-rest", ALICE, "repair-a", 100)
        current.commit("repair-a-effect", ALICE, "repair-a")
        current.advance("repair-b-work", ALICE, "repair-b", 100)
        current.commit("repair-b-effect", ALICE, "repair-b")
    check("continued_restore_exact", engine.checkpoint() == restored.checkpoint())
    repair_event = engine.job_status(ALICE, "repair-a")["result"]
    check("repair_effect_actual", engine.world.head(SAW.identity).facet(Material).condition == "serviceable")
    check("resource_exhausted_exactly_once", available(engine.world.head(STOCK.identity)) == 0)
    check("stale_contender_retains_six_paid_units", engine.job_status(ALICE, "repair-b")["spent"] == 6 and engine.job_status(ALICE, "repair-b")["failure"] == "stale_dependency")
    check("alice_unchanged_without_delivery", engine.participant_view(ALICE).bytes() == before_a)
    check("bob_unchanged_without_delivery", engine.participant_view(BOB).bytes() == before_b)
    save("alice.after_effect_before_delivery.json", engine.participant_view(ALICE).bytes())
    observation = engine.deliver_event("alice-physical", repair_event, ALICE)
    engine.start("read-physical", OperationRequest("read-physical", ALICE, "read", ROOM, delivery="alice-physical"))
    engine.advance("read-partial", ALICE, "read-physical", 1)
    save("workshop.partial_read.checkpoint.json", engine.checkpoint())
    save("alice.partial_read.json", engine.participant_view(ALICE).bytes())
    check("partial_read_does_not_disclose", not engine.participant_view(ALICE).resolve(observation))
    engine.advance("read-rest", ALICE, "read-physical", 1)
    engine.commit("read-effect", ALICE, "read-physical")
    check("paid_read_discloses_observation", bool(engine.participant_view(ALICE).resolve(observation)))
    saved_history_position = len(engine.participant_view(ALICE).snapshot.history)
    saved_actor = engine.participant_view(ALICE).bytes()
    interpretation = binding(engine, "help-interpretation", ALICE, observation)
    perform(engine, interpretation)
    check("binding_is_separately_paid", engine.job_status(ALICE, interpretation.key)["spent"] == 3)
    check("reading_and_binding_not_acquisition", not engine.participant_view(ALICE).can_use(REPAIR, ROOM))
    perform(engine, OperationRequest("retain-repair", ALICE, "acquire", ROOM, procedure=REPAIR, practice=repair_event))
    check("paid_practice_retained_for_actor", engine.participant_view(ALICE).can_use(REPAIR, ROOM))
    check("bob_has_no_unearned_acquisition", not engine.participant_view(BOB).can_use(REPAIR, ROOM))
    bob_obs = receive(engine, repair_event, BOB, "bob-later")
    check("separate_delivery_times", engine.world.resolve(bob_obs).facet(Account).at > engine.world.resolve(observation).facet(Account).at)
    check("one_effect_observation_lineage", engine.world.resolve(observation).facet(Account).sources == (repair_event,) and engine.world.resolve(bob_obs).facet(Account).sources == (repair_event,))
    check("historical_actor_view_exact", engine.participant_view(ALICE, through=saved_history_position).bytes() == saved_actor)
    save("alice.completed.json", engine.participant_view(ALICE).bytes())
    save("bob.completed.json", engine.participant_view(BOB).bytes())
    save("workshop.completed.checkpoint.json", engine.checkpoint())
    save("native.compact.checkpoint.json", engine.world.checkpoint())
    save("situated.completed.checkpoint.json", engine.access.checkpoint())
    save("native.transactions.jsonl", "\n".join(codec.dumps(tx) for tx in engine.world.journal()) + "\n")
    check("completed_engine_replay_exact", OperationEngine.restore(engine.checkpoint()).checkpoint() == engine.checkpoint())
    check("native_store_replay_exact", OperationStore.restore(engine.world.checkpoint()).checkpoint() == engine.world.checkpoint())
    check("access_replay_exact", NativeAccess.restore(engine.access.checkpoint()).checkpoint() == engine.access.checkpoint())
    # Reload the exported raw stream, not the live engine or its cached indexes.
    raw = tuple(codec.loads(line) for line in (out / "native.transactions.jsonl").read_text().splitlines())
    audit = audit_transactions(raw)
    save("independent_raw_audit.json", audit)
    check("raw_accounting_and_material_audit", audit["passed"] and audit["physical_commits"] == 1 and audit["active_reservations"] == 0)
    summary = {"schema": "hle-unified-u4-witness-v1", "checks": checks,
               "checks_passed": sum(checks.values()), "checks_total": len(checks),
               "passed": all(checks.values()), "raw_audit": audit,
               "scope": "Deterministic development workshop; no held-out seeds or population release."}
    save("summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
