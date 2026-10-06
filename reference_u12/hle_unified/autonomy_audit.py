"""Raw U6 accounting, causal access, hypothetical-status and need-effect audit.

No runtime planner, choice policy, engine indexes or state restoration is used.
Inherited auditors independently check U4 physical accounting and U5 realization.
This bounded audit is not a proof of all possible policies or U14 acceptance.
"""
from .records import Account, Occurrence
from .material import attrs
from .cognitive_audit import audit as cognitive_audit, audit_extent


def extent(d):
    if not d.get("u6"):
        return audit_extent(d)
    if d["purpose"] == "anticipate":
        if not 1 <= d["horizon"] <= 2 or not 1 <= d["nodes"] <= d["node_limit"] <= 16:
            raise ValueError("forecast exceeded declared search bounds")
        required = max(1, d["nodes"] + d["recalled_count"])
    elif d["purpose"] in ("attention", "rest"):
        required = 1
    else:
        raise ValueError("unknown U6 paid work")
    if d["required"] != required or d["route_prepare"] != required or d["route_execute"] != 0:
        raise ValueError("unpaid anticipation or attention extent")


def audit(transactions):
    result = cognitive_audit(transactions, extent_check=extent)
    versions, heads, read, states, spent, attentions, appraisals = {}, {}, {}, {}, {}, {}, {}
    counts = {"predictions": 0, "appraisals": 0, "surprises": 0, "rests": 0,
              "requests": 0, "anticipated_actions": 0, "continuation_states": 0}
    for tx in transactions:
        pending = {v.ref: v for v in tx.versions}
        all_values = {**versions, **pending}
        for v in tx.versions:
            d = attrs(v)
            ns = v.ref.identity.namespace
            if d.get("record_type") == "operation":
                old = heads.get(v.ref.identity)
                delta = d["spent"]-(attrs(old)["spent"] if old else 0)
                actor = d["actor"]
                spent[actor] = spent.get(actor, 0)+delta
                if d.get("u6") and d["purpose"] in ("attention", "rest") and d["status"] == "succeeded":
                    attentions.setdefault(actor, []).append(d["purpose"])
                if d["status"] == "succeeded" and d["primitive"] == "read":
                    receipt = next(x for x in tx.versions if x.ref.identity.namespace == "u4.receipt")
                    read.setdefault(actor, set()).add(attrs(receipt)["input.0"])
                if d.get("u6_prediction") and d["status"] in ("succeeded", "failed"):
                    pred = versions[d["u6_prediction"]]
                    a, pd = pred.facet(Account), attrs(pred)
                    if a.holder != actor or pd["kind"] != d["primitive"] or a.referent != d["target"]:
                        raise ValueError("action does not match its own hypothetical continuation")
                    if d["u6_plan"] != pd["plan"] or d["u6_forecast"] not in versions:
                        raise ValueError("action lost paid plan/forecast lineage")
                    counts["anticipated_actions"] += 1
            if ns == "u6.prediction":
                a = v.facet(Account)
                job = versions[d["operation"]]
                jd = attrs(job)
                completed = next((x for x in tx.versions if x.previous == job.ref), None)
                if (v.occurrence != Occurrence.HYPOTHETICAL or jd.get("purpose") != "anticipate"
                    or jd["status"] != "ready" or completed is None or attrs(completed)["status"] != "succeeded"
                    or jd["actor"] != a.holder or d["actor"] != a.holder):
                    raise ValueError("hypothesis was unpaid, foreign or promoted to truth")
                plan = versions[d["plan"]].facet(Account)
                if plan.holder != a.holder or plan.referent != a.referent or d["depth"] > jd["horizon"]:
                    raise ValueError("forecast has wrong plan, actor, target or horizon")
                counts["predictions"] += 1
            if ns == "u6.prediction_error":
                actor = d["actor"]
                obs = versions[d["observation"]]
                od = attrs(obs)
                prior = states[actor]
                if (obs.ref not in read.get(actor, set()) or obs.occurrence != Occurrence.OBSERVATION
                    or od["event"] != d["event"] or prior["await_event"] != d["event"]
                    or od["actor"] != actor or od["context"] != d["context"]):
                    raise ValueError("prediction error used unseen or unrelated result")
                expected = {} if d["prediction"] is None else {
                    p.relation: p.object for p in versions[d["prediction"]].facet(Account).content}
                assessed = tuple(k for k in ("outcome", "condition", "wear") if k in expected and k in od)
                errors = tuple(k for k in assessed if expected[k] != od[k])
                if (d["assessed"] != ",".join(assessed) or d["errors"] != ",".join(errors)
                    or d["surprise"] != bool(errors) or any(d.get("expected."+k) != val
                    or d.get("observed."+k) != od.get(k) for k, val in expected.items())):
                    raise ValueError("prediction error differs from delivered evidence")
                appraisals.setdefault(actor, []).append(od)
                counts["appraisals"] += 1
                counts["surprises"] += int(bool(errors))
            if ns == "u6.request":
                job = versions[d["paid_attention"]]
                jd = attrs(job)
                if jd.get("purpose") != "attention" or jd["status"] != "succeeded" or jd["actor"] != d["sender"]:
                    raise ValueError("unpaid or foreign assistance request")
                counts["requests"] += 1
            if ns == "u6.state":
                actor = d["actor"]
                prior = states.get(actor)
                if prior:
                    paid = spent.get(actor, 0)
                    attention = attentions.get(actor, [])
                    if d["turns"]-prior["turns"] != len(attention) or len(attention) > 1:
                        raise ValueError("scheduling opportunity bypassed paid attention")
                    expected_fatigue = max(0, prior["fatigue"]+paid-1-30) if attention == ["rest"] else prior["fatigue"]+paid
                    if d["fatigue"] != expected_fatigue:
                        raise ValueError("fatigue lacks work/rest cause")
                    if attention == ["rest"]:
                        counts["rests"] += 1
                        # Other native paid work can occur between scheduler
                        # snapshots. Each rest job's one-unit extent was checked
                        # above; total spending here includes that earlier work.
                        if paid < 1 or d["decision"] != "rest":
                            raise ValueError("rest has undeclared resource effects")
                    observations = appraisals.get(actor, [])
                    uses = sum(o.get("primitive") == "use" and o.get("outcome") == "succeeded"
                        and o.get("target") is not None and o["target"].identity == d["target"].identity for o in observations)
                    failures = sum(o.get("outcome") != "succeeded" for o in observations)
                    if d["uses"] != prior["uses"]+uses or d["failures"] != prior["failures"]+failures:
                        raise ValueError("need or goal progress without observed work")
                    if any(not 0 <= d[k] <= 10 for k in ("pressure", "fear", "scarcity", "boredom")):
                        raise ValueError("need exceeded its limited declared range")
                states[actor] = d
                spent[actor], attentions[actor], appraisals[actor] = 0, [], []
                counts["continuation_states"] += 1
        versions.update(pending)
        heads.update({v.ref.identity: v for v in tx.versions})
    result.update(counts)
    return result
