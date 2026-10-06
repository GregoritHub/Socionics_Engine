"""U5 integration on the U4 paid lifecycle, object store, and access authority.

Policies receive ParticipantView only. Frozen recall, Model A route work,
Crux content realization, and retained interpretation share one operation.
The native U4 entry points remain a compatibility API for trusted simulation.
"""
from dataclasses import fields
from hle.model_a import TYPES, element_at
from . import codec
from .compact import ValuePool, seal, unseal
from .records import (ObjectRef, ObjectVersion, Role, Account, Definition,
                      Occurrence, ClaimStatus, Proposition, TimeScope, Moment)
from .store import next_version
from .material import OperationStore, attrs, attributes
from .operations import OperationEngine, address, job_address, record, indexed
from .operation_records import OperationRequest, WRITER
from .cognitive_records import CognitiveRequest, registry, catalog
from .cognitive_routes import route, flatten_route, progress
from .cognitive_content import derive, plan_request


def profile_address(actor):
    return address("u5.profile", actor)


def profile(actor, tim):
    if tim not in TYPES:
        raise ValueError("known Model A type required")
    return record(profile_address(actor), "Model A processing profile", {
        "actor": actor, "tim": tim, "initial_active": element_at(tim, 1)})


class CognitiveEngine(OperationEngine):
    SCHEMA = "hle-unified-u5-engine-v1"

    def __init__(self, world, law):
        super().__init__(world, law)
        self._pool = ValuePool(registry())
        self._cognitive_inputs, self._cursors, self._profiles = {}, {}, {}
        self._plan_stamps = {}
        for identity in world._heads:
            if identity.namespace == "u5.profile":
                value = world.head(identity)
                p = attrs(value)
                if (value.ref != profile_address(p["actor"]) or p["tim"] not in TYPES
                        or p["initial_active"] != element_at(p["tim"], 1)):
                    raise ValueError("invalid immutable Model A profile")
                self._profiles[p["actor"]] = value.ref
                self._cursors[p["actor"]] = p["initial_active"]
        self._references = {v.ref: v for v in catalog()}
        for ref, value in self._references.items():
            if world.resolve(ref) != value:
                raise ValueError("source reference catalog differs from supplied meanings")

    def enact(self, cid, actor, key, plan):
        """Execute the actor's paid plan, retaining the conceptual causal input."""
        return self._execute(("enact", cid, actor, key, plan))

    def _execute(self, command):
        with self._lock:
            if type(command) is not tuple or len(command) < 2 or type(command[1]) is not str or not command[1].strip():
                raise ValueError("command identity required")
            cid = command[1]
            if cid in self._commands:
                prior, result = self._commands[cid]
                if prior != command:
                    raise ValueError("command identity reused with different content")
                return result
            ValuePool(registry()).put(command)
            dispatch = {"start": self._start, "advance": self._advance,
                "commit": self._commit, "cancel": self._cancel, "enact": self._enact,
                "disclose": self._disclose, "deliver_event": self._deliver_event,
                "declare": self._declare}
            if command[0] not in dispatch:
                raise ValueError("unsupported operation command")
            result = dispatch[command[0]](*command[1:])
            self._commands[cid] = command, result
            self._events.append(self._pool.put((command, result)))
            return result

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u5.") for v in versions):
            raise ValueError("U5 generated state and source identities cannot be imported as drafts")
        return super()._declare(cid, versions)

    def _start(self, cid, request):
        if type(request) is not CognitiveRequest:
            return super()._start(cid, request)
        r = request
        if r.actor not in self._profiles or r.actor not in self._wallets or (r.actor, r.key) in self._jobs:
            raise ValueError("funded typed actor and unused operation key required")
        if r.actor in self._locks:
            raise ValueError("finish or cancel this actor's existing cognitive work")
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if any(ref not in known for ref in (r.context, r.cue, r.target, r.rule)):
            raise ValueError("cognitive anchors must already be accessible")
        if r.cue not in self._references or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("stable source cue and context required")
        result = derive(view, r)
        tim = attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        origin, destination, polarity = (("I", "IT", "expenditure") if r.purpose == "plan"
                                          else ("IT", "I", "accumulation"))
        elements = r.elements or (("fi", "si") if r.purpose == "plan" else ("si", "fi"))
        rows = route(tim, self._cursors[r.actor], elements, origin, destination, polarity)
        recall_units = max(1, len(result["traversal"].visited) + len(r.evidence))
        route_units = sum(sum(row["charges"]) + row["content_units"] for row in rows)
        # The ordinary operation fields preserve U4 event, work and audit shapes.
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        d.update(record_type="operation", primitive="bind", u5=True, purpose=r.purpose,
            cue=r.cue, target=r.target, rule=r.rule, relation=result["relation"],
            required=recall_units+route_units, completed=0, spent=0,
            recall_units=recall_units, route_prepare=recall_units, route_execute=route_units,
            status="pending", failure=None, result=None, started_tick=self._now().tick,
            active_start=self._cursors[r.actor], tim=tim, origin=origin,
            destination=destination, polarity=polarity, visit_limit=r.visit_limit,
            **flatten_route(rows))
        sources = tuple(dict.fromkeys(view.detail(a).source for a in result["addresses"]))
        inputs = tuple(dict.fromkeys((r.target, r.cue, r.context, r.rule,
                    self._profiles[r.actor], *sources, *result["traversal"].visited)))
        for prefix, values in (("participant.", (r.actor,)), ("input.", inputs),
                ("dependency.", (r.rule, r.cue, self._profiles[r.actor], self.law)),
                ("lock.", (r.actor,)), ("recalled.", result["traversal"].visited)):
            d.update({prefix+str(i): x for i, x in enumerate(values)})
        for i, a in enumerate(result["addresses"]):
            d[f"evidence.delivery.{i}"], d[f"evidence.key.{i}"] = a.delivery, a.key
        ref = job_address(r.actor, r.key)
        self._batch(cid, r.actor, (record(ref, "Paid conceptual " + r.purpose, d),), evidence=inputs)
        self._jobs[r.actor, r.key] = ref
        self._reserve(d, ref)
        self._cognitive_inputs[ref.identity] = r, view
        return ref

    def _advance(self, cid, actor, key, work_limit):
        ref = super()._advance(cid, actor, key, work_limit)
        d = attrs(self.world.resolve(ref))
        if d.get("u5"):
            self._cursors[actor] = progress(d)[0]
        return ref

    def _enact(self, cid, actor, key, plan):
        view = self.participant_view(actor)
        request = plan_request(view, plan, key)
        # Only a plan emitted by this paid engine can serve as authorization.
        value = self.world.resolve(plan)
        receipts = [b.receipt for b in view.snapshot.bindings if b.ref == plan]
        if value.writer != WRITER or len(receipts) != 1:
            raise ValueError("native paid plan evidence required")
        retained = next(b for b in view.snapshot.bindings if b.ref == plan)
        if self._plan_stamps.get(plan) != self._binding_stamp(view, retained.context):
            raise ValueError("conceptual account changed after this plan; plan again")
        data = self._compile(request)
        data["concept_plan"], data["plan_receipt"] = plan, receipts[0]
        data["input." + str(len(indexed(data, "input.")))] = plan
        # A newer interpretation or plan makes old executable intent stale.
        data["dependency." + str(len(indexed(data, "dependency.")))] = plan
        for binding in view.snapshot.bindings:
            if (binding.ref.identity.namespace == "u5.account" and binding.target.identity == value.facet(Account).referent.identity
                    and binding.context == request.context and view._heads[binding.ref.identity].ref == binding.ref):
                data["dependency." + str(len(indexed(data, "dependency.")))] = binding.ref
        ref = job_address(actor, key)
        data["status"] = "pending" if self._can_reserve(data, ref) else "waiting"
        self._batch(cid, actor, (record(ref, "Enact conceptual plan", data),), evidence=indexed(data, "input."))
        self._jobs[actor, key] = ref
        if data["status"] == "pending":
            self._reserve(data, ref)
        return ref

    @staticmethod
    def _binding_stamp(view, context):
        return tuple(sorted(b.ref for b in view._heads.values() if b.context == context))

    def _commit(self, cid, actor, key):
        old, data = self._active(actor, key)
        if not data.get("u5"):
            return super()._commit(cid, actor, key)
        if data["status"] != "ready":
            raise ValueError("full recall and realization work required")
        request, view = self._cognitive_inputs[old.ref.identity]
        live = self.participant_view(actor)
        failure = None
        if any(self.world.head(ref.identity).ref != ref for ref in indexed(data, "dependency.")):
            failure = "stale_dependency"
        elif (live.traverse(request.cue, request.context, visit_limit=request.visit_limit).visited
              != view.traverse(request.cue, request.context, visit_limit=request.visit_limit).visited):
            failure = "changed_actor_recall"
        changed, command = [], None
        if failure is None:
            result = derive(view, request)
            identity = address("u5.plan" if request.purpose == "plan" else "u5.account",
                actor, request.cue, request.context, request.target.identity, result["relation"]).identity
            prior = live._heads.get(identity)
            ref = ObjectRef(identity, 1 if prior is None else prior.ref.revision+1)
            sources = tuple(dict.fromkeys(view.detail(a).source for a in result["addresses"]))
            binding_data = {"cue": request.cue, "context": request.context,
                "meaning": f"{request.purpose}: {result['relation']}; {result['status']}; {result['tension']}",
                "endorsement": ClaimStatus.ENDORSED.value if result["claim"] else ClaimStatus.TENTATIVE.value,
                "confidence": None}
            binding_data.update({"link."+str(i): x for i, x in enumerate(result["traversal"].visited)})
            binding = ObjectVersion(ref, WRITER, "Situated " + request.purpose, (Role.INTERPRETATION,),
                (Account(result["target"], result["content"], self._now(), actor, sources),),
                previous=None if prior is None else prior.ref, occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(binding_data))
            receipt_data = {"actor": actor, "operation": "bind", "work_key": ref.identity.key,
                **{k: data[k] for k in ("required", "completed", "spent")}}
            receipt_data.update({"input."+str(i): x for i, x in enumerate((ref,)+sources)})
            receipt = record(address("u4.receipt", cid), "Paid U5 realization receipt", receipt_data)
            command = ("bind", actor, ref, result["addresses"], receipt.ref)
            self.access.preview(command, {ref: binding, receipt.ref: receipt})
            # A field records recalled tension; surfaces record actual content
            # transformations with their predecessor, evidence, and paid job.
            field = record(address("u5.field", cid), "Contextual conceptual field", {
                "operation": old.ref, "target": result["target"], "cue": request.cue,
                "context": request.context, "relation": result["relation"],
                "tension": result["tension"], "status": result["status"],
                "recalled_count": len(result["traversal"].visited),
                "observation_count": len(result["observed"]),
                **{"recalled."+str(i): x for i, x in enumerate(result["traversal"].visited)}})
            surfaces, predecessor = [], field.ref
            for i in range(data["route_count"]):
                prefix = f"route.{i}."
                destination = data[prefix+"destination"]
                if i == data["route_count"]-1:
                    content = result["content"]
                    responsibility = "executable_intent" if request.purpose == "plan" else "retained_account"
                elif destination == "WE":
                    content = tuple(p for p in result["content"] if p.relation == "u5.giver")
                    responsibility = "assistance_terms" if request.purpose == "plan" else "observed_participation"
                    if request.purpose == "integrate":
                        content = tuple(Proposition(result["target"], "observed.actor", p.value,
                            request.context, TimeScope(Moment(result["target"].revision, 0), None))
                            for a in request.evidence if (p := view.detail(a)).address.key == "actor")
                else:
                    content = () if result["claim"] is None else (result["claim"],)
                    responsibility = "referent_aligned_relation"
                surface_ref = address("u5.surface", cid, i)
                surface = ObjectVersion(surface_ref, WRITER, "Realized " + data[prefix+"name"], (Role.INTERPRETATION,),
                    (Account(result["target"], content, self._now(), actor, (predecessor, old.ref)+sources),),
                    occurrence=Occurrence.INTERPRETATION,
                    attributes=attributes({"origin": data[prefix+"origin"], "destination": destination,
                        "polarity": data["polarity"], "element": data[prefix+"element"],
                        "operation": old.ref, "predecessor": predecessor, "responsibility": responsibility,
                        "retained": ref if i == data["route_count"]-1 else None}))
                surfaces.append(surface)
                predecessor = surface_ref
            changed = [binding, receipt, field, *surfaces]
            data.update(binding=ref, field=field.ref, surface=predecessor)
        outcome = "succeeded" if failure is None else "failed"
        event = self._event(cid, old, outcome)
        data.update(status=outcome, failure=failure, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(data))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,))
        if command:
            self.access._execute(command)
            if request.purpose == "plan":
                self._plan_stamps[data["binding"]] = self._binding_stamp(self.participant_view(actor), request.context)
        self._jobs[actor, key] = current.ref
        self._release(data, old.ref)
        return event.ref

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"initial", "law", "nodes", "commands", "world", "access"}:
            raise ValueError("invalid cognitive checkpoint")
        result = cls(OperationStore.restore(data["initial"]), codec.decode(data["law"]))
        raw = ValuePool(registry())
        raw.load_nodes(data["nodes"])
        for token in data["commands"]:
            command, expected = raw.get(raw.import_token(token))
            if result._execute(command) != expected:
                raise ValueError("cognitive result replay mismatch")
        if result.world.checkpoint() != data["world"] or result.access.checkpoint() != data["access"]:
            raise ValueError("cognitive, material or access replay mismatch")
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("noncanonical cognitive command history")
        return result
