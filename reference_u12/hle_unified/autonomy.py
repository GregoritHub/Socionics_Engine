"""Continuing opportunities over the native U5 engine.

The scheduler receives an actor opportunity, never an outcome or a solution.
Only the pure anticipation module receives decision inputs: detached access,
actor-owned work/state, and the actor's finite wallet. Simulator result facts
are unavailable until delivery, paid reading, and paid appraisal.
"""
from dataclasses import replace, fields
from . import codec
from .compact import ValuePool, seal, unseal
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence,
    Proposition, TimeScope, Definition)
from .material import OperationStore, attrs, attributes
from .store import next_version
from .operations import record, address, job_address, indexed
from .operation_records import OperationRequest, WRITER
from .cognition import CognitiveEngine
from .cognitive_records import CognitiveRequest
from .autonomy_records import (AutonomyConfig, AutonomyState, ForecastRequest,
    LAW6, world_contract, registry)
from .anticipation import (forecast, choose, needs, evidence_for, offers,
    observed_rows, state_of, known_ref)


class AutonomousEngine(CognitiveEngine):
    SCHEMA = "hle-unified-u6-engine-v1"

    def __init__(self, world, law):
        super().__init__(world, law)
        self._pool = ValuePool(registry())
        self._configs, self._states, self._state_refs = {}, {}, {}
        self._forecast_inputs, self._forecast_results = {}, {}
        self._prediction_rows = {}

    @classmethod
    def adopt(cls, engine):
        """Exact replay migration; no direct state copying or hidden new skill."""
        return cls.restore(seal(cls.SCHEMA, unseal(engine.checkpoint(), engine.SCHEMA)))

    def configure(self, cid, config):
        return self._execute(("configure", cid, config))

    def step(self, cid, actor):
        return self._execute(("opportunity", cid, actor))

    def state(self, actor):
        return self._states[actor]  # frozen actor-owned record

    def _forecast_policy(self, view, request):
        return forecast(view, request)

    def _choose_policy(self, result, config, need, wallet):
        return choose(result, config, need, wallet)

    def _forecast_valid(self, view, request, result):
        return True

    def autonomy_view(self, actor):
        """Detached own state; no global clock, material heads or failure diagnosis."""
        state = self.state(actor)
        job = None
        if state.active:
            d = self.job_status(actor, state.active)
            job = {k: d[k] for k in ("key", "completed", "required", "spent", "status")}
            if job["status"] in ("succeeded", "failed"):
                job["status"] = "awaiting_result"
        return {"state": state, "participant": self.participant_view(actor),
                "wallet": {k: self.wallet(actor)[k] for k in ("energy", "time")}, "work": job}

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
            ValuePool(registry()).put(command)
            dispatch = {"start": self._start, "advance": self._advance, "commit": self._commit,
                "cancel": self._cancel, "enact": self._enact, "disclose": self._disclose,
                "deliver_event": self._deliver_event, "declare": self._declare,
                "configure": self._configure, "opportunity": self._step}
            if command[0] not in dispatch:
                raise ValueError("unsupported autonomy command")
            result = dispatch[command[0]](*command[1:])
            # Quiescent opportunities are not accepted commands or work. They
            # retain no growing poll history and can be retried after delivery.
            if command[0] == "opportunity" and result is None:
                return None
            self._commands[cid] = command, result
            self._events.append(self._pool.put((command, result)))
            return result

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u6.") for v in versions):
            raise ValueError("autonomy state and work cannot be imported as drafts")
        return super()._declare(cid, versions)

    def _configure(self, cid, config):
        if type(config) is not AutonomyConfig or config.actor in self._configs:
            raise ValueError("one explicit initial autonomy policy per actor")
        actor = config.actor
        known = self.access._known_refs(actor)
        if actor not in self._profiles or any(x not in known for x in
                (config.context, config.cue, config.rule, config.target)):
            raise ValueError("typed actor with processed cognitive anchors required")
        if config.partner is not None and (ObjectRef(config.partner, 1) not in known
                or Role.PERSON not in self.world.resolve(ObjectRef(config.partner, 1)).roles):
            raise ValueError("asking requires an accessible recipient identity")
        if any(a == actor and self.job_status(a, key)["status"] not in ("succeeded", "failed", "cancelled")
               for a, key in self._jobs):
            raise ValueError("configure before beginning new participant work")
        versions = []
        if LAW6.identity not in self.world._heads:
            versions.append(world_contract())
        elif self.world.resolve(LAW6) != world_contract():
            raise ValueError("U6 world contract mismatch")
        cfg = record(address("u6.policy", actor), "Declared standing demand and limits",
            {f.name: getattr(config, f.name) for f in fields(config)})
        self._batch(cid, actor, (*versions, cfg))
        self._configs[actor] = config
        self._states[actor] = AutonomyState(actor, config.target)
        return self._save(cid + ":initial", self._states[actor], "configured", "declared_standing_demand")

    def _save(self, cid, state, decision, reason, *, evidence=()):
        wallet = self.wallet(state.actor)
        state = replace(state, decision=decision, reason=reason, energy_mark=wallet["energy"], time_mark=wallet["time"])
        oldref = self._state_refs.get(state.actor)
        ref = address("u6.state", state.actor) if oldref is None else ObjectRef(oldref.identity, oldref.revision+1)
        data = {f.name: getattr(state, f.name) for f in fields(state)
                if f.name not in ("seen", "offers_at_ask", "wait_resources")}
        for name in ("seen", "offers_at_ask", "wait_resources"):
            data.update({name+"."+str(i): x for i, x in enumerate(getattr(state, name))})
        for i, source in enumerate(evidence):
            data["cause."+str(i)] = source
        data.update(policy=address("u6.policy", state.actor), contract=LAW6)
        value = ObjectVersion(ref, WRITER, "Participant continuation and motives", (Role.RECORD,),
            previous=oldref, attributes=attributes(data))
        self._batch(cid, state.actor, (value,), evidence=evidence)
        self._states[state.actor], self._state_refs[state.actor] = state, ref
        return ref

    def _custom_start(self, cid, actor, key, purpose, required, inputs, **extra):
        if (actor, key) in self._jobs or actor not in self._wallets:
            raise ValueError("new funded custom work required")
        c = self._configs[actor]
        base = OperationRequest(key, actor, "bind", c.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        d.update(record_type="operation", primitive="bind", u6=True, purpose=purpose,
            required=required, completed=0, spent=0, status="pending", failure=None, result=None,
            route_prepare=required, route_execute=0, started_tick=self._now().tick, contract=LAW6, **extra)
        d.update({"participant.0": actor, "dependency.0": self.law, "dependency.1": LAW6})
        d.update({"input."+str(i): x for i, x in enumerate(dict.fromkeys((*inputs, c.context, LAW6)))})
        ref = job_address(actor, key)
        self._batch(cid, actor, (record(ref, "Paid U6 " + purpose, d),), evidence=indexed(d, "input."))
        self._jobs[actor, key] = ref
        return ref

    def _start(self, cid, request):
        if type(request) is not ForecastRequest:
            return super()._start(cid, request)
        r = request
        if self._configs.get(r.actor) != r.config:
            raise ValueError("forecast uses the configured actor's declared bounds")
        view = self.participant_view(r.actor)
        if self._plan_stamps.get(r.plan) != self._binding_stamp(view, r.config.context):
            raise ValueError("forecast requires the current paid plan")
        result = self._forecast_policy(view, r)
        sources = tuple(dict.fromkeys(p.source for p in view.snapshot.particulars
            if p.address in evidence_for(view, result["target"], r.config.context)))
        ref = self._custom_start(cid, r.actor, r.key, "anticipate",
            max(1, result["nodes"] + len(result["visited"])), (r.plan, *result["visited"], *sources),
            plan=r.plan, nodes=result["nodes"], recalled_count=len(result["visited"]),
            horizon=r.config.horizon, node_limit=r.config.max_nodes,
            coverage=result["coverage"], unevaluated=result["unevaluated"])
        self._forecast_inputs[ref.identity] = r, result, self._binding_stamp(view, r.config.context)
        return ref

    def _commit(self, cid, actor, key):
        old, d = self._active(actor, key)
        if not d.get("u6"):
            return super()._commit(cid, actor, key)
        if d["status"] != "ready":
            raise ValueError("complete paid U6 work required")
        changed, failure = [], None
        result = None
        if any(self.world.head(ref.identity).ref != ref for ref in indexed(d, "dependency.")):
            failure = "stale_dependency"
        if d["purpose"] == "anticipate":
            r, result, stamp = self._forecast_inputs[old.ref.identity]
            if stamp != self._binding_stamp(self.participant_view(actor), r.config.context):
                failure = "changed_actor_recall"
            elif not self._forecast_valid(self.participant_view(actor), r, result):
                failure = "changed_actor_forecast_inputs"
            if failure is None:
                candidates = []
                for i, row in enumerate(result["candidates"]):
                    ref = address("u6.prediction", actor, key, i)
                    content = tuple(Proposition(result["target"], name, row[name], r.config.context,
                        TimeScope(self._now(), None)) for name in ("outcome", "condition", "wear") if row[name] is not None)
                    data = {k: row[k] for k in ("kind", "basis", "depth", "future_condition", "utility", "cost", "risk")}
                    data.update(actor=actor, operation=old.ref, plan=r.plan, horizon=r.config.horizon,
                        uncertainty=",".join(row["uncertainty"]), coverage=result["coverage"])
                    prediction = ObjectVersion(ref, WRITER, "Hypothetical " + row["kind"], (Role.CLAIM,),
                        (Account(result["target"], content, self._now(), actor, indexed(d, "input.")),),
                        occurrence=Occurrence.HYPOTHETICAL, attributes=attributes(data))
                    changed.append(prediction)
                    self._prediction_rows[ref] = row
                    candidates.append({**row, "prediction": ref})
                fref = address("u6.forecast", actor, key)
                summary = record(fref, "Bounded forecast coverage", {"actor": actor, "plan": r.plan,
                    "operation": old.ref, "nodes": result["nodes"], "coverage": result["coverage"],
                    "unevaluated": result["unevaluated"], "horizon": r.config.horizon,
                    **{"candidate."+str(i): row["prediction"] for i, row in enumerate(candidates)}})
                changed.append(summary)
                self._forecast_results[fref] = {**result, "candidates": tuple(candidates)}
                d["forecast"] = fref
        receipt = record(address("u4.receipt", cid), "U6 paid processing receipt",
            {"actor": actor, "operation": "bind", "work_key": key,
             **{k: d[k] for k in ("required", "completed", "spent")},
             **{"input."+str(i): x for i, x in enumerate(indexed(d, "input."))}})
        if failure is None:
            changed.append(receipt)
        event = self._event(cid, old, "succeeded" if failure is None else "failed")
        d.update(status="succeeded" if failure is None else "failed", failure=failure,
                 result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(d))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,))
        self._jobs[actor, key] = current.ref
        return event.ref

    def _attention(self, cid, state, purpose="attention"):
        key = cid + ":attention"
        self._custom_start(key + ":start", state.actor, key, purpose, 1, (self._state_refs[state.actor],))
        self._advance(key + ":work", state.actor, key, 1)
        self._commit(key + ":commit", state.actor, key)
        fatigue = state.fatigue + 1
        if purpose == "rest":
            fatigue = max(0, state.fatigue - 30)
        return replace(state, turns=state.turns+1, fatigue=fatigue)

    def _start_job(self, cid, state, request, kind):
        self._start(cid + ":start", request)
        return replace(state, active=request.key, active_kind=kind, wait_kind="", wait_ref=None)

    def _act(self, cid, state, row):
        c = self._configs[state.actor]
        view = self.participant_view(state.actor)
        if self._plan_stamps.get(state.plan) != self._binding_stamp(view, c.context):
            return replace(state, phase="idle", forecast=None, plan=None), "switch", "accessible_account_changed"
        r = replace(row["request"], key=cid + ":action")
        data = self._compile(r)
        data.update(u6_forecast=state.forecast, u6_prediction=row["prediction"], u6_plan=state.plan)
        n = len(indexed(data, "input."))
        data.update({"input."+str(n): state.forecast, "input."+str(n+1): row["prediction"], "input."+str(n+2): state.plan})
        ref = job_address(r.actor, r.key)
        data["status"] = "pending" if self._can_reserve(data, ref) else "waiting"
        self._batch(cid + ":action-start", r.actor, (record(ref, "Enact anticipated continuation", data),), evidence=indexed(data, "input."))
        self._jobs[r.actor, r.key] = ref
        if data["status"] == "pending":
            self._reserve(data, ref)
        return replace(state, active=r.key, active_kind="action", prediction=row["prediction"],
            last_action=row["kind"], wait_kind="", wait_ref=None), ("inspect" if row["kind"] == "inspect" else "act"), "affordable_anticipated_consequence"

    def _progress(self, cid, state):
        actor, key = state.actor, state.active
        c = self._configs[actor]
        d = self.job_status(actor, key)
        if d["status"] == "waiting" and state.wait_kind == "resource":
            # A reservation attempt is an explicit physical opportunity. Once
            # blocked, no hidden lock release becomes a policy wake signal.
            return replace(state, wait_kind="resource", wait_ref=d.get("target")), "wait", "reservation_requires_accessible_release_notice"
        if d["status"] != "ready":
            before = d["spent"]
            limit = max(1, c.work_limit + min(3, state.pressure//3) - state.fatigue//20 - state.scarcity//4)
            self._advance(cid + ":work", actor, key, limit)
            d = self.job_status(actor, key)
            state = replace(state, fatigue=state.fatigue+d["spent"]-before)
        if d["status"] == "waiting":
            resources=tuple(d[k] for k in ("target","tool","stock") if d.get(k) is not None)
            return replace(state, wait_kind="resource", wait_ref=d.get("target"), wait_resources=resources), "wait", "reservation_requires_accessible_release_notice"
        if d["status"] != "ready":
            return state, "continue", "paid_work_incomplete"
        ready_ref = self._jobs[actor, key]
        result = self._commit(cid + ":commit", actor, key)
        d = self.job_status(actor, key)
        kind = state.active_kind
        state = replace(state, active="", active_kind="")
        if kind == "read":
            return replace(state, phase=state.resume_phase, active=state.paused,
                active_kind=state.paused_kind, paused="", paused_kind=""), "continue", "delivery_read_with_own_work"
        if kind in ("plan", "integrate", "anticipate"):
            if d["status"] != "succeeded":
                return replace(state, phase="idle", plan=None, forecast=None), "switch", "own_cognitive_inputs_changed"
            if kind == "plan":
                return replace(state, plan=d["binding"], phase="forecast"), "continue", "paid_u5_plan_available"
            if kind == "anticipate":
                return replace(state, forecast=d["forecast"], phase="choose"), "continue", "paid_hypotheses_available"
            target = self.world.resolve(d["binding"]).facet(Account).referent
            if target.identity == c.target.identity:
                state = replace(state, target=target)
            return replace(state, phase="idle", plan=None, forecast=None), "continue", "paid_u5_account_retained"
        # The result ID is an own-operation receipt. Its truth, target revision,
        # outcome and failure diagnosis are deliberately not read here.
        return replace(state, phase="await", await_event=result, await_operation=ready_ref,
            await_target=d.get("target"), wait_kind="observation", wait_ref=result), "wait", "await_exact_operation_observation"

    def _matching(self, view, state):
        c = self._configs[state.actor]
        return next(((source, row) for source, row in observed_rows(view, c.context)
            if source not in state.seen and row.get("event") == state.await_event
            and row.get("operation") == state.await_operation and row.get("actor") == state.actor
            and ((row.get("target") is None and row.get("outcome") != "succeeded")
                or type(row.get("target")) is ObjectRef and state.await_target is not None
                and row["target"].identity == state.await_target.identity)), None)

    def _appraise(self, cid, state, match):
        source, row = match
        c = self._configs[state.actor]
        prediction = self._prediction_rows.get(state.prediction)
        expected = {} if prediction is None else {k: prediction[k] for k in ("outcome", "condition", "wear") if prediction[k] is not None}
        assessed = tuple(k for k in expected if k in row)
        errors = tuple(k for k in assessed if row[k] != expected[k])
        d = {"actor": state.actor, "prediction": state.prediction, "event": state.await_event,
             "observation": source, "context": c.context, "surprise": bool(errors),
             "assessed": ",".join(assessed), "errors": ",".join(errors),
             "unassessed": ",".join(k for k in expected if k not in row)}
        for k in expected:
            d["expected."+k] = expected[k]
            d["observed."+k] = row.get(k)
        error = record(address("u6.prediction_error", cid), "Paid comparison with received consequence", d)
        self._batch(cid + ":appraisal", state.actor, (error,), evidence=tuple(x for x in (state.prediction, source, self._state_refs[state.actor]) if x))
        failed = row.get("outcome") != "succeeded"
        signature = str((row.get("primitive"), row.get("outcome"), row.get("condition")))
        target = row.get("target")
        if type(target) is ObjectRef and target.identity == c.target.identity:
            state = replace(state, target=target)
        state = replace(state, observed=source, seen=state.seen+(source,),
            failures=state.failures+int(failed),
            uses=state.uses+int(not failed and row.get("primitive") == "use"
                               and type(target) is ObjectRef and target.identity == c.target.identity),
            monotony=state.monotony+1 if signature == state.last_signature else 0,
            last_signature=signature, wait_kind="", wait_ref=None, await_event=None)
        if failed and state.failures >= c.failure_limit:
            return replace(state, phase="seek_help", switched=True), "switch", "repeated_observed_failure"
        if errors or failed:
            return replace(state, phase="investigate"), "inspect", "received_prediction_error"
        if row.get("condition") is not None and type(target) is ObjectRef:
            return replace(state, phase="integrate"), "continue", "received_consequence_requires_integration"
        return replace(state, phase="idle"), "continue", "observed_result_has_no_condition_claim"

    def _request_help(self, cid, state):
        c = self._configs[state.actor]
        if c.partner is None:
            return replace(state, stopped=True, phase="stopped"), "stop", "no_accessible_assistance_recipient"
        ref = address("u6.request", cid)
        request = ObjectVersion(ref, WRITER, "Request for changed repair assistance", (Role.EVENT,),
            (Account(state.target, (), self._now(), state.actor, (self._state_refs[state.actor],)),),
            occurrence=Occurrence.ACTUAL_EVENT, attributes=attributes({"sender": state.actor,
                "receiver": c.partner, "target": state.target, "context": c.context,
                "request": "repair_assistance", "cause": state.reason,
                "paid_attention": self._jobs[state.actor, cid+":attention"]}))
        self._batch(cid + ":ask", state.actor, (request,), evidence=(self._state_refs[state.actor],))
        delivered = ObjectVersion(address("u6.request_observation", cid), WRITER,
            "Received request for assistance", (Role.OBSERVATION,),
            (Account(state.target, (), self._now(), c.partner, (ref,)),),
            occurrence=Occurrence.OBSERVATION, attributes=request.attributes)
        self._batch(cid + ":ask-observation", c.partner, (delivered,), evidence=(ref,))
        from .particulars import Selector
        selectors = tuple(Selector(a.name, "detail", ("attributes", str(i), "value")) for i, a in enumerate(delivered.attributes))
        self._disclose(cid+":request-delivery", c.partner, delivered.ref, selectors, state.target)
        return replace(state, phase="help_wait", asked=True, wait_kind="assistance", wait_ref=state.target,
            offers_at_ask=offers(self.participant_view(state.actor), c)), "ask", "need_changed_assistance_or_resource_offer"

    def _step(self, cid, actor):
        if actor not in self._configs:
            raise ValueError("actor must be configured")
        c, state = self._configs[actor], self._states[actor]
        if state.stopped:
            return None
        view = self.participant_view(actor)
        wallet = self.wallet(actor)
        state = replace(state, fatigue=state.fatigue+max(0, state.energy_mark-wallet["energy"]))
        state = replace(state, **needs(view, c, state, wallet))
        pending = view.snapshot.pending
        match = self._matching(view, state) if state.phase == "await" else None
        new_offer = bool(set(offers(view, c)) - set(state.offers_at_ask)) if state.phase == "help_wait" else False
        resource_notice = next((source for source, row in observed_rows(view, c.context)
            if state.wait_kind == "resource" and state.wait_ref is not None and source not in state.seen
            and any(type(row.get(k)) is ObjectRef and row[k].identity in {r.identity for r in state.wait_resources}
                    for k in ("target", "stock"))
            and row.get("outcome") == "succeeded"), None)
        if resource_notice is not None:
            state = replace(state, wait_kind="", wait_ref=None, wait_resources=(), seen=state.seen+(resource_notice,))
        # Waiting is quiescent; a global journal/head/cache change is not a wake.
        blocked = (state.phase == "await" and not match or state.phase == "help_wait" and not new_offer
                   or state.wait_kind == "resource")
        if blocked and not pending:
            if state.decision == "wait":
                return None
            return self._save(cid+":wait", state, "wait", "named_external_condition_not_received")
        if min(wallet["energy"], wallet["time"]) < 1:
            return self._save(cid+":stop", replace(state, stopped=True, phase="stopped"), "stop", "finite_budget_exhausted")
        # A paid rest opportunity affects fatigue debt only; native budgets are
        # still finite and both decline by exactly one quantum.
        if state.fatigue >= c.fatigue_limit and not pending:
            state = self._attention(cid, state, "rest")
            return self._save(cid+":state", state, "rest", "own_paid_work_caused_fatigue")
        state = self._attention(cid, state)
        if state.fear >= c.threat_limit and not pending and state.active_kind != "read":
            state = replace(state, stopped=True, phase="stopped")
            decision, reason = "stop", "processed_threat_exceeds_declared_boundary"
        elif pending and state.active_kind != "read":
            r = OperationRequest(cid+":read", actor, "read", c.context, delivery=pending[0].key)
            waiting_kind, waiting_ref = state.wait_kind, state.wait_ref
            state = self._start_job(cid, replace(state, resume_phase=state.phase,
                paused=state.active, paused_kind=state.active_kind), r, "read")
            state = replace(state, wait_kind=waiting_kind, wait_ref=waiting_ref)
            decision, reason = "continue", "pay_to_read_delivered_information"
        elif state.active:
            if min(self.wallet(actor)[k] for k in ("energy", "time")) == 0:
                return self._save(cid+":stop", replace(state, stopped=True, phase="stopped"), "stop", "finite_budget_exhausted_with_unfinished_work")
            state, decision, reason = self._progress(cid, state)
        elif match:
            state, decision, reason = self._appraise(cid, state, match)
        elif state.phase == "help_wait" and new_offer:
            state = replace(state, phase="idle", asked=False, plan=None, forecast=None, wait_kind="", wait_ref=None)
            decision, reason = "switch", "received_changed_assistance"
        elif state.phase == "seek_help":
            state, decision, reason = self._request_help(cid, state)
        elif state.fear >= c.threat_limit:
            state = replace(state, stopped=True, phase="stopped")
            decision, reason = "stop", "processed_threat_exceeds_declared_boundary"
        elif state.phase == "investigate":
            r = OperationRequest(cid+":investigate", actor, "inspect", c.context,
                target=state.target, evidence=evidence_for(view, state.target, c.context))
            state = self._start_job(cid, replace(state, prediction=None, last_action="inspect"), r, "action")
            decision, reason = "inspect", "test_received_surprise"
        elif state.phase == "integrate":
            rows = view.resolve(state.observed)
            target = next(p.value for p in rows if p.address.key == "target")
            r = CognitiveRequest(cid+":integrate", actor, "integrate", c.context, c.cue, target, c.rule,
                tuple(p.address for p in rows), visit_limit=c.visit_limit)
            state = self._start_job(cid, state, r, "integrate")
            decision, reason = "continue", "integrate_processed_consequence"
        elif state.uses >= c.goal_uses:
            state = replace(state, stopped=True, phase="stopped")
            decision, reason = "stop", "standing_demand_satisfied_by_observed_work"
        elif state.phase == "forecast":
            state = self._start_job(cid, state, ForecastRequest(cid+":forecast", actor, state.plan, c), "anticipate")
            decision, reason = "continue", "evaluate_bounded_continuations"
        elif state.phase == "choose":
            result = self._forecast_results[state.forecast]
            row = self._choose_policy(result, c, {k: getattr(state, k) for k in ("pressure", "fear", "scarcity", "boredom")}, self.wallet(actor))
            if row is None:
                state = replace(state, stopped=True, phase="stopped")
                decision, reason = "stop", "no_affordable_evaluated_continuation"
            elif row["kind"] == "inspect" and state.last_action == "inspect" and state_of(view, state.target, c.context)["condition"] == "damaged":
                state, decision, reason = self._request_help(cid, state)
            else:
                state, decision, reason = self._act(cid, state, row)
        elif state.boredom >= c.boredom_limit and not state.explored and c.explore_target:
            target = known_ref(view, c.explore_target.identity)
            if target is None:
                state = replace(state, explored=True)
                decision, reason = "switch", "exploration_target_not_accessible"
            else:
                r = OperationRequest(cid+":explore", actor, "inspect", c.context, target=target,
                    evidence=evidence_for(view, target, c.context))
                state = self._start_job(cid, replace(state, explored=True, prediction=None, last_action="explore"), r, "action")
                decision, reason = "explore", "repeated_observed_outcomes_caused_boredom"
        else:
            evidence = tuple(a for a in evidence_for(view, state.target, c.context)
                if view.detail(a).source not in state.offers_at_ask)
            r = CognitiveRequest(cid+":plan", actor, "plan", c.context, c.cue, state.target, c.rule,
                evidence, visit_limit=c.visit_limit)
            state = self._start_job(cid, state, r, "plan")
            decision, reason = "continue", "outstanding_demand_needs_paid_plan"
        evidence = tuple(dict.fromkeys(x for x in (state.plan, state.forecast, state.prediction, state.observed) if x))
        return self._save(cid+":state", state, decision, reason, evidence=evidence)

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"initial", "law", "nodes", "commands", "world", "access"}:
            raise ValueError("invalid autonomous checkpoint")
        result = cls(OperationStore.restore(data["initial"]), codec.decode(data["law"]))
        raw = ValuePool(registry())
        raw.load_nodes(data["nodes"])
        for token in data["commands"]:
            command, expected = raw.get(raw.import_token(token))
            if result._execute(command) != expected:
                raise ValueError("autonomous result replay mismatch")
        if result.world.checkpoint() != data["world"] or result.access.checkpoint() != data["access"]:
            raise ValueError("autonomy, material or access replay mismatch")
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("noncanonical autonomous history")
        return result
