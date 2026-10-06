"""Supplied C1 test conditions; neither a world generator nor autonomy claim."""
from dataclasses import replace
from tests_u5.fixtures import *
from hle_unified.crux_execution import CruxEngine
from hle_unified.crux_records import MovementRequest
from hle_unified import crux_content


def setup_c1(tim="iee", *, prior="damaged", actual="serviceable", budget=3000,
             target=SAW, engine_type=CruxEngine, inactive=0, shared=False):
    base = setup5(tim, budget=budget, prepare=False)
    world = OperationStore()
    for tx in base.world.journal():
        versions = []
        for v in tx.versions:
            if v.ref == target:
                m = v.facet(Material)
                v = replace(v, facets=(replace(m, condition=actual),),
                    attributes=attributes({**attrs(v), "wear": 0 if actual == "serviceable" else attrs(v)["max_wear"]}))
            versions.append(v)
        world.create(tx.key, tx.writer, tuple(versions))
    if inactive:
        world.create("inactive-history", WRITER, tuple(
            definition(ref("inactive-" + str(i)), "shared inert definition" if shared else "unused fact " + str(i))
            for i in range(inactive)))
    e = engine_type(world, LAW_REF)
    basics(e, ALICE)
    show(e, ALICE, CUE5)
    show(e, ALICE, RULE, selectors=(Selector("rule", "definition", ("facets", "0")),))
    seed(e, "c1-prior", prior, target=target)
    return e


def hypothesis(e, key="theory", *, target=SAW, elements=()):
    return MovementRequest(key, ALICE, "condition-hypothesis-v1", ROOM, CUE5,
        ref("c1-prior"), evidence(e, ALICE, target), RULE, elements)


def trial(e, model, key="trial"):
    b = e.participant_view(ALICE)._bindings[model]
    return MovementRequest(key, ALICE, "condition-trial-v1", ROOM, CUE5, model, b.particulars)


def retention(e, model, observation, key="embody", *, elements=()):
    return MovementRequest(key, ALICE, "condition-retention-v1", ROOM, CUE5, model,
        tuple(p.address for p in e.participant_view(ALICE).resolve(observation)), elements=elements)


def run_circuit(e, *, target=SAW, later=True):
    first = think(e, request5(e, "before", source=target, target=target))
    perform(e, hypothesis(e, target=target), limit=10000)
    model = e.job_status(ALICE, "theory")["binding"]
    event = perform(e, trial(e, model), limit=10000)
    observation = receive(e, event, ALICE, "c1-trial")
    perform(e, retention(e, model, observation), limit=10000)
    after = think(e, request5(e, "after", source=observation, target=target))
    outcome = enact(e, after, "after-action") if later else None
    return {"before": first, "model": model, "trial": event, "observation": observation,
            "retained": e.job_status(ALICE, "embody")["binding"], "after": after, "after_event": outcome}


class WithoutComparison(CruxEngine):
    """Evaluator ablation; deliberately fails the ordinary C1 content validator."""
    def _semantic_step(self, name, prepared, previous):
        if name == "compare":
            o = prepared["observed"]
            return "assessment", o["target"], {"expected": prepared["model"]["expected"],
                "observed": None, "comparison": "comparison_ablated", "event": o["event"]}
        return super()._semantic_step(name, prepared, previous)
