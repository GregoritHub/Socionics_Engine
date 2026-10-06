"""Declared development worlds. The driver grants opportunities and delivery only."""
from dataclasses import replace
from tests_u5.fixtures import *
from hle_unified.autonomy import AutonomousEngine
from hle_unified.autonomy_records import AutonomyConfig, ForecastRequest
from hle_unified.anticipation import offers


def setup6(*, budget=1200, tim="iee", prior="damaged", offer=True,
           serviceable=False, wear=0, hidden_kit_wear=0, goal_uses=2,
           anticipation=True, **kwargs):
    base = setup5(tim=tim, budget=budget, prepare=False, hidden_wear=hidden_kit_wear)
    if serviceable:
        # Initial condition is an explicitly declared fixture, not a runtime repair.
        world = OperationStore()
        for tx in base.world.journal():
            versions = tuple(tool(SAW, wear=wear) if v.ref == SAW else v for v in tx.versions)
            world.create(tx.key, WRITER, versions)
        base = CognitiveEngine(world, LAW_REF)
    basics(base, ALICE)
    show(base, ALICE, ObjectRef(BOB, 1))
    show(base, ALICE, CUE5)
    show(base, ALICE, RULE, selectors=(Selector("rule", "definition", ("facets", "0")),))
    seed(base, "initial-account", prior)
    # Material thresholds are explicitly visible, not borrowed from world heads.
    if serviceable:
        disclose_fields(base, ALICE, SAW, ("wear", "max_wear"), "initial-wear")
    if offer:
        help_offer(base, "initial-offer", SAW)
    e = AutonomousEngine.adopt(base)
    c = AutonomyConfig(ALICE, ROOM, CUE5, RULE, SAW, KIT, STOCK, CARE,
        REPAIR, BOB, SAW2, goal_uses=goal_uses, anticipation=anticipation, **kwargs)
    e.configure("configure-alice", c)
    return e


def disclose_fields(e, actor, target, names, key):
    v = e.world.resolve(target)
    selectors = tuple(Selector(a.name, "detail", ("attributes", str(i), "value"))
                      for i, a in enumerate(v.attributes) if a.name in names)
    return show(e, actor, target, key=key, selectors=selectors)


def help_offer(e, key, target, *, actor=ALICE, tool_=KIT, stock_=STOCK, context=ROOM,
               deliver=True, read=True):
    r = ref(key)
    value = ObjectVersion(r, WRITER, "Communicated assistance offer", (Role.CLAIM,),
        (Account(target, (), Moment(0, 0), actor),), occurrence=Occurrence.REMEMBERED_CLAIM,
        attributes=attributes({"offer": "assistance", "giver": BOB, "receiver": actor,
            "operation": "repair", "target": target, "tool": tool_, "stock": stock_, "context": context}))
    e.declare("offer:"+key, (value,))
    if deliver:
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(value.attributes))
        e.disclose("show:"+key,actor,r,selectors,r)
        if read:
            perform(e,OperationRequest("read:"+key,actor,"read",ROOM,delivery="show:"+key))
    return r


def drive(e, *, horizon=240, delivery=True, latency=0, stop_when=None, prefix="run", actor=ALICE):
    """Only event IDs are routed, never outcome values or evaluator labels."""
    delivered = set()
    queued = {}
    rows = []
    for turn in range(horizon):
        s = e.state(actor)
        if s.await_event and s.await_event not in delivered:
            queued.setdefault(s.await_event, turn+latency)
        if delivery:
            for event, due in tuple(queued.items()):
                if due <= turn:
                    e.deliver_event(prefix+":delivery:"+str(turn)+":"+event.identity.key, event, actor)
                    delivered.add(event)
                    del queued[event]
        e.step(prefix+":turn:"+str(turn), actor)
        s = e.state(actor)
        rows.append({"turn":turn,"decision":s.decision,"reason":s.reason,"phase":s.phase,
            "active_kind":s.active_kind,"uses":s.uses,"failures":s.failures,
            "fatigue":s.fatigue,"pressure":s.pressure,"fear":s.fear,"scarcity":s.scarcity,"boredom":s.boredom})
        if stop_when and stop_when(e):
            return rows
        if s.stopped:
            return rows
        if s.decision == "wait" and not delivery:
            return rows
        if (s.phase == "help_wait" and not e.participant_view(actor).snapshot.pending
                and not set(offers(e.participant_view(actor),e._configs[actor]))-set(s.offers_at_ask)):
            return rows
    return rows


def first_choice(e, prefix="choice", actor=ALICE):
    drive(e, delivery=False, prefix=prefix, actor=actor, stop_when=lambda e:e.state(actor).active_kind == "action")
    return e.state(actor).last_action


def predictions(e):
    return tuple(v for tx in e.world.journal() for v in tx.versions
                 if v.ref.identity.namespace == "u6.prediction")


def errors(e):
    return tuple(v for tx in e.world.journal() for v in tx.versions
                 if v.ref.identity.namespace == "u6.prediction_error")
