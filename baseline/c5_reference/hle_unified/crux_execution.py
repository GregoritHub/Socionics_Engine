"""C1 native content execution over the complete U14 engine.

One movement job owns real paid steps. Apply includes separately accounted
native inspection work, and completes only with the actual event. Embody
requires that event to have been delivered and paid-read by this actor.
"""
from dataclasses import fields, replace
from . import codec, crux_content as content
from .compact import seal, unseal
from .institutions import InstitutionEngine
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence,
                      Proposition, TimeScope, Moment, ClaimStatus)
from .operations import OperationEngine, address, job_address, record, indexed
from .operation_records import OperationRequest, WRITER
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route, progress
from .crux_records import MovementRequest, RECIPES, definition, registry


class CruxEngine(InstitutionEngine):
    SCHEMA = "hle-full-crux-c1-engine-v1"

    @staticmethod
    def _registry():
        return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._movement_inputs = {}
        self._movement_models = set()
        self._movement_trials = set()

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("c1.") for v in versions):
            raise ValueError("C1 recipes, results and history cannot be imported as drafts")
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith("c1."):
            raise ValueError("C1 models are owned bindings; intermediate steps are audit-only")
        return super()._disclose(cid, actor, source, selectors, subject)

    def _start(self, cid, request):
        if type(request) is not MovementRequest:
            return super()._start(cid, request)
        r, recipe = request, RECIPES[request.recipe]
        if (r.actor not in self._profiles or r.actor not in self._wallets
                or (r.actor, r.key) in self._jobs or r.actor in self._locks):
            raise ValueError("funded typed actor, unused key and free processing required")
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if (r.cue not in self._references or r.context not in known or r.cue not in known
                or Role.CONTEXT not in self.world.resolve(r.context).roles):
            raise ValueError("processed context and source cue required")
        prepared = content.prepare(view, r)
        binding = prepared["binding"]
        if binding.target not in known:
            raise ValueError("target must be accessible")
        if recipe.name != "Theorize" and r.input not in self._movement_models:
            raise ValueError("model must be a completed native C1 output")
        if recipe.name == "Embody":
            event = prepared["observed"]["event"]
            if event not in self._movement_trials:
                raise ValueError("observed event must be an actual C1 trial")
            source = view.detail(r.evidence[0]).source
            observation = self.world.resolve(source)
            if (source.identity.namespace != "u4.observation"
                    or observation.facet(Account).sources != (event,)):
                raise ValueError("native event observation provenance required")
        tim = attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows = route(tim, self._cursors[r.actor], r.elements or recipe.elements,
                     recipe.origin, recipe.destination, recipe.polarity)
        addresses = tuple(dict.fromkeys((*r.evidence, *binding.particulars,
            *(p.address for p in view.resolve(r.rule) if r.rule is not None))))
        sources = tuple(dict.fromkeys(view.detail(a).source for a in addresses))
        recall = 1 + len(addresses) + len(binding.content)
        semantic = sum(sum(row["charges"]) + row["content_units"] for row in rows)
        base = OperationRequest(r.key, r.actor, "inspect" if recipe.material_units else "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base)
             if f.name not in ("participants", "evidence")}
        deps = tuple(dict.fromkeys((recipe.ref, self.law, r.cue, r.context,
            self._profiles[r.actor], r.input, *((r.rule,) if r.rule is not None else ()))))
        d.update(record_type="operation", primitive=base.kind, c1=True, recipe=recipe.ref,
            recipe_key=recipe.key, movement=recipe.name, cue=r.cue, source_input=r.input,
            rule=r.rule, request_evidence_count=len(r.evidence),
            required=recall + semantic + recipe.material_units, completed=0, spent=0,
            recall_units=recall, route_prepare=recall, route_execute=semantic,
            material_units=recipe.material_units, steps_completed=0, last_step=None,
            origin=recipe.origin, destination=recipe.destination, polarity=recipe.polarity,
            active_start=self._cursors[r.actor], tim=tim, target=binding.target,
            status="pending", failure=None, result=None, started_tick=self._now().tick,
            **flatten_route(rows))
        for prefix, values in (("input.", (r.input, r.context, r.cue, *sources)),
                ("dependency.", deps), ("participant.", (r.actor,)), ("lock.", (r.actor,))):
            d.update({prefix + str(i): value for i, value in enumerate(values)})
        for i, a in enumerate(addresses):
            d[f"evidence.delivery.{i}"], d[f"evidence.key.{i}"] = a.delivery, a.key
        ref = job_address(r.actor, r.key)
        added = () if recipe.ref.identity in self.world._heads else (definition(recipe),)
        if not added and self.world.resolve(recipe.ref) != definition(recipe):
            raise ValueError("recipe differs from its immutable contract")
        self._batch(cid, r.actor, (*added, record(ref, "Paid Crux " + recipe.name, d)),
                    evidence=(r.input, *sources))
        self._jobs[r.actor, r.key] = ref
        self._reserve(d, ref)
        self._movement_inputs[ref.identity] = r, prepared, addresses, sources
        return ref

    def _semantic_step(self, name, prepared, previous):
        return content.transform(name, prepared, previous)

    def _recipe_for(self, request):
        return RECIPES[request.recipe]

    def _step_namespace(self, request):
        return "c1.step"

    def _semantic_command(self, data, kind, target, values):
        """Extension hook: install a command only after its paid semantic step."""
        return None

    @staticmethod
    def _step_content(value):
        d, account = attrs(value), value.facet(Account)
        return d["content_kind"], account.referent, {p.relation: p.object for p in account.content}

    def _advance(self, cid, actor, key, work_limit):
        old, d = self._active(actor, key)
        if not (d.get("c1") or d.get("c2") or d.get("c3") or d.get("c4")):
            return super()._advance(cid, actor, key, work_limit)
        if type(work_limit) is not int or work_limit < 1 or d["status"] == "ready":
            raise ValueError("positive work bound and unfinished movement required")
        r, prepared, addresses, sources = self._movement_inputs[old.ref.identity]
        recipe = self._recipe_for(r)
        wallet_before = self.world.resolve(self._wallets[actor])
        wallet = attrs(wallet_before)
        reserve = self._can_reserve(d, old.ref)
        paid = min(work_limit, d["required"] - d["completed"], wallet["energy"], wallet["time"]) if reserve else 0
        d["completed"] += paid
        d["spent"] += paid
        d["status"] = "waiting" if not reserve else ("ready" if d["completed"] == d["required"] else "partial")
        steps = []
        threshold = d["recall_units"]
        previous_ref = d["last_step"]
        previous = None if previous_ref is None else self._step_content(self.world.resolve(previous_ref))
        for i, name in enumerate(recipe.steps):
            prefix = f"route.{i}."
            threshold += sum(indexed(d, prefix + "charges.")) + d[prefix + "content_units"]
            if i < d["steps_completed"] or threshold > d["completed"]:
                continue
            result = self._semantic_step(name, prepared, previous)
            kind, target, values = result
            ref = address(self._step_namespace(r), actor, key, i)
            predecessor = r.input if previous_ref is None else previous_ref
            props = tuple(Proposition(target, k, v, r.context, TimeScope(Moment(target.revision, 0), None))
                          for k, v in sorted(values.items()))
            step = ObjectVersion(ref, WRITER, self._step_namespace(r).split(".")[0].upper() + " semantic " + name, (Role.INTERPRETATION,),
                (Account(target, props, self._now(), actor, (predecessor, *sources)),),
                occurrence=Occurrence.INTERPRETATION,
                attributes=attributes({"content_kind": kind, "step": name, "index": i,
                    "operation": old.ref, "predecessor": predecessor, "recipe": recipe.ref,
                    "paid_threshold": threshold, "origin": d[prefix + "origin"],
                    "destination": d[prefix + "destination"], "polarity": recipe.polarity}))
            steps.append(step)
            d["steps_completed"], d["last_step"] = i + 1, ref
            previous_ref, previous = ref, result
            self._semantic_command(d, kind, target, values)
            if kind == "trial":
                # The material command consumes the generated trial content.
                d["target"], d["primitive"], d["model"] = target, values["primitive"], values["model"]
        current = next_version(old, attributes=attributes(d))
        versions = [current, *steps]
        if paid:
            wallet["energy"] -= paid
            wallet["time"] -= paid
            after_wallet = next_version(wallet_before, attributes=attributes(wallet))
            versions.append(after_wallet)
        self._batch(cid, actor, versions, evidence=(old.ref,))
        self._jobs[actor, key] = current.ref
        if paid:
            self._wallets[actor] = after_wallet.ref
        if reserve:
            self._reserve(d, current.ref)
        self._cursors[actor] = progress(d)[0]
        return current.ref

    def _event(self, cid, job, outcome, changed=()):
        event = super()._event(cid, job, outcome, changed)
        d = attrs(job)
        if d.get("c1") and d["movement"] == "Apply":
            values = attrs(event)
            values.update(model=d["source_input"], trial=d["last_step"], movement="Apply", recipe=d["recipe"])
            event = replace(event, attributes=attributes(values))
        return event

    def _commit(self, cid, actor, key):
        old, d = self._active(actor, key)
        if not d.get("c1"):
            return super()._commit(cid, actor, key)
        if d["status"] != "ready":
            raise ValueError("full paid movement required")
        r, prepared, addresses, sources = self._movement_inputs[old.ref.identity]
        recipe = RECIPES[r.recipe]
        if d["steps_completed"] != len(recipe.steps):
            raise ValueError("movement is missing a semantic handoff")
        last = self.world.resolve(d["last_step"])
        kind, target, values = self._step_content(last)
        if recipe.name == "Apply":
            if (kind != "trial" or d["target"] != target or d["primitive"] != values["primitive"]
                    or d.get("model") != values["model"] or values["primitive"] != "inspect"):
                raise ValueError("actual material command must consume its trial")
            event = OperationEngine._commit(self, cid, actor, key)
            if self.job_status(actor, key)["status"] == "succeeded":
                self._movement_trials.add(event)
            return event
        failure = "stale_dependency" if any(self.world.head(ref.identity).ref != ref
                  for ref in indexed(d, "dependency.")) else None
        live = self.participant_view(actor)
        if live._heads.get(r.input.identity) != prepared["binding"]:
            failure = "changed_owned_input"
        changed, access_command = [], None
        if failure is None:
            if recipe.name == "Theorize":
                if kind != "model":
                    raise ValueError("hypothesis needs its actual model output")
                ref = address("c1.model", actor, key)
                propositions = tuple(replace(p, relation="c1." + p.relation) for p in last.facet(Account).content)
                meaning, endorsement = "C1 scoped hypothesis; test pending", ClaimStatus.TENTATIVE
            else:
                if kind != "personal":
                    raise ValueError("Embody needs its actual retained interpretation")
                identity = address("u5.account", actor, r.cue, r.context, target.identity, "condition").identity
                prior = live._heads.get(identity)
                ref = ObjectRef(identity, 1 if prior is None else prior.ref.revision + 1)
                propositions = () if values["condition"] is None else (Proposition(target, "condition",
                    values["condition"], r.context, TimeScope(Moment(target.revision, 0), None)),)
                meaning = "integrate: condition; " + values["status"] + "; " + values["tension"]
                endorsement = ClaimStatus.ENDORSED if propositions else ClaimStatus.TENTATIVE
            binding = ObjectVersion(ref, WRITER, "Retained C1 " + recipe.name, (Role.INTERPRETATION,),
                (Account(target, propositions, self._now(), actor, sources),),
                previous=None if ref.revision == 1 else ObjectRef(ref.identity, ref.revision - 1),
                occurrence=Occurrence.INTERPRETATION,
                attributes=attributes({"cue": r.cue, "context": r.context, "meaning": meaning,
                    "endorsement": endorsement.value, "confidence": None, "link.0": r.input}))
            receipt = record(address("u4.receipt", cid), "Paid C1 content receipt", {
                "actor": actor, "operation": "bind", "work_key": ref.identity.key,
                **{k: d[k] for k in ("required", "completed", "spent")},
                **{"input." + str(i): x for i, x in enumerate((ref, *sources))}})
            access_command = ("bind", actor, ref, addresses, receipt.ref)
            self.access.preview(access_command, {ref: binding, receipt.ref: receipt})
            changed = [binding, receipt]
            d["binding"] = ref
        outcome = "succeeded" if failure is None else "failed"
        event = self._event(cid, old, outcome)
        d.update(status=outcome, failure=failure, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(d))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref, last.ref))
        if access_command:
            self.access._execute(access_command)
            if recipe.name == "Theorize":
                self._movement_models.add(d["binding"])
        self._jobs[actor, key] = current.ref
        self._release(d, old.ref)
        return event.ref

    @classmethod
    def from_u14(cls, text):
        """Import an exact U14 checkpoint by replay, changing only its schema tag."""
        data = unseal(text, InstitutionEngine.SCHEMA)
        return cls.restore(seal(cls.SCHEMA, data))
