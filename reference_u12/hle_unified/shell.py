"""Paid U7 attribution, contextual encounter, and U6 forecast integration.

The engine is a trusted simulator service. Policies see detached participant
information and owned patterns; offline assessment is never imported here.
"""
from dataclasses import fields, replace
from . import codec
from .compact import ValuePool, seal, unseal
from .records import ObjectRef, ObjectVersion, Role, Account, Occurrence, ClaimStatus, Proposition, TimeScope
from .material import OperationStore, attrs, attributes
from .store import next_version
from .operations import record, address, job_address, indexed
from .operation_records import OperationRequest, WRITER
from .autonomy import AutonomousEngine
from .autonomy_records import ForecastRequest
from .anticipation import forecast, choose
from .cognitive_routes import route, flatten_route, progress
from .shell_records import (Effect, Pattern, PatternPolicy, PatternSeed, EncounterRequest,
                            LAW7, world_contract, registry)
from .shell_policy import facts, applicable, encounter, deform_forecast


class ShellEngine(AutonomousEngine):
    SCHEMA = "hle-unified-u7-engine-v1"

    @staticmethod
    def _registry():
        return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._pool = ValuePool(self._registry())
        self._pattern_policies, self._patterns, self._pattern_index = {}, {}, {}
        self._encounters, self._feedback, self._experienced = {}, {}, set()
        self._last_bindings, self._last_encounters = {}, {}

    def configure_patterns(self, cid, policy):
        return self._execute(("configure_patterns", cid, policy))

    def inject_pattern_fixture(self, cid, seed):
        return self._execute(("inject_pattern_fixture", cid, seed))

    def pattern_view(self, actor):
        """Frozen owned attributions only. No global assessment or other owner."""
        return tuple(p for p in self._patterns.values() if p.owner == actor)

    def _execute(self, command):
        with self._lock:
            if type(command) is not tuple or len(command) < 2 or type(command[1]) is not str or not command[1].strip():
                raise ValueError("command identity required")
            cid = command[1]
            if cid in self._commands:
                old, result = self._commands[cid]
                if old != command:
                    raise ValueError("command identity reused with different content")
                return result
            ValuePool(self._registry()).put(command)
            dispatch = {"start": self._start, "advance": self._advance, "commit": self._commit,
                "cancel": self._cancel, "enact": self._enact, "disclose": self._disclose,
                "deliver_event": self._deliver_event, "declare": self._declare,
                "configure": self._configure, "opportunity": self._step,
                "configure_patterns": self._configure_patterns,
                "inject_pattern_fixture": self._inject_pattern_fixture}
            if command[0] not in dispatch:
                raise ValueError("unsupported U7 command")
            result = dispatch[command[0]](*command[1:])
            if command[0] == "opportunity" and result is None:
                return None
            self._commands[cid] = command, result
            self._events.append(self._pool.put((command, result)))
            return result

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u7.") for v in versions):
            raise ValueError("U7 execution and pattern history cannot be supplied as drafts")
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        value = self.world.resolve(source)
        d = attrs(value)
        if (source.identity.namespace.startswith("u7.") and source != LAW7
                and d.get("owner", d.get("actor")) not in (None, actor)):
            raise ValueError("private attribution needs an explicit recipient observation")
        return super()._disclose(cid, actor, source, selectors, subject)

    def _configure_patterns(self, cid, policy):
        if type(policy) is not PatternPolicy or policy.actor not in self._profiles or policy.actor in self._pattern_policies:
            raise ValueError("one attribution policy per typed actor")
        versions = []
        if LAW7.identity not in self.world._heads:
            versions.append(world_contract())
        elif self.world.resolve(LAW7) != world_contract():
            raise ValueError("pattern contract mismatch")
        value = record(address("u7.policy", policy.actor), "Declared attribution policy",
            {"actor": policy.actor, "generate": policy.generate, "threshold": policy.threshold, "contract": LAW7})
        self._batch(cid, policy.actor, (*versions, value))
        self._pattern_policies[policy.actor] = policy
        return value.ref

    @staticmethod
    def _pattern_record(p):
        data = {k: getattr(p, k) for k in ("owner", "origin", "context", "cue", "trigger", "origin_mode")}
        data.update(contract=LAW7, **{"source."+str(i): s for i, s in enumerate(p.evidence)})
        for i, e in enumerate(p.effects):
            for name in ("kind", "route", "amount"):
                data[f"effect.{i}.{name}"] = getattr(e, name)
        return record(p.ref, "Reusable actor attribution", data)

    def _index_pattern(self, p):
        self._patterns[p.ref] = p
        self._pattern_index.setdefault((p.owner, p.context, p.cue, p.trigger), []).append(p.ref)

    def _owned_matches(self, actor, context, cue, known):
        return tuple(self._patterns[r] for r in self._pattern_index.get(
            (actor, context, cue, known.get("trigger")), ()))

    def _effective_matches(self, actor, target, context, cue, known):
        """Default-preserving hook for later paid, actor-owned development."""
        return self._owned_matches(actor, context, cue, known)

    def _inject_pattern_fixture(self, cid, seed):
        if type(seed) is not PatternSeed or seed.actor not in self._pattern_policies or not seed.effects or not seed.evidence:
            raise ValueError("explicit owned detector fixture with evidence required")
        view = self.participant_view(seed.actor)
        known = self.access._known_refs(seed.actor)
        if any(r not in known for r in (seed.context, seed.cue, seed.trigger, seed.origin)):
            raise ValueError("fixture anchors must be accessible to its owner")
        details = tuple(view.detail(a) for a in seed.evidence)
        if any(p is None for p in details):
            raise ValueError("fixture evidence must already be processed")
        p = Pattern(address("u7.pattern", seed.actor, cid), seed.actor, seed.origin,
            seed.context, seed.cue, seed.trigger, seed.effects,
            tuple(dict.fromkeys(x.source for x in details)), "injected_fixture")
        self._batch(cid, p.owner, (self._pattern_record(p),), evidence=p.evidence)
        self._index_pattern(p)
        return p.ref

    def _stamp(self, view, request):
        known, sources = facts(view, request.target, request.context)
        recalled = view.traverse(request.cue, request.context, visit_limit=request.visit_limit)
        return (known, sources, recalled.visited,
                self._effective_matches(request.actor, request.target, request.context, request.cue, known))

    def _start(self, cid, request):
        if type(request) is not EncounterRequest:
            return super()._start(cid, request)
        r = request
        if r.actor not in self._pattern_policies or (r.actor, r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("configured actor with an unused key and no competing cognitive work required")
        view = self.participant_view(r.actor)
        known_refs = self.access._known_refs(r.actor)
        if any(x not in known_refs for x in (r.target, r.context, r.cue, r.carrier, r.bearer)):
            raise ValueError("encounter roles must be accessible exact references")
        if r.cue not in self._references or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("source cue and context required")
        known, sources = facts(view, r.target, r.context, r.evidence)
        if known.get("trigger") is not None and known["trigger"] not in known_refs:
            raise ValueError("trigger identity must be accessible")
        recalled = view.traverse(r.cue, r.context, visit_limit=r.visit_limit)
        matches = self._effective_matches(r.actor, r.target, r.context, r.cue, known)
        decision = encounter(r, known, matches, recalled.truncated)
        tim = attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows = route(tim, self._cursors[r.actor], ("fi", "si"), "I", "IT", "expenditure")
        recall_units = max(1, len(r.evidence)+len(recalled.visited))
        effect_units = sum(len(p.effects) for p in matches)
        route_units = sum(sum(row["charges"])+row["content_units"] for row in rows)
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        d.update(record_type="operation", primitive="bind", u7=True, purpose="encounter",
            target=r.target, cue=r.cue, carrier=r.carrier, bearer=r.bearer, demand=r.demand,
            requested_route=r.route, required=recall_units+effect_units+route_units, completed=0, spent=0,
            recall_units=recall_units+effect_units, route_prepare=recall_units+effect_units, route_execute=route_units,
            status="pending", failure=None, result=None, active_start=self._cursors[r.actor],
            tim=tim, origin="I", destination="IT", polarity="expenditure", contract=LAW7,
            started_tick=self._now().tick, truncated=recalled.truncated, **flatten_route(rows))
        d.update(evidence_count=len(r.evidence), recalled_count=len(recalled.visited), effect_units=effect_units,
                 **{"recalled."+str(i): ref for i, ref in enumerate(recalled.visited)})
        inputs = tuple(dict.fromkeys((r.target, r.context, r.cue, r.carrier, r.bearer,
            self._profiles[r.actor], LAW7, *sources, *recalled.visited, *(p.ref for p in matches))))
        for prefix, values in (("input.", inputs), ("participant.", (r.actor,)), ("lock.", (r.actor,)),
                ("dependency.", (LAW7, self.law, r.cue, self._profiles[r.actor]))):
            d.update({prefix+str(i): x for i, x in enumerate(values)})
        ref = job_address(r.actor, r.key)
        self._batch(cid, r.actor, (record(ref, "Paid situated encounter", d),), evidence=inputs)
        self._jobs[r.actor, r.key] = ref
        self._reserve(d, ref)
        self._encounters[ref.identity] = r, view, known, sources, matches, decision, self._stamp(view, r)
        return ref

    def _advance(self, cid, actor, key, work_limit):
        result = super()._advance(cid, actor, key, work_limit)
        data = attrs(self.world.resolve(result))
        if data.get("u7"):
            self._cursors[actor] = progress(data)[0]
        return result

    def _commit(self, cid, actor, key):
        old, data = self._active(actor, key)
        if not data.get("u7"):
            result = super()._commit(cid, actor, key)
            if data.get("u6") and data.get("purpose") == "anticipate" and self.job_status(actor, key)["status"] == "succeeded":
                self._record_forecast_application(cid, actor, key, old)
            return result
        if data["status"] != "ready":
            raise ValueError("complete paid encounter required")
        r, view, known, sources, matches, decision, stamp = self._encounters[old.ref.identity]
        failure = None
        if any(self.world.head(ref.identity).ref != ref for ref in indexed(data, "dependency.")):
            failure = "stale_dependency"
        elif stamp != self._stamp(self.participant_view(actor), r):
            failure = "changed_actor_encounter"
        event = self._event(cid, old, "succeeded" if failure is None else "failed")
        changed, access_command = [], None
        generated, feedback_key, feedback_entry = None, None, None
        if failure is None:
            eref = address("u7.encounter", actor, key)
            ed = {"actor": actor, "target": r.target, "context": r.context, "cue": r.cue,
                "carrier": r.carrier, "bearer": r.bearer, "operation": old.ref, "demand": r.demand,
                "requested_route": r.route, "spent": data["spent"], "truncated": data["truncated"],
                **{k: v for k, v in decision.items() if k != "applied"},
                **{"known."+k: v for k, v in known.items()},
                **{"source."+str(i): s for i, s in enumerate(sources)},
                **{"pattern."+str(i): p for i, p in enumerate(decision["applied"])}}
            changed.append(record(eref, "Realized situated intention", ed))
            # One actor-owned association retains target, role bindings, content,
            # cost and causal lineage. It grants no physical affordance or skill.
            bref = address("u7.binding", actor, r.target.identity, r.context, r.cue)
            prior = self._last_bindings.get((actor, r.target.identity, r.context, r.cue))
            if prior:
                bref = ObjectRef(bref.identity, prior.revision+1)
            content = tuple(Proposition(r.target, "u7."+name, value, r.context, TimeScope(self._now(), None))
                for name, value in decision.items() if name in ("route", "salience", "forecast_risk", "obligation", "approval", "excluded"))
            binding = ObjectVersion(bref, WRITER, "Situated attribution and intention", (Role.INTERPRETATION,),
                (Account(r.target, content, self._now(), actor,
                    tuple(dict.fromkeys(view.detail(a).source for a in r.evidence))),), previous=prior,
                occurrence=Occurrence.INTERPRETATION, attributes=attributes({"cue": r.cue, "context": r.context,
                    "meaning": decision["reason"], "endorsement": ClaimStatus.TENTATIVE.value,
                    "confidence": None, **({"link.0": prior} if prior else {})}))
            receipt = record(address("u4.receipt", cid), "Paid situated attribution receipt",
                {"actor": actor, "operation": "bind", "work_key": bref.identity.key,
                 **{k: data[k] for k in ("required", "completed", "spent")},
                 **{"input."+str(i): s for i, s in enumerate((bref, *binding.facet(Account).sources))}})
            # Empty evidence can support uncertainty intent, but U3 binding needs
            # grounded particulars; no invented evidence is supplied in its place.
            if r.evidence:
                access_command = ("bind", actor, bref, r.evidence, receipt.ref)
                self.access.preview(access_command, {bref: binding, receipt.ref: receipt})
            if access_command:
                changed.append(binding)
                data["binding"] = bref
            else:
                receipt = record(receipt.ref, "Paid uncertain encounter receipt", {
                    "actor": actor, "operation": "bind", "work_key": key,
                    **{k: data[k] for k in ("required", "completed", "spent")}, "input.0": eref})
            changed.append(receipt)
            data["encounter"] = eref
            policy = self._pattern_policies[actor]
            fresh = tuple(s for s in sources if (actor, s) not in self._experienced)
            if (policy.generate and fresh and r.demand and decision["base_route"] == "engage"
                    and known.get("feedback") == "blame"
                    and not self._owned_matches(actor, r.context, r.cue, known)):
                feedback_key = actor, r.context, r.cue, known["trigger"]
                feedback_entry = eref, fresh
                history = (*self._feedback.get(feedback_key, ()), feedback_entry)
                if len(history) >= policy.threshold:
                    mref = address("u7.material", actor, key)
                    material = record(mref, "Unresolved accountability tension", {
                        "owner": actor, "origin": eref, "target": r.target, "context": r.context,
                        "ownership": "externally_attributed", "content": "competent_action_can_still_receive_blame",
                        "carrier": r.carrier, "bearer": r.bearer,
                        **{"experience."+str(i): row[0] for i, row in enumerate(history)}})
                    generated = Pattern(address("u7.pattern", actor, key), actor, mref, r.context, r.cue,
                        known["trigger"], (Effect("approval"),), tuple(row[0] for row in history), "generated")
                    changed.extend((material, self._pattern_record(generated)))
            # Functional content crosses the same lawful Model A path as U5.
            predecessor = old.ref
            for i in range(data["route_count"]):
                prefix = f"route.{i}."
                sref = address("u7.surface", actor, key, i)
                changed.append(record(sref, "Realized encounter perspective", {
                    "actor": actor, "operation": old.ref, "predecessor": predecessor,
                    "origin": data[prefix+"origin"], "destination": data[prefix+"destination"],
                    "polarity": data[prefix+"polarity"], "content": eref,
                    **({"perceived_approval": decision["approval"], "perceived_obligation": decision["obligation"],
                        "anticipated_risk": decision["forecast_risk"]} if i == 0 else {"selected_intent": decision["route"]}),
                    "responsibility": "attributed_terms" if i == 0 else "executable_intention"}))
                predecessor = sref
        data.update(status="succeeded" if failure is None else "failed", failure=failure,
                    result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(data))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,))
        self._jobs[actor, key] = current.ref
        self._release(data, old.ref)
        if failure is None:
            if access_command:
                self.access._execute(access_command)
                self._last_bindings[actor, r.target.identity, r.context, r.cue] = data["binding"]
            self._last_encounters[actor, r.target.identity, r.context, r.cue] = data["encounter"]
            if feedback_entry:
                self._feedback.setdefault(feedback_key, []).append(feedback_entry)
                self._experienced.update((actor, s) for s in feedback_entry[1])
            if generated:
                self._index_pattern(generated)
        return event.ref

    def _forecast_policy(self, view, request):
        result = forecast(view, request)
        known, sources = facts(view, result["target"], request.config.context)
        matches = self._effective_matches(request.actor, result["target"], request.config.context, request.config.cue, known)
        result["u7_before"] = result["candidates"]
        return {**deform_forecast(result, matches, known), "u7_sources": sources,
                "u7_stamp": (known, sources, matches)}

    def _forecast_valid(self, view, request, result):
        known, sources = facts(view, result["target"], request.config.context)
        matches = self._effective_matches(request.actor, result["target"], request.config.context, request.config.cue, known)
        return result.get("u7_stamp") == (known, sources, matches)

    def _act(self, cid, state, row):
        result = self._forecast_results[state.forecast]
        c = self._configs[state.actor]
        r = ForecastRequest("validate", state.actor, state.plan, c)
        if not self._forecast_valid(self.participant_view(state.actor), r, result):
            return replace(state, phase="idle", forecast=None, plan=None), "switch", "accessible_attribution_changed"
        return super()._act(cid, state, row)

    def _choose_policy(self, result, config, need, wallet):
        eligible = tuple(r for r in result["candidates"] if r.get("eligible", True))
        return choose({**result, "candidates": eligible}, config, need, wallet)

    def _record_forecast_application(self, cid, actor, key, old):
        request, result, _ = self._forecast_inputs[old.ref.identity]
        if not result.get("u7_applied"):
            return
        c = request.config
        bref = self._last_bindings.get((actor, result["target"].identity, c.context, c.cue))
        eref = self._last_encounters.get((actor, result["target"].identity, c.context, c.cue))
        binding = attrs(self.world.resolve(eref)) if eref else {}
        data = {"actor": actor, "target": result["target"], "context": c.context, "cue": c.cue,
            "carrier": binding.get("carrier", result["target"]),
            "bearer": binding.get("bearer", ObjectRef(actor, 1)), "binding": bref,
            "operation": old.ref, "forecast": self.job_status(actor, key)["forecast"],
            **{"pattern."+str(i): p for i, p in enumerate(result["u7_applied"])},
            **{"source."+str(i): p for i, p in enumerate(result["u7_sources"])}}
        for i, (before, after) in enumerate(zip(result["u7_before"], result["candidates"])):
            for name in ("kind", "utility", "risk", "outcome"):
                data[f"before.{i}.{name}"], data[f"after.{i}.{name}"] = before[name], after[name]
            data[f"after.{i}.eligible"] = after["eligible"]
        self._batch(cid+":attribution", actor,
            (record(address("u7.forecast_application", actor, key), "Attributed forecast consequences", data),),
            evidence=(old.ref, *result["u7_applied"]))

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"initial", "law", "nodes", "commands", "world", "access"}:
            raise ValueError("invalid U7 checkpoint")
        result = cls(OperationStore.restore(data["initial"]), codec.decode(data["law"]))
        raw = ValuePool(cls._registry())
        raw.load_nodes(data["nodes"])
        for token in data["commands"]:
            command, expected = raw.get(raw.import_token(token))
            if result._execute(command) != expected:
                raise ValueError("U7 command replay mismatch")
        if result.world.checkpoint() != data["world"] or result.access.checkpoint() != data["access"]:
            raise ValueError("U7 world or access replay mismatch")
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("noncanonical U7 history")
        return result
