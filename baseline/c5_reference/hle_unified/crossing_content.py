"""Pure C3 operations. Only prepared participant-visible values enter here.

Numbers are resource units, not psychological measures. A cap is a scoped
constraint; an observation, personal intention, model and public rule differ.
"""
from .self_content import encode, decode

def intention(d):
    if (set(d)!={"kind","cap","consent"} or d["kind"]!="intention" or
        type(d["cap"]) is not int or not 0<=d["cap"]<=1000 or type(d["consent"]) is not bool):
        raise ValueError("bounded actor-owned intention and explicit assent required")

def cap(d):
    return d.get("available") if d["kind"]=="observation" else d.get("cap")

def bounded(value, demand): return 0 if value is None else min(value,demand)

def frame(p):
    r=p["request"]; recipe=p["recipe"]; a=recipe.action; data=p["data"]
    face=recipe.polarity; x=data[0]
    common=dict(target=r.target,context=r.context,source=r.input)
    if a=="offer":
        return dict(common,kind="offer",cap=cap(x),domain=recipe.origin,speaker=r.actor,
            receiver=r.peer,group=r.group,question_demand=r.demand,
            status="offered",source_kind=x["kind"])
    if a=="reply":
        own=data[1]
        return dict(common,kind="reply",offer=r.input,speaker=r.actor,receiver=r.peer,
            group=r.group,understood=cap(x),answer=bounded(cap(x),x["question_demand"]),
            own_cap=own["cap"],consent=own["consent"],
            question="capacity_difference" if own["cap"]!=cap(x) else "none")
    if a=="vote":
        own=data[1]
        return dict(common,kind="vote",draft=r.input,speaker=r.actor,group=r.group,
            cap=cap(x),assent=own["consent"] and cap(x) is not None and cap(x)<=own["cap"])
    if a in ("share","coordinate","educate"):
        offer,reply=data[1:]
        received=reply["understood"]
        return dict(common,kind="shared",cap=None if received is None else min(received,reply["own_cap"]),
            offered_cap=cap(x),participants=(r.actor,r.peer),group=r.group,
            exchange=(r.inputs[1],r.inputs[2]),difference=reply["question"],
            receiver_answer=reply["answer"],understood=received,
            assents=(p["source_assent"],reply["consent"]),
            mode="examined" if face=="accumulation" else "active_contribution",
            authorized=face=="expenditure" and p["source_assent"] and reply["consent"],
            teaching=a=="educate",competence=False)
    if a=="theorize":
        return dict(common,kind="model",cap=x["cap"],
            formula="min(demand, cap, observed_available)",
            assumptions=("same context and consumable units","cap is an owned hypothesis"),
            test="compare actual consumption and remaining stock",uncertain=True,
            status="contained_hypothesis" if face=="accumulation" else "submitted_model")
    if a=="organize":
        quantities=tuple(d.get("available") for d in data)
        observed=tuple(v for v in quantities if v is not None)
        return dict(common,kind="model",cap=min(observed) if observed else None,
            formula="min(demand, cap, observed_available)",samples=tuple(r.inputs),
            observed_limits=quantities,assumptions=("observed stock snapshots are historical","current custody still required"),
            dependencies=("available units","owner consent","paid execution"),
            authority=r.actor if face=="expenditure" else None,
            status="dependency_model" if face=="accumulation" else "governed_arrangement",uncertain=True)
    if a=="institutionalize":
        if face=="accumulation":
            return dict(common,kind="rule",cap=cap(x),group=r.group,participants=x["participants"],
                practice=r.inputs[1],status="draft",authority="unanimous_exact_votes",votes=(),
                responsibilities=((r.actor,"pay own participation"),(r.peer,"pay own participation")),
                enforcement="voluntary governed requests only",authorized=False)
        accepted=all(d["assent"] for d in data[1:])
        return dict(x,source=r.input,status="ratified" if accepted else "declined",
            votes=tuple(r.inputs[1:]),authorized=accepted)
    if a in ("embody","identify","understand"):
        own=data[1] if len(data)>1 else None
        value=cap(x)
        if own is not None and value is not None: value=min(value,own["cap"])
        return dict(common,kind="personal_policy",cap=value,
            mode="interpretation" if face=="accumulation" else "decision_policy",
            basis=x["kind"],limits=("this context and consumable units","no practiced competence conferred"),
            stance=("accepted" if own is None or own["consent"] else "declined"),
            consent=True if own is None else own["consent"],
            tension=False if own is None else cap(x)!=own["cap"],competence=False)
    if a in ("express","apply","mobilize"):
        amount=bounded(cap(x),r.demand)
        primitive="inspect" if face=="accumulation" and a!="apply" else "consume"
        if face=="accumulation" and a=="apply": amount=min(1,amount)
        return dict(common,kind="material_command",primitive=primitive,stock=r.stock,
            amount=amount if primitive=="consume" else 1,
            mode=("trial" if a=="apply" else "preparation") if face=="accumulation" else "performance",
            permitted=p["material_assent"])
    if a=="use":
        amount=bounded(cap(x),r.demand)
        if p.get("available") is not None: amount=min(amount,p["available"])
        permission=x.get("consent",True) and (x["kind"]!="rule" or x.get("authorized",False))
        if x["kind"]=="shared": permission=x.get("authorized",False)
        if x.get("mode")=="interpretation" or x.get("status")=="dependency_model": permission=False
        if x.get("status")=="governed_arrangement": permission=x["authority"]==r.actor
        return dict(common,kind="decision",amount=amount,cap=cap(x),demand=r.demand,
            status="proposed" if not permission else "selected",permitted=permission,
            stock=r.stock,group=r.group,action="consume" if amount and permission else "none")
    raise ValueError("unknown C3 operation")

def transform(name,p,previous):
    if name.startswith("scope:"):
        result=dict(kind="scoped_work",work=encode(frame(p)))
    elif len(p["recipe"].steps)==2:
        prior=decode(previous[2]["payload"])
        if prior["kind"]!="scoped_work": raise ValueError("missing exact intermediate")
        result=decode(prior["work"])
    else: result=frame(p)
    return "c3",p["request"].target,{"payload":encode(result)}
