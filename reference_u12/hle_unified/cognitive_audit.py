"""Independent audit of raw paid routes, material effects and evidence lineage.

Does not call cognitive planning, content derivation, progression, or engine
indexes. Reuses the inherited independent material/accounting auditor through
an explicit extent validator. Source geometry is the shared specification.
"""
from hle.model_a import neighbors, position_of, fields, position, jungian, element_at
from hle.concept_structure import EDGES
from hle.crux import Perspective, Route, CODE
from . import codec
from .records import Account, Occurrence, ObjectRef
from .operation_audit import audit_transactions, data, indexed


def audit_extent(d):
    current, active = Perspective(d["origin"]), d["active_start"]
    total = 0
    for i in range(d["route_count"]):
        p = f"route.{i}."
        e, tim = d[p+"element"], d["tim"]
        ends = EDGES[e[0]]
        if current not in ends or d[p+"origin"] != current.value:
            raise ValueError("unlawful Fold origin")
        destination = ends[1] if current == ends[0] else ends[0]
        if d[p+"destination"] != destination.value or d[p+"name"] != Route(current,destination).name:
            raise ValueError("unlawful Fold destination")
        seat = position_of(tim,e)
        if d[p+"seat"] != seat or d[p+"dimensionality"] != fields(seat)["dimensionality"]:
            raise ValueError("type seat or fixed dimensionality mismatch")
        if indexed(d,p+"position.") != position(seat) or indexed(d,p+"type_coordinates.") != jungian(tim):
            raise ValueError("confused Model A coordinates")
        if d[p+"origin_bits"] != CODE[current] or d[p+"destination_bits"] != CODE[destination]:
            raise ValueError("invalid perspective coordinates")
        path, charges = indexed(d,p+"path."), indexed(d,p+"charges.")
        if not path or path[0] != active or path[-1] != e or len(charges) != len(path)-1:
            raise ValueError("invalid processing path endpoints")
        supports = (5,7) if d["polarity"] == "accumulation" else (6,8)
        if d[p+"polarity"] != d["polarity"] or d[p+"support_seat"] not in supports:
            raise ValueError("wrong polarity support")
        at = d[p+"support_at"]
        if not 0 <= at < len(path) or path[at] != element_at(tim,d[p+"support_seat"]):
            raise ValueError("processing skipped its support seat")
        for a,b,charge in zip(path,path[1:],charges):
            if b not in neighbors(tim,a) or charge != 5-fields(position_of(tim,b))["dimensionality"]:
                raise ValueError("invalid or unpaid Model A hop")
        content = 5-fields(seat)["dimensionality"]
        if d[p+"content_units"] != content:
            raise ValueError("invalid content price")
        total += sum(charges)+content
        current, active = destination, e
    if current.value != d["destination"] or d["route_count"] < 1:
        raise ValueError("incomplete perspective composition")
    if (d["required"] != d["recall_units"]+total or d["recall_units"] < 1
            or d["route_execute"] != total or d["route_prepare"] != d["recall_units"]):
        raise ValueError("conceptual work extent is not the sum of performed stages")


def audit(transactions, *, extent_check=audit_extent):
    result = audit_transactions(transactions,extent_check=extent_check)
    versions, read, retained = {}, {}, {}
    conceptual, surfaces, linked_actions = 0,0,0
    for tx in transactions:
        pending = {v.ref:v for v in tx.versions}
        for v in tx.versions:
            d = data(v)
            if d.get("record_type") != "operation" or d.get("status") != "succeeded":
                continue
            actor = d["actor"]
            if d["primitive"] == "read":
                receipt = next(x for x in tx.versions if x.ref.identity.namespace == "u4.receipt")
                read.setdefault(actor,set()).add(data(receipt)["input.0"])
            if d.get("concept_plan") is not None:
                plan = versions[d["concept_plan"]]
                if plan.facet(Account).holder != actor or d["concept_plan"] not in retained.get(actor,set()):
                    raise ValueError("action bypassed actor-owned paid conceptual output")
                actions = [p.object for p in plan.facet(Account).content if p.relation == "u5.action"]
                if actions != [d["primitive"]] or plan.facet(Account).referent != d["target"]:
                    raise ValueError("physical action does not realize its conceptual plan")
                linked_actions += 1
            if d.get("u5"):
                conceptual += 1
                binding = pending[d["binding"]]
                account = binding.facet(Account)
                if account.holder != actor or not set(account.sources) <= read.get(actor,set()):
                    raise ValueError("conceptual output used unprocessed or foreign evidence")
                recalled = indexed(d,"recalled.")
                if not set(recalled) <= retained.get(actor,set()):
                    raise ValueError("unowned or unretained recall input")
                claims = [p for ref in recalled for p in versions[ref].facet(Account).content
                    if p.subject.identity == d["target"].identity and p.context == d["context"]
                    and p.relation == d["relation"] and p.scope.end is None
                    and data(versions[ref])["endorsement"] not in ("retracted","disputed")]
                accounts = [versions[ref] for ref in recalled if ref.identity.namespace == "u5.account"
                    and data(versions[ref])["endorsement"] not in ("retracted","disputed")
                    and versions[ref].facet(Account).referent.identity == d["target"].identity
                    and data(versions[ref])["meaning"].startswith("integrate: " + d["relation"] + ";")]
                newest = max([p.subject.revision for p in claims]+[x.facet(Account).referent.revision for x in accounts],default=0)
                current = [x for x in accounts if x.facet(Account).referent.revision == newest]
                if current:
                    corrected = [[p for p in x.facet(Account).content if p.relation == d["relation"]] for x in current]
                    claims = [] if any(not values for values in corrected) else [p for values in corrected for p in values]
                observed = []
                if d["purpose"] == "integrate":
                    for source in account.sources:
                        value = versions[source]
                        sd = data(value)
                        target = sd.get("target")
                        if (value.occurrence == Occurrence.OBSERVATION and type(target) is ObjectRef
                                and target.identity == d["target"].identity and sd.get("context") == d["context"]
                                and sd.get("outcome") == "succeeded" and d["relation"] in sd):
                            observed.append((target.revision,sd[d["relation"]]))
                candidates = [(p.subject.revision,p.object) for p in claims]
                if observed and max(x[0] for x in observed) >= max((x[0] for x in candidates),default=0):
                    candidates = observed
                conclusions = [p for p in account.content if p.relation == d["relation"]]
                if conclusions:
                    top = max(x[0] for x in candidates)
                    values = {codec.dumps(x[1]) for x in candidates if x[0] == top}
                    if (len(conclusions) != 1 or len(values) != 1 or conclusions[0].subject.revision != top
                            or codec.dumps(conclusions[0].object) not in values):
                        raise ValueError("retained conclusion differs from accessible evidence")
                field = pending[d["field"]]
                chain = [x for x in tx.versions if x.ref.identity.namespace == "u5.surface"]
                predecessor = field.ref
                if len(chain) != d["route_count"]:
                    raise ValueError("missing realized perspective surface")
                for i,surface in enumerate(chain):
                    sd = data(surface)
                    if (sd["predecessor"] != predecessor or sd["operation"] != v.previous
                            or sd["origin"] != d[f"route.{i}.origin"]
                            or sd["destination"] != d[f"route.{i}.destination"]):
                        raise ValueError("disconnected perspective content")
                    predecessor = surface.ref
                if chain[-1].facet(Account).content != account.content or data(chain[-1])["retained"] != binding.ref:
                    raise ValueError("surface output not retained in account")
                surfaces += len(chain)
            if d["primitive"] == "bind" and d.get("binding") is not None:
                retained.setdefault(actor,set()).add(d["binding"])
        versions.update(pending)
    result.update(conceptual_commits=conceptual,realized_surfaces=surfaces,concept_linked_actions=linked_actions)
    return result
