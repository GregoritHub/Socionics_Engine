"""A finite retained-capacity assay; no psychological diagnosis or altitude law."""
from dataclasses import dataclass
import hashlib

from hle.contracts import ActionRequest, ClaimStatus, Kind, Ref, WorkStatus
from hle.crux import Perspective
from hle.metabolism_records import ProcessingPolicy, Profile
from hle.model_a import TYPES, ego, stack
from hle.socion_records import AgentPolicy
from hle.world_records import Attempt, Entity, INSPECT, Ownership, TRANSFER, Wallet, WorldConfig
from .runtime import ContentWorld, WIRE, canonical, unpack

LEARNER, HELPER, PARTNER, SECOND = tuple(Ref(Kind.ENTITY, name, 1) for name in
                                     ("learner", "helper", "partner", "second_partner"))
ACTORS = (LEARNER, HELPER, PARTNER, SECOND)
CONTEXT = Ref(Kind.CONTEXT, "finite_crossing_task", 1)
TRAINING = {"kind": "training", "cases": [
    {"offered": ["train_a", "train_b"], "accepts": ["train_b"]},
    {"offered": ["train_c", "train_d", "train_e"], "accepts": ["train_c", "train_e"]},
]}
QUADRANTS = {frozenset("NF"): "I", frozenset("ST"): "It",
             frozenset("SF"): "We", frozenset("NT"): "Its"}
EDGES = {"f": frozenset(("I", "We")), "t": frozenset(("It", "Its")),
         "n": frozenset(("I", "Its")), "s": frozenset(("It", "We"))}


def geometry():
    rows = []
    for tim in TYPES:
        native, complement = stack(tim)[:2], stack(tim)[4:6]
        quadrant = lambda pair: QUADRANTS[frozenset(e[0].upper() for e in pair)]
        a, b = quadrant(native), quadrant(complement)
        assert frozenset((a, b)) not in EDGES.values()
        rows.append({"tim": tim, "native": a, "complement": b,
                     "native_pair": list(native), "complementary_pair": list(complement)})
    return {"function_edges": {k: sorted(v) for k, v in EDGES.items()},
            "primitive_horizontal_edges": [], "types": rows,
            "scope": "club/quadrant bridge; paths are not retained development"}


def tasks():
    before = [dict(kind="task", key=f"before_{i}", offered=[f"before_{i}_{j}" for j in range(3)],
                   accepts=[f"before_{i}_1"], recipient=PARTNER.key) for i in range(2)]
    practice = dict(kind="task", key="practice", offered=["practice_0", "practice_1"],
                    accepts=["practice_1"], recipient=PARTNER.key)
    after = []
    for width in (3, 4, 5):
        for accepted in range(width):
            key = f"held_{width}_{accepted}"
            after.append(dict(kind="task", key=key, offered=[f"{key}_{j}" for j in range(width)],
                              accepts=[f"{key}_{accepted}"],
                              recipient=PARTNER.key if accepted % 2 else SECOND.key))
    return before, practice, after


def make_world(task_values=(), tim="sli", energy=10000):
    items = tuple(Ref(Kind.ENTITY, key, 1) for task in task_values for key in task["offered"])
    descriptors = tuple(Entity(a, a.key, "actor") for a in ACTORS) + tuple(Entity(i, i.key, "object") for i in items)
    config = WorldConfig(CONTEXT, descriptors, ACTORS, tuple(Ownership(i, LEARNER) for i in items),
                         tuple(Wallet(a, energy, energy) for a in ACTORS), (),
                         tuple((a, b) for a in ACTORS for b in ACTORS if a != b))
    profiles = (Profile(LEARNER, tim, ego(tim)[0]), Profile(HELPER, "iee", "ne"),
                Profile(PARTNER, "lsi", "ti"), Profile(SECOND, "ese", "fe"))
    return ContentWorld(config, profiles, ProcessingPolicy(), tuple(AgentPolicy(a) for a in ACTORS))


@dataclass(frozen=True)
class CapacityPolicy:
    """Reads detached OWN durable memories; has no condition, Truth or answer key."""
    def sources(self, own_memories):
        result = {}
        for memory in own_memories:
            if memory.claim_status != ClaimStatus.ENDORSED:
                continue
            if len(memory.content) != 1 or memory.content[0].relation != WIRE:
                continue
            body = unpack(memory.content[0].object)
            if body["kind"] in ("search_rule", "boundary_rule"):
                result[body["kind"]] = memory.ref
        return result


def charge_total(world, actor, since=0):
    return sum(work.completed_units for tx in world.truth.journal()[since:]
               for work in tx.works if work.owner == actor)


def teach(world, retained):
    training = world.retain_content(HELPER, "training", TRAINING)
    ephemeral = {}
    for family in ("search", "boundary"):
        demo = world.process(HELPER, "demo:" + family, "demonstrate_" + family, (training,))
        observation = world.send_content(HELPER, demo, LEARNER, "teach:" + family)
        world.receive_content(LEARNER, observation, "read:" + family)
        output = world.process(LEARNER, "infer:" + family, "infer_" + family, (observation,))
        ephemeral[family + "_rule"] = output
        if family in retained:
            world.retain_content(LEARNER, "capacity:" + family, world.content(LEARNER, output), (output,))
    return ephemeral


def trial(world, task, sources, enact=True):
    start = len(world.truth.journal())
    recipient = next(a for a in ACTORS if a.key == task["recipient"])
    request = world.retain_content(recipient, task["key"], task)
    observation = world.send_content(recipient, request, LEARNER, task["key"] + ":request")
    world.receive_content(LEARNER, observation, task["key"] + ":receive")
    basis = (observation,) + ((sources["search_rule"],) if "search_rule" in sources else ())
    options = world.process(LEARNER, task["key"] + ":search", "search", basis)
    basis = (observation, options) + ((sources["boundary_rule"],) if "boundary_rule" in sources else ())
    related = world.process(LEARNER, task["key"] + ":relate", "relate", basis)
    plan_ref = world.process(LEARNER, task["key"] + ":prepare", "prepare", (observation, related))
    plan = world.content(LEARNER, plan_ref)
    completed = False
    action_event = None
    if enact and plan["item"] is not None:
        item = Ref(Kind.ENTITY, plan["item"], 1)
        key = task["key"] + ":inspect"
        event = world.execute(Attempt(key, key, ActionRequest(LEARNER, INSPECT, (item,), (plan_ref,))))
        observed = world.participant_input(LEARNER)[0].observations[-1]
        # Executor decisions use delivered inspection, never global facts.
        if event.outcome == WorkStatus.COMPLETED and any(p.subject == item and p.relation == "owned_by" and p.object == LEARNER
                                                       for p in observed.content):
            key = task["key"] + ":return"
            action_event = world.execute(Attempt(key, key, ActionRequest(LEARNER, TRANSFER, (item, recipient), (plan_ref, observed.ref))))
            completed = action_event.outcome == WorkStatus.COMPLETED
    # Evaluator-only checks follow action; none enter content operations/policy.
    accepted = completed and plan["item"] in task["accepts"]
    if completed:
        fact = world.truth.current_fact(Ref(Kind.ENTITY, plan["item"], 1), "owned_by", world.config.context)
        accepted = accepted and fact.object == recipient
    option_values, related_values = world.content(LEARNER, options), world.content(LEARNER, related)
    return {"task": task["key"], "width": len(task["offered"]), "recipient": recipient.key,
            "offered": task["offered"], "accepts": task["accepts"], "options": option_values["items"],
            "admissible": related_values["items"], "chosen": plan["item"],
            "search_complete": option_values["items"] == task["offered"],
            "boundary_complete": related_values["items"] == [x for x in task["offered"] if x in task["accepts"]],
            "action_completed": completed, "accepted_return": accepted,
            "action_event": action_event.ref.key if action_event else None,
            "retained_sources": {k: {"key": v.key, "revision": v.revision, "kind": v.kind.value} for k, v in sources.items()},
            "learner_units": charge_total(world, LEARNER, start),
            "helper_units": charge_total(world, HELPER, start),
            "processing_active": world.processing_state(LEARNER).active}


def assess(before, after, retained, tim_before, tim_after):
    if not after:
        return {"status": "unassessed_no_renewed_demand", "gates": {}}
    retained_pair = set(retained) == {"search_rule", "boundary_rule"}
    expected_refs = {k: {"key": r.key, "revision": r.revision, "kind": r.kind.value} for k, r in retained.items()}
    gates = {
        "same_tim": tim_before == tim_after,
        "complement_matches_tim": set(stack(tim_before)[4:6]) == {"ne", "fi"},
        "retained_pair_used": retained_pair and all(t["retained_sources"] == expected_refs for t in after),
        "helper_withdrawn": all(t["helper_units"] == 0 for t in after),
        "new_objects": not ({x for t in before for x in t["offered"]} & {x for t in after for x in t["offered"]}),
        "alternative_generation": all(t["search_complete"] for t in after),
        "partner_constraints": all(t["boundary_complete"] for t in after),
        "consequential_return": all(t["accepted_return"] for t in after),
        "renewed_increased_demand": len(after) >= 2 and min(t["width"] for t in after) >= max(t["width"] for t in before)
                                    and max(t["width"] for t in after) > max(t["width"] for t in before),
        "repeated_failure_resolved": len(before) >= 2 and all(not t["accepted_return"] for t in before)
                                     and all(t["accepted_return"] for t in after),
    }
    return {"status": "retained_complement_candidate_in_tested_task" if all(gates.values()) else "criteria_not_met",
            "gates": gates}


CONDITIONS = {"no_instruction": (), "help_only": (), "search_only": ("search",),
              "boundary_only": ("boundary",), "both_retained": ("search", "boundary"),
              "both_without_return": ("search", "boundary"), "quiet_after_help": ("search", "boundary")}


def run_condition(condition, tim="sli"):
    before_tasks, practice_task, after_tasks = tasks()
    world = make_world(before_tasks + [practice_task] + after_tasks, tim)
    policy = CapacityPolicy()
    before = [trial(world, t, policy.sources(world.participant_input(LEARNER)[0].own_memories)) for t in before_tasks]
    practice = None
    if condition != "no_instruction":
        temporary = teach(world, CONDITIONS[condition])
        practice = trial(world, practice_task, temporary)
    # New controller, same world and owned memories. No transient help is passed.
    policy = CapacityPolicy()
    retained = policy.sources(world.participant_input(LEARNER)[0].own_memories)
    after = [] if condition == "quiet_after_help" else [
        trial(world, task, policy.sources(world.participant_input(LEARNER)[0].own_memories),
              enact=condition != "both_without_return") for task in after_tasks]
    assessment = assess(before, after, retained, tim, world._profiles[LEARNER].tim)
    # Independently reconcile every work record with its wallet debits.
    ledger = dict((a, (10000, 10000)) for a in ACTORS)
    for tx in world.truth.journal():
        for work in tx.works:
            previous, charged, remaining = ([r.amount for r in x] for x in (work.before, work.charged, work.after))
            assert tuple(previous) == ledger[work.owner]
            assert charged == [work.completed_units, work.completed_units]
            assert remaining == [previous[i] - charged[i] for i in range(2)]
            ledger[work.owner] = tuple(remaining)
    return {"condition": condition, "tim": tim, "before": before, "assisted_practice": practice,
            "after": after, "retained_programs": {k: world.content(LEARNER, v)["program"] for k, v in retained.items()},
            "successes": sum(t["accepted_return"] for t in after), "held_out_trials": len(after),
            "total_units": {a.key: charge_total(world, a) for a in ACTORS}, "assessment": assessment}


def content_identity_panel():
    rows = []
    for tim in TYPES:
        for family in ("search", "boundary"):
            for activity in ("hold", "infer_" + family):
                world = make_world(tim=tim)
                training = world.retain_content(HELPER, "training", TRAINING)
                demo = world.process(HELPER, "demo", "demonstrate_" + family, (training,))
                # The same completed content is issued after different activities.
                world.process(HELPER, "intervening", activity, (demo,))
                sender_active = world.processing_state(HELPER).active
                body = world.content(HELPER, demo)
                obs = world.send_content(HELPER, demo, LEARNER, "send")
                notice = world._notice_by_observation[(LEARNER, obs)]
                start = len(world.truth.journal())
                world.receive_content(LEARNER, obs, "read")
                reception = world._receptions[(LEARNER, "read")]
                rows.append({"receiver": tim, "family": family, "sender_active": sender_active,
                             "content_aspect": notice.element, "receiver_landing": reception.landing_position,
                             "body_sha256": hashlib.sha256(canonical(body).encode()).hexdigest(),
                             "reception_units": charge_total(world, LEARNER, start)})
    pairs = list(zip(rows[::2], rows[1::2]))
    stable = sum(all(a[k] == b[k] for k in ("body_sha256", "content_aspect", "receiver_landing", "reception_units"))
                 and a["sender_active"] != b["sender_active"] for a, b in pairs)
    return {"matched_pairs": len(pairs), "stable_pairs": stable, "rows": rows}


def run():
    return {"schema": "experimental-crossing-v1", "scope": "finite procedural learning under declared content contracts",
            "geometry": geometry(), "content_identity": content_identity_panel(),
            "conditions": [run_condition(c) for c in CONDITIONS],
            "type_control": [run_condition("both_retained", tim) for tim in TYPES],
            "full_individuation": "unassessed", "altitude_change": "unassessed",
            "human_validation": "unassessed", "checkpoint_support": False}
