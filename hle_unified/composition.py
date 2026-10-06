"""U9 paid composition, execution and counterexample revision on the U8 engine.

This trusted service retains simulator records. Participant decisions use only
detached views and actor-owned generated outputs. Search does not read world
material heads, evaluation labels or another actor's repertoire.
"""
from copy import deepcopy
from dataclasses import fields, replace
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence,
                      ClaimStatus, Proposition, TimeScope, Material, Procedure, Concept)
from .store import next_version
from .material import attrs as raw_attrs, attributes
from .operations import address, job_address, indexed
from .operation_records import OperationRequest, WRITER
from .cognitive_routes import route, flatten_route, progress
from .development import DevelopmentEngine, record
from .development_values import attrs, pack
from .composition_records import CompositionRequest, LAW9, world_contract, registry
from . import composition_language as lang
from . import codec


class CompositionEngine(DevelopmentEngine):
    SCHEMA = "hle-unified-u9-engine-v1"

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._construct_inputs, self._construct, self._construct_heads = {}, {}, {}
        self._construct_enacted, self._construct_observed = {}, set()

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u9.") for v in versions):
            raise ValueError("generated procedures, demands and practice cannot be imported")
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith("u9.") and source != LAW9:
            if attrs(self.world.resolve(source)).get("actor") != actor:
                raise ValueError("another actor's composition needs a separate learning path")
        return super()._disclose(cid, actor, source, selectors, subject)

    def composition_view(self, actor):
        """Detached owned current records, with unfinished work and no assessor."""
        return tuple(deepcopy(self._construct[r]) for r in self._construct_heads.values()
                     if self._construct[r]["actor"] == actor)

    def _owned(self, actor, ref, kind=None, *, current=True):
        d = self._construct.get(ref)
        if (d is None or d["actor"] != actor or kind and d["kind"] not in kind
                or current and self._construct_heads.get(ref.identity) != ref):
            raise ValueError("current actor-owned generated output required")
        return d

    def _capacities9(self, actor, context):
        return {r: d for r, d in self._construct.items()
                if d["kind"] == "capacity" and d["actor"] == actor and d["context"] == context}

    def _prepare9(self, r):
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if r.actor not in self._profiles or r.cue not in self._references or any(x not in known for x in (r.context, r.cue)):
            raise ValueError("processed source cue and context for a typed actor required")
        if Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("context role required")
        focus = None if r.focus is None else self._owned(r.actor, r.focus)
        if focus and (focus["context"], focus["cue"]) != (r.context, r.cue):
            raise ValueError("owned work must stay within its learned contextual scope")
        slots = r.slots if focus is None else focus["slots"]
        state, sources, evidence = lang.snapshot(view, slots)
        if any(x not in known for _, x in slots):
            raise ValueError("all role references must be accessible")
        primitives = lang.acquired(view, r.context)
        caps = self._capacities9(r.actor, r.context)
        item = None
        if r.item:
            item = self._owned(r.actor, r.item, ("candidate", "capacity"))
            if item["context"] != r.context or item["cue"] != r.cue:
                raise ValueError("program is outside retained contextual scope")
        observation = None
        if r.observation:
            details = view.resolve(r.observation)
            observation = {p.address.key: p.value for p in details}
            if not details or r.observation.identity.namespace != "u4.observation":
                raise ValueError("a processed native execution observation is required")
            sources = tuple(dict.fromkeys((*sources, r.observation)))
            evidence = tuple(dict.fromkeys((*evidence, *(p.address for p in details))))
        # Every source used by this operation is actor processed. Version changes
        # received during payment invalidate pending work without erasing costs.
        return dict(state=state, sources=sources, evidence=evidence, primitives=primitives,
                    capacities=caps, focus=focus, item=item, observation=observation, slots=slots)

    def _start(self, cid, request):
        if type(request) is not CompositionRequest: return super()._start(cid, request)
        r = request
        if (r.actor, r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("unused operation key and no competing cognitive work required")
        prepared = self._prepare9(r)
        field_count = sum(len(fs) for _, fs in prepared["state"])
        # Explicit conservative finite work tickets. All search/interpreter work
        # is done after payment, and incomplete tickets expose no candidate.
        fuel = r.limit * r.depth * 4
        repertoire_units = sum(lang.size(d["program"]) for d in prepared["capacities"].values())
        units = max(1, len(prepared["evidence"]) + field_count + repertoire_units +
                    (r.limit * (field_count + fuel + len(prepared["primitives"])) if r.purpose == "search" else fuel))
        tim = raw_attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        outward = r.purpose in ("instantiate", "select")
        origin, destination, polarity = ("I", "IT", "expenditure") if outward else ("IT", "I", "accumulation")
        rows = route(tim, self._cursors[r.actor], ("fi", "si") if outward else ("si", "fi"), origin, destination, polarity)
        route_units = sum(sum(row["charges"]) + row["content_units"] for row in rows)
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        d.update(record_type="operation", primitive="bind", u9=True, purpose=r.purpose,
            target=dict(prepared["slots"])["target"], cue=r.cue, focus=r.focus, item=r.item,
            required=units+route_units, completed=0, spent=0, recall_units=units,
            route_prepare=units, route_execute=route_units, status="pending", failure=None,
            result=None, active_start=self._cursors[r.actor], tim=tim, origin=origin,
            destination=destination, polarity=polarity, started_tick=self._now().tick,
            contract=LAW9, limit=r.limit, depth=r.depth, fuel=fuel,
            field_count=field_count, repertoire_units=repertoire_units,
            evidence_count=len(prepared["evidence"]), primitive_count=len(prepared["primitives"]), **flatten_route(rows))
        sources = prepared["sources"]
        refs = tuple(dict.fromkeys((r.context, r.cue, *(x for _, x in prepared["slots"]), *sources,
                                  *((r.focus,) if r.focus else ()), *((r.item,) if r.item else ()),
                                  *(p for _, p in prepared["primitives"]))))
        for prefix, values in (("input.", refs), ("source.", sources), ("participant.", (r.actor,)),
                               ("lock.", (r.actor,)), ("dependency.", (LAW9, self.law, r.cue, self._profiles[r.actor]))):
            d.update({prefix+str(i): x for i, x in enumerate(values)})
        ref = job_address(r.actor, r.key)
        added = () if LAW9.identity in self.world._heads else (world_contract(),)
        if not added and self.world.resolve(LAW9) != world_contract(): raise ValueError("constructive contract mismatch")
        self._batch(cid, r.actor, (*added, record(ref, "Paid constructive "+r.purpose, d)), evidence=refs)
        self._jobs[r.actor, r.key] = ref
        self._reserve(d, ref)
        self._construct_inputs[ref.identity] = r, prepared
        return ref

    def _advance(self, cid, actor, key, work_limit):
        ref = super()._advance(cid, actor, key, work_limit)
        d = raw_attrs(self.world.resolve(ref))
        if d.get("u9"): self._cursors[actor] = progress(d)[0]
        return ref

    def _new9(self, kind, r, operation, p, *, prior=None, suffix="", **values):
        ref = address("u9."+kind, r.actor, r.key, suffix) if prior is None else ObjectRef(prior.identity, prior.revision+1)
        return dict(ref=ref, kind=kind, actor=r.actor, context=r.context, cue=r.cue,
                    slots=p["slots"], sources=p["sources"], operation=operation, **values)

    def _derive9(self, r, p, operation, fuel):
        f, state, caps = p["focus"], p["state"], p["capacities"]
        out = []
        if r.purpose == "notice":
            # Validate the goal grammar even if an early conjunct is false.
            for test in r.goal: lang.predicate(test, lang.thaw(state))
            out.append(self._new9("demand", r, operation, p, state=state, goal=r.goal,
                status="satisfied" if lang.meets(state, r.goal) else "open", reason="observed_goal_discrepancy", origin=None))
        elif r.purpose == "search":
            if f["kind"] not in ("demand", "search") or f["status"] in ("satisfied", "candidate"):
                raise ValueError("an open demand or unfinished search is required")
            if not p["primitives"]: raise ValueError("no actor-owned acquired operations")
            if f["kind"] == "demand":
                repertoire = tuple(ref for ref, d in caps.items() if self._construct_heads[ref.identity] == ref and ref != f.get("failed_capacity"))
                s = dict(goal=f["goal"], initial=f["state"], queue=((f["state"], (), 0),), deferred=(),
                    visited=(lang.signature(f["state"]),), depth=r.depth, considered=0, repertoire=repertoire,
                    demand=f["ref"], primitive_dependencies=p["primitives"])
                prior = None
            else:
                s, prior = f, f["ref"]
                if s["primitive_dependencies"] != p["primitives"]:
                    raise ValueError("acquired repertoire changed; start a newly scoped search")
            s, program, attempts = lang.search_ticket(s, p["primitives"], caps, r.actor, r.limit, r.depth, fuel)
            values = {k: s[k] for k in ("goal", "initial", "queue", "deferred", "visited", "depth", "considered", "repertoire", "demand", "primitive_dependencies", "status")}
            search = self._new9("search", r, operation, p, prior=prior, **values, attempts=attempts)
            out.append(search)
            if program:
                lang.validate(program, caps)
                d = self._construct[s["demand"]]
                candidate = self._new9("candidate", r, operation, p, program=program,
                    initial=s["initial"], goal=s["goal"], search=search["ref"], demand=s["demand"],
                    dependencies=tuple(dict.fromkeys((*lang.dependencies(program), *(ref for _, ref in p["primitives"])))),
                    revises=d.get("failed_capacity"), status="hypothesis")
                out.append(candidate)
        elif r.purpose == "instantiate":
            if f["kind"] != "demand" or f["status"] == "satisfied": raise ValueError("an open physical demand required")
            current = lang.thaw(state)
            current["progress"] = dict(lang.thaw(f["state"])["progress"])
            state = lang.freeze(current)
            item = p["item"]
            if item["goal"] != f["goal"]: raise ValueError("program was not retained for this declared goal")
            if item["kind"] == "capacity" and not lang.meets(state, item["guard"]): raise ValueError("outside learned concept guard")
            lang.validate(item["program"], caps)
            if not lang.primitive_names(item["program"], caps) <= dict(p["primitives"]).keys(): raise ValueError("procedure contains an unacquired primitive")
            out.append(self._new9("run", r, operation, p, program=item["ref"], trace=(), remaining=(item["program"],),
                initial=state, state=state, goal=f["goal"], demand=f["ref"], index=0, events=(),
                observations=(), selected=None, status="active", failure_kind=None, primitive_dependencies=p["primitives"]))
        elif r.purpose == "select":
            if f["kind"] != "run" or f["status"] != "active" or f["selected"] is not None:
                raise ValueError("active run without an outstanding selected action required")
            if p["primitives"] != f["primitive_dependencies"]:
                raise ValueError("primitive repertoire changed during run")
            # Fresh processed slot state supplies exact revisions; progress comes
            # only from this run's distinct observed successful uses.
            current = lang.thaw(state); current["progress"] = lang.thaw(f["state"])["progress"]
            state = lang.freeze(current)
            name, remaining, _ = lang.take_step(f["remaining"], state, caps, fuel)
            plan = self._new9("plan", r, operation, p, run=f["ref"], index=f["index"],
                primitive=name, procedure=dict(p["primitives"])[name], state=state, status="selected")
            out.append(plan)
            values = self._run_values(f)
            values.update(trace=(*f["trace"], name), remaining=remaining)
            out.append(self._new9("run", r, operation, p, prior=f["ref"], **values, selected=plan["ref"], state=state))
        elif r.purpose == "observe":
            if f["kind"] != "run" or f["status"] != "active" or f["selected"] is None:
                raise ValueError("selected run action required")
            obs = p["observation"]
            event = obs.get("event")
            if (event in self._construct_observed or obs.get("actor") != r.actor
                    or obs.get("u9_plan") != f["selected"] or type(obs.get("operation")) is not ObjectRef
                    or self._construct_enacted.get(f["selected"]) != obs["operation"].identity
                    or obs.get("primitive") != f["trace"][f["index"]]):
                raise ValueError("fresh observed actual execution of this exact selected step required")
            actual = raw_attrs(self.world.resolve(event))
            if any(actual.get(k) != v for k, v in obs.items()): raise ValueError("observation differs from its actual execution")
            current = lang.thaw(state)
            current["progress"] = dict(lang.thaw(f["state"])["progress"])
            if obs["outcome"] == "succeeded" and obs["primitive"] == "use": current["progress"]["uses"] += 1
            state = lang.freeze(current)
            index = f["index"]+1
            status = "failed" if obs["outcome"] != "succeeded" else ("succeeded" if not f["remaining"] and lang.meets(state, f["goal"]) else "active")
            if not f["remaining"] and status == "active": status = "failed"
            failure_kind = None
            if status == "failed":
                name = obs["primitive"]
                limited = any(current[slot].get("custodian") != r.actor for _,slot in lang.SCHEMAS[name]["inputs"] if slot != "relation")
                if name in ("care", "repair"):
                    stock = current[name+"_stock"]
                    limited = limited or stock["available"] < 1 or stock["owner"] != r.actor
                if obs["outcome"] == "cancelled":
                    status, failure_kind = "interrupted", "interrupted_work"
                elif limited: failure_kind = "resource_or_permission_limit"
                elif obs["outcome"] == "failed" and lang.action(f["state"], name, r.actor) is not None:
                    failure_kind = "unresolved_execution_failure"
                else: failure_kind = "observed_counterexample"
            values = self._run_values(f)
            values.update(index=index, events=(*f["events"], event), observations=(*f["observations"], r.observation), status=status, failure_kind=failure_kind)
            run = self._new9("run", r, operation, p, prior=f["ref"], **values, selected=None, state=state)
            out.append(run)
            if status in ("failed", "interrupted"):
                program = self._construct[f["program"]]
                out.append(self._new9("demand", r, operation, p, suffix="consequence", state=state, goal=f["goal"],
                    status="open", origin=run["ref"], reason="persistent_consequence" if failure_kind == "observed_counterexample" else failure_kind))
                if program["kind"] == "capacity" and failure_kind == "observed_counterexample":
                    out.append(self._new9("demand", r, operation, p, suffix="generalization", state=f["initial"], goal=f["goal"],
                        status="open", origin=run["ref"], reason="failed_generalization", failed_capacity=program["ref"]))
        else:
            if f["kind"] != "run" or f["status"] != "succeeded" or not f["events"]:
                raise ValueError("successful independently observed full execution required")
            item = self._construct[f["program"]]
            if item["kind"] != "candidate": raise ValueError("retention takes a tested novel candidate")
            if any(d["kind"] == "capacity" and d.get("practice") == f["ref"] for d in self._construct.values()):
                raise ValueError("the same practice cannot grant capacity twice")
            program, prior, split = item["program"], item.get("revises"), None
            guard = (("eq", ("field", "target", "condition"), lang.thaw(f["initial"])["target"]["condition"]),)
            if prior:
                old = self._owned(r.actor, prior, ("capacity",))
                split = lang.separator(old["example"], item["initial"])
                # New context must exhibit the failed distinction when testing
                # the revised branch. A convenient unrelated success is invalid.
                if not lang.predicate(split, lang.thaw(f["initial"])):
                    raise ValueError("revision practice did not test the counterexample distinction")
                program = ("if", split, program, ("call", prior))
                guard = old["guard"]
            lang.validate(program, caps)
            out.append(self._new9("capacity", r, operation, p, prior=prior, program=program,
                guard=guard, goal=f["goal"], practice=f["ref"], observations=f["observations"],
                candidate=item["ref"], example=f["initial"], split=split, previous_capacity=prior,
                dependencies=tuple(dict.fromkeys((*lang.dependencies(program), *(ref for _, ref in p["primitives"])))), status="retained"))
        return out

    @staticmethod
    def _run_values(f):
        return {k: f[k] for k in ("program", "trace", "remaining", "initial", "goal", "demand", "index", "events", "observations", "status", "failure_kind", "primitive_dependencies")}

    def _commit(self, cid, actor, key):
        old, d = self._active(actor, key)
        if not d.get("u9"): return super()._commit(cid, actor, key)
        if d["status"] != "ready": raise ValueError("full paid constructive work required")
        r, p = self._construct_inputs[old.ref.identity]
        failure, outputs = None, []
        try:
            if self._prepare9(r) != p: raise ValueError("changed processed input")
            outputs = self._derive9(r, p, old.ref, d["fuel"])
        except (ValueError, KeyError) as err:
            failure = str(err)
        event = self._event(cid, old, "succeeded" if failure is None else "failed")
        changed, command = [], None
        if failure is None:
            bref = address("u9.binding", actor, key)
            target = dict(p["slots"])["target"]
            binding = ObjectVersion(bref, WRITER, "Retained constructive work", (Role.INTERPRETATION,),
                (Account(target, (Proposition(target, "u9."+r.purpose, outputs[-1]["status"], r.context, TimeScope(self._now(), None)),),
                         self._now(), actor, p["sources"]),), occurrence=Occurrence.INTERPRETATION,
                attributes=attributes({"cue":r.cue, "context":r.context, "meaning":"constructive "+r.purpose,
                    "endorsement":ClaimStatus.ENDORSED.value, "confidence":None}))
            receipt = record(address("u4.receipt", cid), "Paid constructive receipt", {
                "actor":actor, "operation":"bind", "work_key":bref.identity.key,
                **{k:d[k] for k in ("required", "completed", "spent")},
                **{"input."+str(i):s for i,s in enumerate((bref, *p["sources"]))}})
            command = ("bind", actor, bref, p["evidence"], receipt.ref)
            self.access.preview(command, {bref:binding, receipt.ref:receipt})
            for output in outputs:
                output["binding"] = bref
                value = record(output["ref"], "Actor constructive "+output["kind"], output)
                if output["kind"] in ("candidate", "capacity"):
                    value = replace(value, roles=(Role.RECORD, Role.PROCEDURE, Role.CONCEPT),
                        facets=(Procedure(tuple(s for s,_ in p["slots"]), (), (), (), "u9.structured.v1"),
                            Concept((Proposition(output["ref"], "u9.declared_goal", codec.dumps(output["goal"]),
                                r.context, TimeScope(self._now(), None)),))))
                changed.append(value)
            changed.extend((binding, receipt))
            # Retain realized content and lawful routes, not just route labels.
            predecessor = old.ref
            for i in range(d["route_count"]):
                ref = address("u9.surface", actor, key, i)
                changed.append(record(ref, "Constructive perspective content", {"actor":actor, "operation":old.ref,
                    "predecessor":predecessor, "content":outputs[-1]["ref"], "binding":bref,
                    "origin":d[f"route.{i}.origin"], "destination":d[f"route.{i}.destination"], "purpose":r.purpose}))
                predecessor = ref
            d.update(binding=bref, **{"output."+str(i):o["ref"] for i,o in enumerate(outputs)})
        d.update(status="succeeded" if failure is None else "failed", failure=failure, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(d))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,))
        self._jobs[actor, key] = current.ref
        self._release(d, old.ref)
        if command:
            self.access._execute(command)
            for output in outputs:
                self._construct[output["ref"]] = output
                self._construct_heads[output["ref"].identity] = output["ref"]
            if r.purpose == "observe": self._construct_observed.add(p["observation"]["event"])
        return event.ref

    def _enact(self, cid, actor, key, plan):
        if plan.identity.namespace != "u9.plan": return super()._enact(cid, actor, key, plan)
        p = self._owned(actor, plan, ("plan",))
        if plan in self._construct_enacted: raise ValueError("a selected step can execute only once")
        run = self._construct[self._construct_heads[p["run"].identity]]
        if run["selected"] != plan or run["status"] != "active": raise ValueError("run no longer selects this action")
        state, _, evidence = lang.snapshot(self.participant_view(actor), p["slots"])
        current = lang.thaw(state); current["progress"] = lang.thaw(p["state"])["progress"]
        if lang.freeze(current) != p["state"]: raise ValueError("received state changed after step selection")
        kwargs = {name:current[slot]["ref"] for name,slot in lang.SCHEMAS[p["primitive"]]["inputs"]}
        r = OperationRequest(key, actor, "procedure", p["context"], evidence=evidence, procedure=p["procedure"], **kwargs)
        d = self._compile(r)
        d.update(u9_plan=plan, u9_run=run["ref"], u9_step=p["index"],
            u9_stock_role=p["primitive"]+"_stock" if p["primitive"] in ("care", "repair") else "")
        d["input."+str(len(indexed(d,"input.")))] = plan
        d["dependency."+str(len(indexed(d,"dependency.")))] = plan
        ref = job_address(actor,key)
        d["status"] = "pending" if self._can_reserve(d,ref) else "waiting"
        self._batch(cid,actor,(record(ref,"Execute constructed procedure step",d),),evidence=indexed(d,"input."))
        self._jobs[actor,key] = ref
        if d["status"] == "pending": self._reserve(d,ref)
        self._construct_enacted[plan] = ref.identity
        return ref

    def _event(self, cid, job, outcome, changed=()):
        event = super()._event(cid, job, outcome, changed)
        d = raw_attrs(job)
        if not d.get("u9_plan"): return event
        ed = raw_attrs(event)
        ed.update(u9_plan=d["u9_plan"], u9_run=d["u9_run"], u9_step=d["u9_step"])
        for value in changed:
            slot = next((n for n in ("target","tool","stock","relation") if d.get(n) and d[n].identity == value.ref.identity), None)
            if slot == "stock": slot = d["u9_stock_role"]
            if slot is None: continue
            prefix = "u9.slot."+slot+"."
            values = {"ref":value.ref}
            m = value.facet(Material)
            if m:
                values.update({n:getattr(m,n) for n in lang.MATERIAL_FIELDS}, **raw_attrs(value))
            else:
                from .records import Relation
                rel = value.facet(Relation)
                values.update(predicate=rel.predicate, **{e.role:e.target.identity for e in rel.endpoints}, **{a.name:a.value for a in rel.terms})
            ed.update({prefix+k:v for k,v in values.items()})
        return replace(event, attributes=attributes(ed))
