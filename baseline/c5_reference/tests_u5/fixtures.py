"""Finite supplied workshop, prior belief, and communicated offer, not emergence."""
from dataclasses import replace
from tests_u4.fixtures import *
from hle_unified.records import Proposition
from hle_unified.cognitive_records import CognitiveRequest, catalog, reference
from hle_unified.cognition import CognitiveEngine, profile
from hle_unified.cognitive_content import plan_request, derive

CUE5 = reference("minor:Coin:10")
RULE = ref("condition-policy")
OFFER = ref("communicated-help")


def setup5(tim="iee", budget=500, *, prior="damaged", prepare=True,
           offer_target=SAW, offer_context=ROOM, offer_receiver=ALICE, time_budget=None,
           hidden_wear=0):
    inherited = setup(budget, prepare=False, time_budget=time_budget)
    world = OperationStore()
    initial = inherited.world.journal()[0].versions
    world.create("genesis", WRITER, tuple(replace(v, attributes=attributes(
        {**attrs(v), "wear":hidden_wear})) if v.ref == KIT else v for v in initial))
    policy = ObjectVersion(RULE, WRITER, "Finite property action policy", (Role.DEFINITION,),
        (Definition("Inspect uncertain or damaged tools; use retained serviceable tools; assistance may offer repair.",
            SourceStatus.ENGINEERING, attributes({"relation": "condition", "default": "inspect",
                'when."damaged"': "inspect", 'when."serviceable"': "use"})),))
    world.create("u5-initial-structure", WRITER, (*catalog(), policy,
        *(profile(a, tim if a == ALICE else "sli") for a in (ALICE, BOB, EVE))))
    e = CognitiveEngine(world, LAW_REF)
    if prepare:
        basics(e, ALICE)
        show(e, ALICE, CUE5)
        show(e, ALICE, RULE, selectors=(Selector("rule", "definition", ("facets", "0")),))
        seed(e, "initial-account", prior)
        offer = ObjectVersion(OFFER, WRITER, "Communicated assistance offer", (Role.CLAIM,),
            (Account(offer_target, (), Moment(0, 0), ALICE),), occurrence=Occurrence.REMEMBERED_CLAIM,
            attributes=attributes({"offer": "assistance", "giver": BOB, "receiver": offer_receiver,
                "operation": "repair", "target": offer_target, "tool": KIT, "stock": STOCK,
                "context": offer_context}))
        e.declare("offer-input", (offer,))
        show(e, ALICE, OFFER, selectors=tuple(Selector(a.name, "detail", ("attributes", str(i), "value"))
                                            for i, a in enumerate(offer.attributes)))
    return e


def seed(e, key, value="damaged", *, actor=ALICE, target=SAW, cue=CUE5, context=ROOM,
         relation="condition", links=(), status=ClaimStatus.ENDORSED, scope=None):
    addresses = evidence(e, actor, target)
    source = e.participant_view(actor).detail(addresses[0]).source
    binding_ref = ref(key)
    draft = ObjectVersion(binding_ref, WRITER, "Supplied prior association", (Role.INTERPRETATION,),
        (Account(target, (Proposition(target, relation, value, context,
            scope or TimeScope(Moment(target.revision, 0), None)),), Moment(0, 0), actor, (source,)),),
        occurrence=Occurrence.INTERPRETATION,
        attributes=attributes({"cue":cue,"context":context,"meaning":"Prior situated account",
            "endorsement":status.value,"confidence":None,
            **{"link."+str(i): b for i,b in enumerate(links)}}))
    e.declare("seed:"+key, (draft,))
    perform(e, OperationRequest("seed:"+key, actor, "bind", context, binding=binding_ref, evidence=addresses))
    return binding_ref


def request5(e, key="plan", purpose="plan", *, actor=ALICE, target=SAW,
             source=OFFER, rule=RULE, cue=CUE5, context=ROOM, **kwargs):
    evidence_ = tuple(p.address for p in e.participant_view(actor).resolve(source))
    return CognitiveRequest(key, actor, purpose, context, cue, target, rule, evidence_, **kwargs)


def think(e, r):
    perform(e, r)
    d = e.job_status(r.actor, r.key)
    assert d["status"] == "succeeded", d["failure"]
    return d["binding"]


def enact(e, plan, key="assisted-repair", actor=ALICE):
    e.enact("enact:"+key, actor, key, plan)
    e.advance("work:"+key, actor, key, 1000)
    return e.commit("commit:"+key, actor, key)


def circuit(tim="iee"):
    e = setup5(tim)
    first = think(e, request5(e))
    event = enact(e, first)
    observation = receive(e, event, ALICE, "repair-outcome")
    retained = think(e, request5(e, "retain", "integrate", source=observation))
    later = think(e, request5(e, "later", target=SAW, source=observation))
    used = enact(e, later, "later-use")
    return e, {"first": first, "repair": event, "observation": observation,
               "retained": retained, "later": later, "used": used}
