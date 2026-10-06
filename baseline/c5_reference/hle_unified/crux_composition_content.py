"""C4 transformations use prepared accessible content, never world truth."""
from .self_content import encode, decode


def frame(p):
    r=p["request"]; recipe=p["recipe"]; a=recipe.action; data=p["data"]; x=data[0]
    common=dict(target=r.target, context=r.context, source=r.input)
    if a=="renew":
        own=data[1]
        return dict(common, kind="offer", cap=own["cap"], domain="WE", speaker=r.actor,
            receiver=r.peer, group=r.group, question_demand=r.demand, status="offered",
            source_kind="shared", consent=own["consent"], prior=r.input)
    if a=="commune":
        offer,reply=data[1:]; inward=recipe.polarity=="accumulation"
        assents=(offer["consent"],reply["consent"])
        return dict(common, kind="shared", cap=min(offer["cap"],reply["own_cap"]),
            offered_cap=offer["cap"], participants=(r.actor,r.peer), group=r.group,
            exchange=r.inputs[1:], prior=r.input, positions=(offer["cap"],reply["own_cap"]),
            difference=offer["cap"]!=reply["own_cap"], prior_difference=x["difference"],
            assents=assents, authorized=not inward and all(assents),
            mode="understood" if inward else "commitment",
            status="understood" if inward else ("accepted" if all(assents) else "declined"),
            competence=False)
    if a=="integrate":
        limits=tuple(d["cap"] for d in data)
        coupled=recipe.polarity=="expenditure" and all(d.get("authority")==r.actor and d["status"]=="governed_arrangement" for d in data)
        return dict(common, kind="model", cap=min(limits) if all(v is not None for v in limits) else None,
            formula="min(demand, cap, observed_available)", components=r.inputs,
            limits=limits, differences=len(set(limits))>1,
            assumptions=("conjunctive constraints in the same consumable context", "component evidence remains historical"),
            uncertain=any(d["uncertain"] for d in data), coupled=coupled,
            authority=r.actor if coupled else None,
            status="governed_arrangement" if coupled else "dependency_model", competence=False)
    if a=="context":
        own,observation=data[1:]
        limits=(x["cap"],own["cap"],observation["available"])
        return dict(common, kind="model", cap=min(limits) if all(v is not None for v in limits) else None,
            formula="min(demand, cap, observed_available)", source_context=x["context"],
            local_evidence=r.inputs[1:], limits=limits, differences=len(set(limits))>1,
            assumptions=("source model is a hypothesis in the destination context", "local observation is historical"),
            uncertain=True, authority=None, status="dependency_model", competence=False)
    if a=="parent":
        rows=p["child_rows"]; completed=all(z[2]=="succeeded" and z[7] for z in rows)
        return dict(common, kind="nested", children=tuple((c.operation,c.output) for c in r.children),
            links=r.links, outcomes=rows, complete=completed,
            status="complete" if completed else "blocked", depth=p["depth"],
            operations=p["operations"], cited_spending=sum(n for _,n in p["operations"]),
            polarities=tuple(z[6] for z in rows), competence=False)
    if a=="release":
        model=data[1]; allowed=x["complete"]
        return dict(model, source=r.inputs[1], gate=r.input, gate_satisfied=allowed,
            cap=model["cap"] if allowed else None, competence=False)
    raise ValueError("unknown composition action")


def transform(name,p,previous):
    if name.startswith("prepare:"):
        result=dict(kind="composition_work", work=encode(frame(p)))
    else:
        prior=decode(previous[2]["payload"])
        if prior["kind"]!="composition_work": raise ValueError("missing paid composition handoff")
        result=decode(prior["work"])
    return "c4", p["request"].target, {"payload":encode(result)}
