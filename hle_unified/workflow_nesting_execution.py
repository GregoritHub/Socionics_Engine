"""Paid bounded workflow-parent review without cross-owner aggregation."""
from dataclasses import fields
from .workflow_execution import WorkflowEngine
from .workflow_nesting_records import WorkflowParentRequest, PARENT_RECIPE, definition, registry
from . import workflow_content as sem
from .records import ObjectVersion, Role, Account, Occurrence, Proposition, TimeScope, Moment, ClaimStatus
from .operations import OperationEngine, address, job_address, record, indexed
from .operation_records import OperationRequest, WRITER
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route, progress


class WorkflowNestingEngine(WorkflowEngine):
    SCHEMA = "hle-full-crux-c7-workflow-nesting-v1"

    @staticmethod
    def _registry(): return registry()

    def _recipe_for(self, r):
        return PARENT_RECIPE if type(r) is WorkflowParentRequest else super()._recipe_for(r)

    def _step_namespace(self, r):
        return "c7n.step" if type(r) is WorkflowParentRequest else super()._step_namespace(r)

    def _semantic_step(self, name, p, previous):
        if not p.get("c7n"):
            return super()._semantic_step(name, p, previous)
        if name == "review:children":
            value = dict(kind="reviewed_children", content=sem.encode(p["result"]))
        else:
            value = sem.decode(previous[2]["payload"])
            if value.get("kind") != "reviewed_children":
                raise ValueError("exact reviewed child predecessor required")
            value = sem.decode(value["content"])
        return "c7n", p["request"].target, {"payload": sem.encode(value)}

    def _read_child(self, view, ref, r):
        if ref.identity.namespace == "u4.observation":
            items = view.resolve(ref)
            value = {p.address.key: p.value for p in items}
            if not {"event", "outcome", "context", "primitive", "actor"} <= set(value) or value["context"] != r.context:
                raise ValueError("paid exact child event observation required")
            return dict(value, kind="child_event"), tuple(p.address for p in items)
        binding = view._bindings.get(ref)
        if binding is None or (binding.actor, binding.context, binding.cue, binding.target.identity) != (r.actor, r.context, r.cue, r.target.identity):
            raise ValueError("owned exact child output required")
        if len(binding.content) != 1 or binding.content[0].relation not in ("c7w.data", "c7n.data"):
            raise ValueError("workflow child output schema required")
        return sem.decode(binding.content[0].object), binding.particulars

    def _prepare_parent(self, r):
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if r.cue not in self._references or any(x not in known for x in (r.context, r.cue, r.target)) or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("processed context, target and cue required")
        if any(view.detail(x) is None for x in r.evidence):
            raise ValueError("unread or foreign parent evidence")
        addresses = list(r.evidence); rows = []; operations = {}; depth = 1; values = []; inherited = []
        for child in r.children:
            job = self.world.resolve(child.operation); d = attrs(job)
            receipt = {p.address.key: p.value for p in view.resolve(child.operation)}
            if any(k not in receipt or receipt[k] != d.get(k) for k in ("actor", "context", "status", "spent", "result")):
                raise ValueError("paid exact child operation receipt required")
            addresses.extend(p.address for p in view.resolve(child.operation))
            value, paid = self._read_child(view, child.output, r); values.append(value); addresses.extend(paid)
            if (child.operation.identity.namespace != "u4.operation" or self.world.head(child.operation.identity).ref != child.operation
                    or d.get("actor") != r.actor or d.get("context") != r.context or not (d.get("c7w") or d.get("c7n"))
                    or d.get("status") not in ("succeeded", "failed", "cancelled")):
                raise ValueError("current terminal owned workflow movement required")
            if d.get("content_target", d.get("target")).identity != r.target.identity:
                raise ValueError("child target differs")
            if child.output.identity.namespace == "u4.observation":
                if value["event"] != d["result"]:
                    raise ValueError("child event differs")
            elif child.output not in (d.get("binding"), *indexed(d, "public.")):
                raise ValueError("output does not belong to declared child")
            fulfilled = d["status"] == "succeeded" and value.get("complete", True) and value.get("status") not in ("declined", "blocked")
            rows.append((child.operation, child.output, d["status"], d["origin"], d["destination"],
                         d["actor"], d["polarity"], fulfilled, d["movement"]))
            operations[child.operation] = d["spent"]
            if d["status"] == "succeeded" and child.output.identity.namespace != "u4.observation":
                inherited.extend(indexed(d, "dependency."))
            if value.get("kind") == "workflow_parent":
                depth = max(depth, value["depth"] + 1)
                for ref, spent in value["operations"]:
                    if ref in operations and operations[ref] != spent:
                        raise ValueError("inconsistent descendant charge")
                    operations[ref] = spent
        if depth > 4 or len(operations) > 64:
            raise ValueError("declared workflow nesting budget exceeded")
        for left, right in r.links:
            ca, cb = r.children[left], r.children[right]
            da, db = attrs(self.world.resolve(ca.operation)), attrs(self.world.resolve(cb.operation))
            if da["destination"] != db["origin"] or ca.output not in indexed(db, "source."):
                raise ValueError("formal endpoint equality is not an actual child handoff")
        group = None
        if r.group:
            fields_ = [p for p in view.resolve(r.group) if p.address.key == "payload"]
            if len(fields_) != 1:
                raise ValueError("paid current parent membership required")
            group = sem.decode(fields_[0].value)
            if group["context"] != r.context or len(group["members"]) != 2 or r.actor not in group["members"]:
                raise ValueError("bounded current parent membership required")
            addresses.extend(p.address for p in view.resolve(r.group))
        addresses = tuple(dict.fromkeys(addresses))
        sources = tuple(dict.fromkeys(view.detail(x).source for x in addresses))
        operations = tuple(sorted(operations.items(), key=lambda x: (x[0].identity.namespace, x[0].identity.key, x[0].revision)))
        complete = all(row[7] for row in rows)
        result = dict(kind="workflow_parent", target=r.target, context=r.context,
            children=tuple((c.operation, c.output) for c in r.children), links=r.links, outcomes=tuple(rows),
            complete=complete, status="complete" if complete else "blocked", depth=depth,
            operations=operations, cited_spending=sum(n for _, n in operations),
            polarities=tuple(row[6] for row in rows), competence=False, executable=False,
            authority=None, group=r.group)
        return dict(c7n=True, request=r, recipe=PARENT_RECIPE, addresses=addresses, sources=sources,
            rows=tuple(rows), operations=operations, depth=depth, result=result, inherited=tuple(dict.fromkeys(inherited)),
            units=1 + len(addresses) + sum(1 + len(sem.encode(v)) // 64 for v in values) + len(operations))

    def _start(self, cid, r):
        if type(r) is not WorkflowParentRequest:
            return super()._start(cid, r)
        if r.actor not in self._profiles or (r.actor, r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("available funded typed actor required")
        p = self._prepare_parent(r); recipe = PARENT_RECIPE
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        tim = attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        route_rows = route(tim, self._cursors[r.actor], r.elements or recipe.elements, recipe.origin, recipe.destination, recipe.polarity)
        execution = sum(sum(row["charges"]) + row["content_units"] for row in route_rows)
        d.update(record_type="operation", primitive="bind", c7n=True, recipe=recipe.ref, recipe_key=recipe.key,
            movement=recipe.name, cue=r.cue, content_target=r.target, source_input=r.input, group=r.group,
            required=p["units"] + execution, completed=0, spent=0, recall_units=p["units"], route_prepare=p["units"],
            route_execute=execution, material_units=0, steps_completed=0, last_step=None,
            origin=recipe.origin, destination=recipe.destination, polarity=recipe.polarity,
            active_start=self._cursors[r.actor], tim=tim, status="pending", failure=None, result=None,
            children_payload=sem.encode(dict(children=tuple((c.operation, c.output) for c in r.children), links=r.links)),
            started_tick=self._now().tick, **flatten_route(route_rows))
        deps = tuple(dict.fromkeys((recipe.ref, self.law, r.context, r.cue, self._profiles[r.actor],
            *r.inputs, *(c.operation for c in r.children), *p["inherited"], *((r.group,) if r.group else ()))))
        for prefix, values in (("input.", (r.context, r.cue, *r.inputs, *p["sources"])),
                               ("source.", r.inputs), ("dependency.", deps),
                               ("participant.", (r.actor,)), ("lock.", (r.actor,))):
            d.update({prefix + str(i): value for i, value in enumerate(values)})
        for i, value in enumerate(p["addresses"]):
            d[f"evidence.delivery.{i}"], d[f"evidence.key.{i}"] = value.delivery, value.key
        ref = job_address(r.actor, r.key)
        added = () if recipe.ref.identity in self.world._heads else (definition(),)
        if not added and self.world.resolve(recipe.ref) != definition():
            raise ValueError("immutable workflow parent recipe differs")
        self._batch(cid, r.actor, (*added, record(ref, "Paid workflow parent review", d)), evidence=r.inputs)
        self._jobs[r.actor, r.key] = ref
        self._movement_inputs[ref.identity] = r, p, p["addresses"], p["sources"]
        self._reserve(d, ref)
        return ref

    def _advance(self, cid, actor, key, work_limit):
        old, d = self._active(actor, key)
        if not d.get("c7n"):
            return super()._advance(cid, actor, key, work_limit)
        if type(work_limit) is not int or work_limit < 1 or d["status"] == "ready":
            raise ValueError("positive work bound and unfinished parent review required")
        r, prepared, addresses, sources = self._movement_inputs[old.ref.identity]
        wallet_before = self.world.resolve(self._wallets[actor]); wallet = attrs(wallet_before)
        reserve = self._can_reserve(d, old.ref)
        paid = min(work_limit, d["required"] - d["completed"], wallet["energy"], wallet["time"]) if reserve else 0
        d["completed"] += paid; d["spent"] += paid
        d["status"] = "waiting" if not reserve else ("ready" if d["completed"] == d["required"] else "partial")
        steps = []; threshold = d["recall_units"]; previous_ref = d["last_step"]
        previous = None if previous_ref is None else self._step_content(self.world.resolve(previous_ref))
        for i, name in enumerate(PARENT_RECIPE.steps):
            prefix = f"route.{i}."
            threshold += sum(indexed(d, prefix + "charges.")) + d[prefix + "content_units"]
            if i < d["steps_completed"] or threshold > d["completed"]:
                continue
            kind, target, values = self._semantic_step(name, prepared, previous)
            ref = address(self._step_namespace(r), actor, key, i)
            predecessor = r.input if previous_ref is None else previous_ref
            propositions = tuple(Proposition(target, k, v, r.context, TimeScope(Moment(target.revision, 0), None))
                for k, v in sorted(values.items()))
            step = ObjectVersion(ref, WRITER, "C7N semantic " + name, (Role.INTERPRETATION,),
                (Account(target, propositions, self._now(), actor, (predecessor, *sources)),),
                occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(dict(content_kind=kind, step=name, index=i, operation=old.ref,
                    predecessor=predecessor, recipe=PARENT_RECIPE.ref, paid_threshold=threshold,
                    origin=d[prefix + "origin"], destination=d[prefix + "destination"], polarity=PARENT_RECIPE.polarity)))
            steps.append(step); d["steps_completed"], d["last_step"] = i + 1, ref
            previous_ref, previous = ref, (kind, target, values)
        current = next_version(old, attributes=attributes(d)); versions = [current, *steps]
        if paid:
            wallet["energy"] -= paid; wallet["time"] -= paid
            after_wallet = next_version(wallet_before, attributes=attributes(wallet)); versions.append(after_wallet)
        self._batch(cid, actor, versions, evidence=(old.ref,)); self._jobs[actor, key] = current.ref
        if paid: self._wallets[actor] = after_wallet.ref
        if reserve: self._reserve(d, current.ref)
        self._cursors[actor] = progress(d)[0]
        return current.ref

    def _commit(self, cid, actor, key):
        old, d = self._active(actor, key)
        if not d.get("c7n"):
            return super()._commit(cid, actor, key)
        r, p, addresses, sources = self._movement_inputs[old.ref.identity]
        if d["status"] != "ready" or d["steps_completed"] != 2:
            raise ValueError("fully paid parent review required")
        last = self.world.resolve(d["last_step"]); result = sem.decode(self._step_content(last)[2]["payload"])
        failure = "stale_dependency" if any(self.world.head(x.identity).ref != x for x in indexed(d, "dependency.")) else None
        changed = []; command = None
        if failure is None:
            ref = address("c7n.output", actor, key)
            binding = ObjectVersion(ref, old.writer, "Retained bounded workflow parent", (Role.INTERPRETATION,),
                (Account(r.target, (Proposition(r.target, "c7n.data", sem.encode(result), r.context,
                    TimeScope(self._now(), None)),), self._now(), actor, sources),),
                occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(dict(cue=r.cue, context=r.context, meaning="Bounded workflow parent",
                    endorsement=ClaimStatus.TENTATIVE.value, confidence=None)))
            receipt = record(address("u4.receipt", cid), "Paid workflow parent retention", dict(actor=actor,
                operation="bind", work_key=ref.identity.key, **{k: d[k] for k in ("required", "completed", "spent")},
                **{"input." + str(i): value for i, value in enumerate((ref, *sources))}))
            command = ("bind", actor, ref, addresses, receipt.ref)
            self.access.preview(command, {ref: binding, receipt.ref: receipt})
            changed = [binding, receipt]; d["binding"] = ref
        outcome = "succeeded" if failure is None else "failed"
        event = self._event(cid, old, outcome)
        d.update(status=outcome, failure=failure, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(d))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref, last.ref))
        if command:
            self.access._execute(command)
        self._jobs[actor, key] = current.ref; self._release(d, old.ref)
        return event.ref
