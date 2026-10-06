"""Paid U8 local correction, response practice, retained organization and return.

Development never edits a U7 origin or deletes a pattern. Actual task outputs,
their delivery, practice retention and broader organization are separate acts.
"""
from dataclasses import fields, replace
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence,
                      ClaimStatus, Proposition, TimeScope)
from .material import attrs, attributes
from .store import next_version
from .operations import record as native_record, address, job_address, indexed
from .operation_records import OperationRequest, WRITER
from .cognitive_routes import route, flatten_route, progress
from .shell import ShellEngine
from .shell_records import EncounterRequest
from .shell_policy import encounter
from .development_records import DevelopmentRequest, LAW8, registry, world_contract
from .development_policy import opportunity, releasable, permits, learned_load
from .development_values import pack


def record(ref, label, values):
    return ObjectVersion(ref, WRITER, label, (Role.RECORD,), attributes=attributes(pack(values)),
                         previous=None if ref.revision == 1 else ObjectRef(ref.identity, ref.revision-1))


class DevelopmentEngine(ShellEngine):
    SCHEMA = "hle-unified-u8-engine-v1"

    @staticmethod
    def _registry():
        return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._development_inputs = {}
        self._corrections, self._capacities, self._practices = {}, {}, {}
        self._response_results, self._practiced_events, self._treatments = {}, set(), {}

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u8.") for v in versions):
            raise ValueError("development history cannot be imported as drafts")
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith("u8.") and source != LAW8:
            d = attrs(self.world.resolve(source))
            if d.get("actor", d.get("owner")) != actor:
                raise ValueError("private development requires an explicit recipient observation")
        return super()._disclose(cid, actor, source, selectors, subject)

    def development_view(self, actor):
        """Detached owned records. Assessment and other participants are excluded."""
        return {"corrections": tuple(dict(x) for x in self._corrections.values() if x["actor"] == actor),
                "capacities": tuple(dict(x) for x in self._capacities.values() if x["actor"] == actor),
                "practices": tuple(dict(x) for rows in self._practices.values() for x in rows if x["actor"] == actor),
                "treatments": tuple(dict(x) for x in self._treatments.values() if x["actor"] == actor)}

    def _selection(self, actor, target, context, cue, known, load, recalled):
        matches, bases = [], []
        for p in self._owned_matches(actor, context, cue, known):
            basis = permits(p, target, known, self._corrections, self._capacities.get(p.ref), load, recalled)
            if basis is None:
                matches.append(p)
            else:
                bases.append((p.ref, basis))
        return tuple(matches), tuple(bases)

    def _effective_matches(self, actor, target, context, cue, known):
        view = self.participant_view(actor)
        recalled = view.traverse(cue, context).visited
        return self._selection(actor, target, context, cue, known, 1, recalled)[0]

    def _derive(self, r, view):
        p = self._patterns.get(r.pattern)
        if p is None or (p.owner, p.context, p.cue) != (r.actor, r.context, r.cue):
            raise ValueError("owned pattern in its exact context and cue required")
        details = tuple(view.detail(a) for a in r.evidence)
        if any(x is None for x in details):
            raise ValueError("development evidence must already be processed by its actor")
        recalled = view.traverse(r.cue, r.context, visit_limit=r.visit_limit)
        sources = tuple(dict.fromkeys(x.source for x in details))
        result = {"sources": sources, "recalled": recalled.visited, "truncated": recalled.truncated,
                  "pattern": p, "rows": (), "examples": (), "max_load": 0}
        if r.purpose in ("release", "respond"):
            rows = []
            for target in r.targets:
                known, current = opportunity(view, target, r.context, r.evidence)
                # Evidence subsets cannot hide a later received revision or conflict.
                latest, latest_sources = opportunity(view, target, r.context)
                if (known, current) != (latest, latest_sources):
                    raise ValueError("all current received opportunity evidence is required")
                if r.purpose == "release":
                    if (recalled.truncated or not releasable(known) or known["approved"]
                            or known.get("trigger") != p.trigger
                            or any(e.kind not in ("approval", "obligation") for e in p.effects)):
                        raise ValueError("unsupported, incomplete or scaffolded local correction")
                matches, bases = self._selection(r.actor, target, r.context, r.cue, known,
                                                len(r.targets), recalled.visited)
                request = EncounterRequest(r.key, r.actor, target, r.context, r.cue,
                    r.partner or target, ObjectRef(r.actor, 1), r.evidence, demand=r.demand)
                decision = encounter(request, known, matches, recalled.truncated)
                if r.purpose == "respond" and known.get("partner") != r.partner:
                    decision.update(route="inspect", reason="unverified_partner")
                rows.append({"target": target, "known": known, "sources": current,
                             "decision": decision, "bases": bases})
            result["rows"] = tuple(rows)
        elif r.purpose == "practice":
            if r.observation.identity.namespace != "u4.observation":
                raise ValueError("native observed execution required")
            values = {x.address.key: x.value for x in details if x.source == r.observation}
            event = values.get("event")
            response = self._response_results.get(event)
            if response is None or (r.pattern, event) in self._practiced_events:
                raise ValueError("fresh actual response observation required")
            if (response["actor"], response["pattern"], response["context"], response["cue"], response["targets"], response["partner"]) != (
                    r.actor, r.pattern, r.context, r.cue, r.targets, r.partner):
                raise ValueError("practice actor, targets, partner and scope must match execution")
            expected = {"actor": r.actor, "event": event, "outcome": "succeeded",
                        "development_response": response["ref"], "completed_demand": response["completed_demand"],
                        "supported": response["supported"], "load": len(r.targets)}
            if any(values.get(k) != v for k, v in expected.items()):
                raise ValueError("complete processed response outcome required")
            result.update(response=response, observation=r.observation,
                independent=response["completed_demand"] and not response["supported"] and not recalled.truncated)
        else:
            examples = tuple(self._practices.get(r.pattern, ()))
            if recalled.truncated:
                raise ValueError("development recall is incomplete")
            usable = tuple(x for x in examples if x["independent"] and x["binding"] in recalled.visited)
            load = learned_load(usable)
            if not load:
                raise ValueError("two retained independent episodes over distinct targets required")
            capacity = self._capacities.get(r.pattern)
            if r.purpose == "reorganize":
                if capacity and tuple(x["ref"] for x in usable) == capacity["examples"]:
                    raise ValueError("no new independent practice to reorganize")
            else:
                if capacity is None or capacity["binding"] not in recalled.visited:
                    raise ValueError("accessible reusable organization required before reownership")
                # Returned episodes must use the organization, meet its load, and
                # include novel target(s) and a changed contextual partner.
                returned = tuple(x for x in usable if x["capacity"] == capacity["ref"]
                                 and len(x["targets"]) >= capacity["max_load"])
                trained = {t.identity for x in usable if x["ref"] in capacity["examples"] for t in x["targets"]}
                partners = {x["partner"] for x in usable if x["ref"] in capacity["examples"]}
                if (len(returned) < 2 or not any({t.identity for t in x["targets"]} - trained for x in returned)
                        or not any(x["partner"] not in partners for x in returned)):
                    raise ValueError("renewed independent returns with novel targets and changed partner required")
                if self._treatments.get(p.origin, {}).get("ownership") == "reowned":
                    raise ValueError("material is already reowned")
                usable = returned
            result.update(examples=usable, max_load=load, capacity=capacity)
        return result

    def _start(self, cid, request):
        if type(request) is not DevelopmentRequest:
            return super()._start(cid, request)
        r = request
        if r.actor not in self._pattern_policies or (r.actor, r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("configured actor, unused key and no competing work required")
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if any(x not in known for x in (*r.targets, r.context, r.cue, *((r.partner,) if r.partner else ()))):
            raise ValueError("development targets and contextual partner must be accessible")
        if r.cue not in self._references or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("source cue and context required")
        result = self._derive(r, view)
        tim = attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        outward = r.purpose == "respond"
        origin, destination, polarity = ("I", "IT", "expenditure") if outward else ("IT", "I", "accumulation")
        rows = route(tim, self._cursors[r.actor], ("fi", "si") if outward else ("si", "fi"), origin, destination, polarity)
        units = max(1, len(r.evidence) + len(result["recalled"]) + len(r.targets) + len(result["examples"]))
        route_units = sum(sum(x["charges"]) + x["content_units"] for x in rows)
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        data = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        data.update(record_type="operation", primitive="bind", u8=True, purpose=r.purpose,
            pattern=r.pattern, cue=r.cue, target=r.targets[0], partner=r.partner, demand=r.demand,
            required=units+route_units, completed=0, spent=0, recall_units=units,
            evidence_count=len(r.evidence), recalled_count=len(result["recalled"]),
            target_count=len(r.targets), example_count=len(result["examples"]),
            route_prepare=units, route_execute=route_units, status="pending", failure=None, result=None,
            active_start=self._cursors[r.actor], tim=tim, origin=origin, destination=destination,
            polarity=polarity, contract=LAW8, started_tick=self._now().tick,
            truncated=result["truncated"], observation=r.observation, **flatten_route(rows))
        inputs = tuple(dict.fromkeys((r.pattern, result["pattern"].origin, r.context, r.cue,
                    *r.targets, *result["sources"], *result["recalled"], *(x["ref"] for x in result["examples"]))))
        for prefix, values in (("input.", inputs), ("source.", result["sources"]), ("recalled.", result["recalled"]),
                ("target.", r.targets), ("participant.", (r.actor,)), ("lock.", (r.actor,)),
                ("dependency.", (self.law, r.cue, self._profiles[r.actor], LAW8))):
            data.update({prefix+str(i): x for i, x in enumerate(values)})
        for i, a in enumerate(r.evidence):
            data[f"evidence.delivery.{i}"], data[f"evidence.key.{i}"] = a.delivery, a.key
        ref = job_address(r.actor, r.key)
        added = () if LAW8.identity in self.world._heads else (world_contract(),)
        if not added and self.world.resolve(LAW8) != world_contract():
            raise ValueError("development contract mismatch")
        self._batch(cid, r.actor, (*added, record(ref, "Paid development: "+r.purpose, data)), evidence=inputs)
        self._jobs[r.actor, r.key] = ref
        self._reserve(data, ref)
        self._development_inputs[ref.identity] = r, view, result
        return ref

    def _advance(self, cid, actor, key, work_limit):
        ref = super()._advance(cid, actor, key, work_limit)
        data = attrs(self.world.resolve(ref))
        if data.get("u8"):
            self._cursors[actor] = progress(data)[0]
        return ref

    def _treatment(self, p, kind, carrier, target, evidence, operation):
        prior = self._treatments.get(p.origin)
        ref = address("u8.treatment", p.owner, p.origin)
        previous = None if prior is None else prior["ref"]
        if previous:
            ref = ObjectRef(ref.identity, previous.revision+1)
        data = {"ref": ref, "actor": p.owner, "pattern": p.ref, "origin": p.origin,
            "original_carrier": attrs(self.world.resolve(p.origin)).get("carrier"),
            "kind": kind, "ownership": "reowned" if kind == "reownership" else "externally_attributed",
            "carrier": None if kind == "reownership" else carrier, "target": target,
            "prior_carrier": None if prior is None else prior["carrier"],
            "operation": operation, "evidence": evidence}
        return replace(record(ref, "Continuing treatment of original material", data), previous=previous), data

    def _commit(self, cid, actor, key):
        old, data = self._active(actor, key)
        if not data.get("u8"):
            return super()._commit(cid, actor, key)
        if data["status"] != "ready":
            raise ValueError("complete paid development work required")
        r, view, result = self._development_inputs[old.ref.identity]
        failure = None
        if any(self.world.head(x.identity).ref != x for x in indexed(data, "dependency.")):
            failure = "stale_dependency"
        else:
            try:
                if self._derive(r, self.participant_view(actor)) != result:
                    failure = "changed_actor_development_input"
            except ValueError:
                failure = "changed_actor_development_input"
        changed, command, effect, treatment = [], None, None, None
        event = self._event(cid, old, "succeeded" if failure is None else "failed")
        if failure is None:
            p = result["pattern"]
            bref = address("u8.account", actor, key)
            common = {"actor": actor, "pattern": p.ref, "origin": p.origin, "context": r.context,
                "cue": r.cue, "trigger": p.trigger, "operation": old.ref, "binding": bref,
                "targets": r.targets, "partner": r.partner}
            if r.purpose == "release":
                previous = self._corrections.get((p.ref, r.targets[0]))
                ref = address("u8.correction", actor, p.ref, r.targets[0])
                if previous:
                    ref = ObjectRef(ref.identity, previous["ref"].revision+1)
                effect = {**common, "ref": ref, "target": r.targets[0], "approval_required": False,
                          "sources": result["sources"]}
                changed.append(replace(record(ref, "Local guarded correction", effect),
                    previous=None if previous is None else previous["ref"]))
                value, treatment = self._treatment(p, "local_release", r.partner or r.targets[0],
                    r.targets[0], ref, old.ref)
                changed.append(value)
            elif r.purpose == "respond":
                ref = address("u8.response", actor, key)
                supported = any(x["known"].get("approved", False) for x in result["rows"])
                completed = r.demand and all(x["decision"]["route"] == "engage"
                    and x["known"].get("trigger") == p.trigger for x in result["rows"])
                effect = {**common, "ref": ref, "event": event.ref, "demand": r.demand,
                    "load": len(r.targets), "supported": supported, "completed_demand": completed,
                    "truncated": result["truncated"]}
                for i, row in enumerate(result["rows"]):
                    effect.update({f"row.{i}.target": row["target"], f"row.{i}.route": row["decision"]["route"],
                        f"row.{i}.base_route": row["decision"]["base_route"], f"row.{i}.reason": row["decision"]["reason"],
                        f"row.{i}.patterns": row["decision"]["applied"], f"row.{i}.bases": row["bases"],
                        f"row.{i}.sources": row["sources"],
                        **{f"row.{i}.known."+k: v for k, v in row["known"].items()}})
                changed.append(record(ref, "Executed guarded responses", effect))
                ed = attrs(event)
                ed.update(development_response=ref, completed_demand=completed,
                          supported=supported, load=len(r.targets))
                event = replace(event, attributes=attributes(ed))
                residual = next((x for x in result["rows"] if x["decision"]["applied"]
                                 and x["decision"]["route"] != x["decision"]["base_route"]), None)
                if residual:
                    value, treatment = self._treatment(p, "displacement", r.partner or residual["target"],
                        residual["target"], ref, old.ref)
                    changed.append(value)
            elif r.purpose == "practice":
                response = result["response"]
                cap = self._capacities.get(p.ref)
                cap_used = cap is not None and all((p.ref, cap["ref"]) in response[f"row.{i}.bases"]
                                                     for i in range(response["load"]))
                ref = address("u8.practice", actor, key)
                effect = {**common, "ref": ref, "event": response["event"], "response": response["ref"],
                    "observation": r.observation, "independent": result["independent"],
                    "supported": response["supported"], "capacity": cap["ref"] if cap_used else None}
                changed.append(record(ref, "Retained observed practice", effect))
            elif r.purpose == "reorganize":
                previous = self._capacities.get(p.ref)
                ref = address("u8.capacity", actor, p.ref)
                if previous:
                    ref = ObjectRef(ref.identity, previous["ref"].revision+1)
                effect = {**common, "ref": ref, "max_load": result["max_load"],
                    "organization": "check_opportunity_then_engage",
                    "examples": tuple(x["ref"] for x in result["examples"])}
                changed.append(replace(record(ref, "Retained reusable organization", effect),
                    previous=None if previous is None else previous["ref"]))
            else:
                value, treatment = self._treatment(p, "reownership", None, r.targets[0],
                    result["capacity"]["ref"], old.ref)
                treatment["returns"] = tuple(x["ref"] for x in result["examples"])
                value = replace(value, attributes=attributes(pack(treatment)))
                changed.append(value)
                effect = treatment
            conclusion = {"release": False, "respond": effect.get("completed_demand", False),
                "practice": effect.get("independent", False), "reorganize": effect.get("max_load", 0),
                "reown": "reowned"}[r.purpose]
            content = (Proposition(r.targets[0], "u8."+r.purpose, conclusion, r.context, TimeScope(self._now(), None)),)
            binding = ObjectVersion(bref, WRITER, "Retained development content", (Role.INTERPRETATION,),
                (Account(r.targets[0], content, self._now(), actor, result["sources"]),),
                occurrence=Occurrence.INTERPRETATION, attributes=attributes({"cue": r.cue, "context": r.context,
                    "meaning": r.purpose, "endorsement": ClaimStatus.ENDORSED.value, "confidence": None}))
            receipt = record(address("u4.receipt", cid), "Paid development receipt", {
                "actor": actor, "operation": "bind", "work_key": bref.identity.key,
                **{k: data[k] for k in ("required", "completed", "spent")},
                **{"input."+str(i): s for i, s in enumerate((bref, *result["sources"]))}})
            command = ("bind", actor, bref, r.evidence, receipt.ref)
            self.access.preview(command, {bref: binding, receipt.ref: receipt})
            changed.extend((binding, receipt))
            predecessor = old.ref
            for i in range(data["route_count"]):
                sref = address("u8.surface", actor, key, i)
                changed.append(record(sref, "Realized development perspective", {
                    "actor": actor, "operation": old.ref, "predecessor": predecessor,
                    "origin": data[f"route.{i}.origin"], "destination": data[f"route.{i}.destination"],
                    "polarity": data[f"route.{i}.polarity"], "content": effect["ref"],
                    "responsibility": "received_evidence" if i == 0 else r.purpose,
                    "retained": bref if i == data["route_count"]-1 else None}))
                predecessor = sref
            data.update(binding=bref, development=effect["ref"])
        data.update(status="succeeded" if failure is None else "failed", failure=failure,
                    result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(data))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,))
        self._jobs[actor, key] = current.ref
        self._release(data, old.ref)
        if command:
            self.access._execute(command)
            if r.purpose == "release":
                self._corrections[r.pattern, r.targets[0]] = effect
            elif r.purpose == "respond":
                self._response_results[event.ref] = effect
            elif r.purpose == "practice":
                self._practices.setdefault(r.pattern, []).append(effect)
                self._practiced_events.add((r.pattern, effect["event"]))
            elif r.purpose == "reorganize":
                self._capacities[r.pattern] = effect
            if treatment:
                self._treatments[treatment["origin"]] = treatment
        return event.ref
