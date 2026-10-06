"""U10 paid, receiver-owned meaning over the native U9 operation engine.

Private intention is retained separately from the public envelope. Delivery,
reading, interpretation, lexical induction, response, physical practice and
commitment settlement are distinct operations with immutable histories.
"""
from copy import deepcopy
from dataclasses import fields, replace
from . import codec, composition_language as lang, language_semantics as sem
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence,
    ClaimStatus, Proposition, TimeScope, Procedure, Concept, Relation, Endpoint, Attribute)
from .store import next_version
from .material import attrs as raw_attrs, attributes
from .operations import address, job_address
from .operation_records import OperationRequest, WRITER
from .cognitive_routes import route, flatten_route, progress
from .development import record
from .composition import CompositionEngine
from .language_records import LanguageRequest, LAW10, world_contract, registry


class LanguageEngine(CompositionEngine):
    SCHEMA = "hle-unified-u10-engine-v1"

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._language_inputs, self._language, self._language_heads, self._lexicon = {}, {}, {}, {}
        self._responded = set()

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u10.") for v in versions):
            raise ValueError("generated language, meanings and promises cannot be imported")
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith("u10.") and source != LAW10:
            d = self._language.get(source)
            if d is None or (d["actor"] != actor and not (d["kind"] == "message" and d["receiver"] == actor)):
                raise ValueError("private language content requires its own public utterance")
            if d["actor"] != actor:
                value = self.world.resolve(source)
                public = {(a.name,("attributes",str(i),"value")) for i,a in enumerate(value.attributes)
                          if a.name in ("payload","wording")}
                if subject not in (None,source) or any((s.key,s.path) not in public for s in selectors):
                    raise ValueError("delivery exposes only public wording and payload")
        return super()._disclose(cid, actor, source, selectors, subject)

    def language_view(self, actor):
        return tuple(deepcopy(self._language[r]) for r in self._language_heads.values()
                     if self._language[r]["actor"] == actor)

    def _owned10(self, actor, ref, kinds=None):
        d = self._language.get(ref)
        if not d or d["actor"] != actor or self._language_heads[ref.identity] != ref or kinds and d["kind"] not in kinds:
            raise ValueError("current actor-owned language record required")
        return d

    def _lex(self, actor, context, peer):
        return {token: self._language[ref] for (owner, scope, partner, token), ref in self._lexicon.items()
                if (owner, scope, partner) == (actor, context, peer)}

    def _prepare10(self, r):
        view = self.participant_view(r.actor)
        known = self.access._known_refs(r.actor)
        if (r.actor not in self._profiles or r.cue not in self._references
                or any(ref not in known for ref in (r.context, r.cue))):
            raise ValueError("processed context and source cue required")
        if Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("context role required")
        focus, wire, practice = None, None, None
        if r.purpose in ("interpret", "learn"):
            details = {p.address.key: p.value for p in view.resolve(r.focus)}
            if r.focus.identity.namespace != "u10.message" or "payload" not in details:
                raise ValueError("message delivery must be separately read")
            wire = dict(codec.loads(details["payload"]))
            if wire["ref"] != r.focus or wire["receiver"] != r.actor or wire["context"] != r.context or wire["cue"] != r.cue:
                raise ValueError("message recipient and contextual scope mismatch")
        elif r.purpose == "coin": focus = self._owned(r.actor, r.focus, ("capacity",))
        elif r.purpose == "challenge": focus = self._owned(r.actor, r.focus, ("run",))
        elif r.purpose == "send":
            if ObjectRef(r.peer, 1) not in known: raise ValueError("speaker must know the addressee")
            if r.focus: focus = self._owned(r.actor, r.focus, ("run",))
        else:
            focus = self._owned10(r.actor, r.focus, ("interpretation",) if r.purpose == "respond" else ("commitment",))
        if focus and (focus["context"], focus["cue"]) != (r.context, r.cue):
            raise ValueError("owned language work cannot cross its context")
        if r.practice: practice = self._owned(r.actor, r.practice, ("run",))
        peer = wire["speaker"] if wire else r.actor
        interpretation = None
        if r.purpose == "challenge":
            candidate = self._construct[focus["program"]]
            if "interpretation" not in candidate: raise ValueError("challenge requires an interpreted procedure")
            interpretation = self._language[candidate["interpretation"]]
            peer = interpretation["speaker"]
        lexicon = self._lex(r.actor, r.context, peer)
        if r.purpose == "respond": lexicon = self._lex(r.actor, r.context, focus["speaker"])
        # Preparation retains actor evidence only. New paid processing during a
        # partial operation changes this stamp; hidden world changes cannot.
        details = view.snapshot.particulars
        sources = tuple(dict.fromkeys(p.source for p in details))
        evidence = tuple(p.address for p in details)
        caps = self._capacities9(r.actor, r.context)
        samples = ()
        if r.purpose == "coin":
            samples = tuple(d for ref in self._construct_heads.values() for d in (self._construct[ref],)
                if d["kind"] == "run" and d["actor"] == r.actor and d["context"] == r.context
                and d["status"] == "succeeded" and (d["program"] == focus["ref"] or ref == focus["practice"]))
        return deepcopy(dict(focus=focus, wire=wire, practice=practice, lexicon=lexicon, capacities=caps,
            primitives=lang.acquired(view, r.context), sources=sources, evidence=evidence, samples=samples,
            particulars=details, responded=r.focus in self._responded, interpretation=interpretation))

    def _start(self, cid, request):
        if type(request) is not LanguageRequest: return super()._start(cid, request)
        r = request
        if (r.actor, r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("unused key and no competing actor work required")
        p = self._prepare10(r)
        syntax_units = sem.units(r.body) + sem.units(tuple(sorted((p["wire"] or {}).items())))
        lexical_units = sum(sem.units(d.get("program")) + sem.units(d.get("examples", ())) for d in p["lexicon"].values())
        focus_units = sem.units(tuple(sorted((p["focus"] or {}).items())))
        sample_units = sum(sem.units(tuple(sorted(s.items()))) for s in p["samples"])
        units = 1 + len(p["evidence"]) + syntax_units + lexical_units + focus_units + sample_units
        tim = raw_attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        outward = r.purpose in ("send", "respond")
        origin, destination, polarity = ("I", "IT", "expenditure") if outward else ("IT", "I", "accumulation")
        rows = route(tim, self._cursors[r.actor], ("fi", "si") if outward else ("si", "fi"), origin, destination, polarity)
        route_units = sum(sum(row["charges"]) + row["content_units"] for row in rows)
        base = OperationRequest(r.key, r.actor, "bind", r.context)
        d = {f.name: getattr(base, f.name) for f in fields(base) if f.name not in ("participants", "evidence")}
        d.update(record_type="operation", primitive="bind", u10=True, purpose=r.purpose,
            cue=r.cue, focus=r.focus, target=r.focus or r.context, contract=LAW10,
            required=units+route_units, completed=0, spent=0, recall_units=units,
            route_prepare=units, route_execute=route_units, status="pending", failure=None, result=None,
            active_start=self._cursors[r.actor], tim=tim, origin=origin, destination=destination, polarity=polarity,
            started_tick=self._now().tick, evidence_count=len(p["evidence"]), syntax_units=syntax_units,
            lexical_units=lexical_units, focus_units=focus_units, sample_units=sample_units, **flatten_route(rows))
        refs = tuple(dict.fromkeys((r.context, r.cue, *p["sources"], *((r.focus,) if r.focus else ()))))
        for prefix, values in (("input.", refs), ("source.", p["sources"]), ("participant.", (r.actor,)),
                              ("lock.", (r.actor,)), ("dependency.", (LAW10, self.law, r.cue, self._profiles[r.actor]))):
            d.update({prefix+str(i): x for i, x in enumerate(values)})
        ref = job_address(r.actor, r.key)
        added = () if LAW10.identity in self.world._heads else (world_contract(),)
        if not added and self.world.resolve(LAW10) != world_contract(): raise ValueError("language contract mismatch")
        self._batch(cid, r.actor, (*added, record(ref, "Paid language " + r.purpose, d)), evidence=refs)
        self._jobs[r.actor, r.key] = ref
        self._reserve(d, ref)
        self._language_inputs[ref.identity] = r, p
        return ref

    def _advance(self, cid, actor, key, work_limit):
        ref = super()._advance(cid, actor, key, work_limit)
        d = raw_attrs(self.world.resolve(ref))
        if d.get("u10"): self._cursors[actor] = progress(d)[0]
        return ref

    def _new10(self, kind, r, op, p, *, prior=None, suffix="", **values):
        ref = address("u10."+kind, r.actor, r.key, suffix) if prior is None else ObjectRef(prior.identity, prior.revision+1)
        return dict(ref=ref, kind=kind, actor=r.actor, context=r.context, cue=r.cue,
                    operation=op, sources=p["sources"], **values)

    def _message10(self, r, op, p, peer, act, body=(), **content):
        d = self._new10("message", r, op, p, receiver=peer, act=act, status="emitted")
        wire = dict(ref=d["ref"], speaker=r.actor, receiver=peer, context=r.context, cue=r.cue, act=act, body=body, **content)
        d.update(payload=codec.dumps(tuple(sorted(wire.items()))), wording=act + ": " + sem.render(body) if body else act)
        return d

    def _ground10(self, view, body, slots, goal):
        if not slots: raise sem.MeaningGap("missing_referents")
        try: state, _, _ = lang.snapshot(view, slots)
        except ValueError as e: raise sem.MeaningGap("unprocessed_referents") from e
        for test in (*sem.tests(body), *goal):
            sem.validate_test(test)
            try: lang.predicate(test, lang.thaw(state))
            except (KeyError, ValueError) as e: raise sem.MeaningGap("unprocessed_relation") from e
        return state

    def _derive10(self, r, p, op):
        f, wire = p["focus"], p["wire"]
        view = self.participant_view(r.actor)
        if r.purpose == "challenge":
            if f["status"] != "failed" or f["failure_kind"] != "observed_counterexample":
                raise ValueError("only observed counterexamples challenge meaning")
            interpreted = p["interpretation"]
            payload = {x.address.key:x.value for x in view.resolve(interpreted["message"])}
            original = dict(codec.loads(payload["payload"]))
            if original["body"][0] != "word": raise ValueError("composite blame remains unresolved; isolate the term")
            term = original["body"][1]
            old = p["lexicon"][term]
            example = dict(message=interpreted["message"], target=lang.thaw(f["initial"])["target"]["ref"].identity,
                initial=f["initial"], program=("seq",tuple(("act",a) for a in f["trace"])), success=False, events=f["events"])
            examples = [dict(e) for e in old["examples"]]
            if any(set(e["events"]) & set(example["events"]) for e in examples): raise ValueError("counterexample already processed")
            examples.append(example)
            status, program, split = sem.induce(examples)
            entry = self._new10("lexeme",r,op,p,prior=old["ref"],term=term,partner=interpreted["speaker"],
                program=program,status=status,split=split,examples=tuple(tuple(sorted(e.items())) for e in examples),practices=(),capacity=None)
            report = self._message10(r,op,p,interpreted["speaker"],"counterexample",term=term,events=f["events"],
                target=lang.thaw(f["initial"])["target"]["ref"],goal=f["goal"],run=f["ref"],reply_to=interpreted["message"])
            return [entry,report]
        if r.purpose == "coin":
            if len({dict(s["slots"])["target"].identity for s in p["samples"]}) < 2:
                raise ValueError("two successful distinct targets required before coining")
            program = sem.expand(f["program"], {}, p["capacities"])
            term = r.term or "vek" + str(1 + len(self._lex(r.actor, r.context, r.actor)))
            old = self._lex(r.actor, r.context, r.actor).get(term)
            if old and old["program"] == program: raise ValueError("no new stable distinction")
            return [self._new10("lexeme", r, op, p, prior=old["ref"] if old else None,
                term=term, partner=r.actor, program=program, status="stable", split=f.get("split"),
                examples=(), practices=tuple(s["ref"] for s in p["samples"]), capacity=f["ref"])]
        if r.purpose == "send":
            if r.act in ("demonstration", "counterexample"):
                entry = p["lexicon"].get(r.term)
                if not entry or entry["status"] != "stable": raise ValueError("demonstration requires own stable lexical use")
                positive = r.act == "demonstration"
                if (f["status"] == "succeeded") != positive or f["status"] not in ("succeeded", "failed"):
                    raise ValueError("speech act must preserve observed actual outcome")
                if positive and sem.trace_for(entry["program"], f["initial"]) != f["trace"]:
                    raise ValueError("demonstration does not exhibit the speaker's current term")
                return [self._message10(r, op, p, r.peer, r.act, term=r.term, events=f["events"],
                    target=lang.thaw(f["initial"])["target"]["ref"], goal=f["goal"], run=f["ref"])]
            meaning = sem.expand(r.body, p["lexicon"], p["capacities"])
            state = self._ground10(view, meaning, r.slots, r.goal)
            if r.act in ("statement", "question") and meaning[0] != "test":
                raise ValueError("statement/question takes a grounded relation")
            if r.act == "explanation" and meaning[0] != "because": raise ValueError("explanation must state a reason")
            if r.act not in ("statement", "question"):
                program = sem.executable(meaning); lang.validate(program, {})
                if not lang.primitive_names(program, {}) <= dict(p["primitives"]).keys():
                    raise ValueError("speaker cannot express an unacquired action as its own procedure")
                if not r.goal: raise ValueError("practical speech requires an explicit goal")
            intent = self._new10("intention", r, op, p, peer=r.peer, act=r.act, meaning=meaning,
                                 slots=r.slots, goal=r.goal, state=state, status="expressed")
            output = [intent]
            commitment = None
            if r.act == "commitment":
                promise = self._new10("commitment", r, op, p, beneficiary=r.peer, program=sem.executable(meaning),
                    slots=r.slots, goal=r.goal, status="open", practice=None, observations=())
                output.append(promise); commitment = promise["ref"]
            output.append(self._message10(r, op, p, r.peer, r.act, sem.public_form(r.body, p["capacities"]),
                slots=r.slots, goal=r.goal, commitment=commitment))
            intent["message"] = output[-1]["ref"]
            return output
        if r.purpose == "learn":
            if wire["act"] not in ("demonstration", "counterexample"): raise ValueError("learning needs observed demonstration")
            example = sem.observed_demo(view, wire)
            old = p["lexicon"].get(wire["term"])
            examples = [] if old is None else [dict(x) for x in old["examples"]]
            if any(set(e["events"]) & set(example["events"]) for e in examples):
                raise ValueError("duplicate demonstrations cannot create independent stability")
            examples.append(example)
            status, program, split = sem.induce(examples)
            return [self._new10("lexeme", r, op, p, prior=old["ref"] if old else None,
                term=wire["term"], partner=wire["speaker"], program=program, status=status, split=split,
                examples=tuple(tuple(sorted(e.items())) for e in examples), practices=(), capacity=None)]
        if r.purpose == "interpret":
            if wire["act"] == "counterexample":
                example = sem.observed_demo(view,wire)
                return [self._new10("interpretation",r,op,p,message=r.focus,speaker=wire["speaker"],act=wire["act"],
                    meaning=("counterexample",wire["term"],example["program"],example["initial"]),slots=(),goal=wire["goal"],
                    state=example["initial"],status="understood",reason="observed_counterexample",assessment="contradicted",lexical_versions=())]
            if wire["act"] == "demonstration":
                raise ValueError("demonstrations use the separate paid learning operation")
            status, reason, meaning, assessment, state, token = "understood", None, (), None, (), ""
            if wire["act"] in ("clarification", "answer"):
                meaning = wire["body"]
            else:
                try:
                    meaning = sem.expand(wire["body"], p["lexicon"])
                    state = self._ground10(view, meaning, wire["slots"], wire["goal"])
                    if meaning[0] in ("test", "because"):
                        test = meaning[1] if meaning[0] == "test" else meaning[1][1]
                        assessment = "supported" if lang.predicate(test, lang.thaw(state)) else "contradicted"
                except sem.MeaningGap as e:
                    status, reason, token = "clarification", e.reason, e.term
            result = self._new10("interpretation", r, op, p, message=r.focus, speaker=wire["speaker"],
                act=wire["act"], meaning=meaning, slots=wire.get("slots", ()), goal=wire.get("goal", ()),
                state=state, status=status, reason=reason, assessment=assessment,
                lexical_versions=tuple(d["ref"] for d in p["lexicon"].values()))
            output = [result]
            if status == "clarification":
                output.append(self._message10(r, op, p, wire["speaker"], "clarification", ("clarify", reason, token), reply_to=r.focus))
            return output
        if r.purpose == "respond":
            if p["responded"]: raise ValueError("an interpretation can receive one practical response")
            result = self._new10("response", r, op, p, interpretation=f["ref"], message=f["message"],
                status="acknowledged", reason=None, candidate=None, demand=None)
            if f["status"] != "understood":
                result.update(status="deferred", reason="meaning_unresolved"); return [result]
            if f["act"] in ("statement", "question", "explanation") and f["assessment"] is not None:
                return [result, self._message10(r, op, p, f["speaker"], "answer", ("answer", f["assessment"], f["meaning"]), reply_to=f["message"])]
            if f["act"] != "request": return [result]
            current_lex = tuple(d["ref"] for d in p["lexicon"].values())
            if current_lex != f["lexical_versions"]:
                result.update(status="deferred", reason="meaning_changed_reinterpret"); return [result]
            program = sem.executable(f["meaning"])
            lang.validate(program, {})
            if not lang.primitive_names(program, {}) <= dict(p["primitives"]).keys():
                result.update(status="refused", reason="own_practice_required"); return [result]
            try: state = self._ground10(view, program, f["slots"], f["goal"])
            except sem.MeaningGap:
                result.update(status="deferred", reason="received_state_incomplete"); return [result]
            if f["meaning"][0] == "because" and not lang.predicate(f["meaning"][1][1], lang.thaw(state)):
                result.update(status="refused", reason="reason_contradicted"); return [result]
            name, _, _ = lang.take_step((program,), state, {}, max(1, sem.units(program)))
            if lang.action(state, name, r.actor) is None:
                result.update(status="refused", reason="received_permission_or_resource_limit"); return [result]
            if lang.meets(state, f["goal"]):
                result.update(status="unnecessary", reason="goal_already_received"); return [result]
            demand = self._new10("demand", r, op, p, slots=f["slots"], state=state, goal=f["goal"],
                status="open", reason="interpreted_request", origin=None, interpretation=f["ref"])
            candidate = self._new10("candidate", r, op, p, slots=f["slots"], program=program, initial=state,
                goal=f["goal"], search=None, demand=demand["ref"], revises=None, status="hypothesis",
                dependencies=tuple(ref for _, ref in p["primitives"]), interpretation=f["ref"])
            result.update(status="planned", candidate=candidate["ref"], demand=demand["ref"])
            return [demand, candidate, result]
        if f["status"] != "open": raise ValueError("commitment is already settled")
        run = p["practice"]
        if (run["context"] != r.context or run["status"] != "succeeded" or run["goal"] != f["goal"]
                or tuple((s, ref.identity) for s, ref in run["slots"]) != tuple((s, ref.identity) for s, ref in f["slots"])):
            raise ValueError("promise needs matching actual successful actor performance")
        program = sem.expand(self._construct[run["program"]]["program"], {}, p["capacities"])
        if program != f["program"]: raise ValueError("performance differs from promised procedure")
        if raw_attrs(self.world.resolve(run["operation"]))["started_tick"] < raw_attrs(self.world.resolve(f["operation"]))["started_tick"]:
            raise ValueError("old performance cannot fulfill a new promise")
        return [self._new10("commitment", r, op, p, prior=f["ref"], beneficiary=f["beneficiary"],
            program=f["program"], slots=f["slots"], goal=f["goal"], status="fulfilled",
            practice=run["ref"], observations=run["observations"])]

    def _commit(self, cid, actor, key):
        old, d = self._active(actor, key)
        if not d.get("u10"): return super()._commit(cid, actor, key)
        if d["status"] != "ready": raise ValueError("full paid language work required")
        r, p = self._language_inputs[old.ref.identity]
        failure, outputs = None, []
        try:
            if self._prepare10(r) != p: raise ValueError("changed processed language input")
            outputs = self._derive10(r, p, old.ref)
        except (ValueError, KeyError) as e: failure = str(e)
        event = self._event(cid, old, "succeeded" if failure is None else "failed")
        changed, command = [], None
        if failure is None:
            bref = address("u10.binding", actor, key)
            subject = r.context
            binding = ObjectVersion(bref, WRITER, "Retained grounded language work", (Role.INTERPRETATION,),
                (Account(subject, (Proposition(subject, "u10."+r.purpose, outputs[-1]["status"], r.context, TimeScope(self._now(), None)),),
                    self._now(), actor, p["sources"]),), occurrence=Occurrence.INTERPRETATION,
                attributes=attributes({"cue":r.cue,"context":r.context,"meaning":"grounded language "+r.purpose,
                    "endorsement":ClaimStatus.ENDORSED.value,"confidence":None}))
            receipt = record(address("u4.receipt", cid), "Paid grounded language receipt", {
                "actor":actor,"operation":"bind","work_key":bref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},
                **{"input."+str(i):s for i,s in enumerate((bref,*p["sources"]))}})
            command = ("bind", actor, bref, p["evidence"], receipt.ref)
            self.access.preview(command, {bref:binding,receipt.ref:receipt})
            for o in outputs:
                o["binding"] = bref
                value = record(o["ref"], "Actor language "+o["kind"], o)
                if o["kind"] == "candidate":
                    value = replace(value, roles=(Role.RECORD,Role.PROCEDURE,Role.CONCEPT),
                        facets=(Procedure(tuple(s for s,_ in o["slots"]),(),(),(),"u9.structured.v1"),
                            Concept((Proposition(o["ref"],"u10.communicated_goal",codec.dumps(o["goal"]),r.context,TimeScope(self._now(),None)),))))
                if o["kind"] == "commitment":
                    value = replace(value, roles=(Role.RECORD,Role.COMMITMENT), facets=(Relation("promised_procedure",
                        (Endpoint("promisor",ObjectRef(actor,1)),Endpoint("beneficiary",ObjectRef(o["beneficiary"],1))),
                        True,r.context,TimeScope(self._now(),None),(Attribute("status",o["status"]),)),))
                changed.append(value)
            changed.extend((binding,receipt))
            for i in range(d["route_count"]):
                changed.append(record(address("u10.surface",actor,key,i), "Grounded communication perspective", {
                    "actor":actor,"operation":old.ref,"content":outputs[-1]["ref"],"binding":bref,
                    "origin":d[f"route.{i}.origin"],"destination":d[f"route.{i}.destination"]}))
            d.update(binding=bref,**{"output."+str(i):o["ref"] for i,o in enumerate(outputs)})
        d.update(status="succeeded" if failure is None else "failed",failure=failure,result=event.ref,finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(d))
        self._batch(cid,actor,(current,*changed,event),evidence=(old.ref,))
        self._jobs[actor,key] = current.ref
        self._release(d,old.ref)
        if command:
            self.access._execute(command)
            for o in outputs:
                self._language[o["ref"]] = o
                self._language_heads[o["ref"].identity] = o["ref"]
                if o["kind"] == "lexeme": self._lexicon[actor,r.context,o["partner"],o["term"]] = o["ref"]
                if o["kind"] in ("candidate","demand"):
                    self._construct[o["ref"]] = o; self._construct_heads[o["ref"].identity] = o["ref"]
            if r.purpose == "respond": self._responded.add(r.focus)
        return event.ref
