"""Experimental demand controller, learned cue retrieval, and actual R11 work.

Only _external_start and _close evaluate fixture ownership. Participant stages
use actor-owned records. No TIM-to-meaning or phase-to-card mapping is supplied.
"""
from collections import Counter
from dataclasses import replace
import hashlib
import json
import random

from hle.assessment_demo import declare, drain
from hle.assessment_records import BeginTrial, EndTrial
from hle.cards import card
from hle.codec import canonical, encode
from hle.contracts import ActionRequest, ClaimStatus, Kind, Moment, Proposition, Ref, TimeScope, WorkStatus
from hle.crux import Perspective
from hle.demo import ALICE, BOB, ROOM
from hle.memory import observed_revision
from hle.memory_records import BindDraft, ContextDraft, MemoryCommand, RecallQuery, WriteDraft
from hle.metabolism_records import ApplyDraft, EmbodyDraft, MetabolicCommand, ProcessingPolicy, Profile, TheorizeDraft
from hle.organization import OrganizationWorld
from hle.socion_records import AgentPolicy
from hle.world_records import Attempt, Credit, Entity, INSPECT, Ownership, Tick, TRANSFER, Wallet, WorldConfig
from .learning import allocate, describe, experienced_unavailability, learn, read_meaning

SCENES = ("a", "b", "c", "d")
POLICIES = ("learned", "frozen", "shuffled", "fixed_direct", "fixed_cautious")
SCOPE = TimeScope(Moment(0, 0), None)
EMPTY_CUE = card("arcana:0").ref


def owned_wallet(world):
    view, _ = world.select_input(BOB)
    amounts = {r.unit.key: r.amount for r in view.available}
    return amounts["r2.energy_quantum"], amounts["r2.time_quantum"]


class Session:
    def __init__(self, tim="iee", seed=17, history="east_reliable", budget=8000,
                 policy="learned", time_budget=None, discovery="forward", labels="cards"):
        if policy not in POLICIES or history not in ("east_reliable", "west_reliable"):
            raise ValueError("unknown policy/history")
        if discovery not in ("forward", "reverse") or labels not in ("cards", "anonymous"):
            raise ValueError("unknown discovery or display control")
        self.config = dict(tim=tim, seed=seed, history=history, budget=budget, policy=policy,
                           time_budget=time_budget, discovery=discovery, labels=labels)
        self.history, self.rows, self.studies = [], [], []
        self.episode, self.phases, self.paid_calls, self.spent = 0, 0, 0, 0
        self.stage, self.external_credit, self.external_spent = "start", 0, 0
        self.assignments, self.contexts = {}, {}
        self.previous = self.selected = self.proposed = None
        self.meaning_recall = self.selection_recall = self.recall = None
        self.account = self.application = self.memory = self.decision = None
        self.scene = self.item = self.cue = self.target = None
        self.desired = None  # Evaluator/fixture only, never passed into learning or R4.
        self.check = self.empty_account = False
        self.start_cost = 0
        self.costs = Counter()
        order = list((19, 20, 21)); random.Random(seed).shuffle(order)
        self.cues = tuple(card(f"arcana:{rank}").ref for rank in order)
        items = [Ref(Kind.ENTITY, f"object:{n:02d}", 1) for n in range(40)]
        random.Random(seed).shuffle(items)
        self.items = tuple(items)
        self.original_cues = tuple(card(f"minor:{suit}:{rank}").ref for suit in ("Cup", "Sword", "Coin", "Wand") for rank in range(1, 11))
        # Forty initial writes (2 each), forty binds (2 each), four contexts (1 each).
        self.setup_cost = 164
        time = budget if time_budget is None else time_budget
        cfg = WorldConfig(ROOM, tuple(Entity(a, a.key, "actor") for a in (ALICE, BOB)) +
            tuple(Entity(i, i.key, "object") for i in items), (ALICE, BOB),
            tuple(Ownership(i, BOB) for i in items),
            (Wallet(ALICE, 100000, 100000), Wallet(BOB, budget + self.setup_cost, time + self.setup_cost)),
            (), ((ALICE, BOB), (BOB, ALICE)))
        self.world = OrganizationWorld(cfg, (Profile(ALICE, "lse"), Profile(BOB, tim)),
            ProcessingPolicy(), (AgentPolicy(ALICE), AgentPolicy(BOB)))
        w = self.world
        view, _ = w.select_input(BOB)
        for n, item in enumerate(items):
            obs = next(o for o in view.observations if any(p.subject == item and p.relation == "owned_by" for p in o.content))
            draft, basis = observed_revision(view, obs.ref, item, "owned_by", f"original:{n}")
            k = f"setup:write:{n}"
            w.execute(MemoryCommand(k, k, BOB, draft, basis))
            memory = w.memory_head(BOB, f"original:{n}")
            k = f"setup:bind:{n}"
            w.execute(MemoryCommand(k, k, BOB, BindDraft(f"original:{n}", self.original_cues[n], ROOM, memory.ref, SCOPE), (memory.ref,)))
        for scene in SCENES:
            k = f"setup:context:{scene}"
            w.execute(MemoryCommand(k, k, BOB, ContextDraft(f"scene:{scene}", f"experienced scene {scene}")))
            self.contexts[scene] = w._journal[-1].contexts[0].ref
        if owned_wallet(w) != (budget, time): raise AssertionError("setup billing mismatch")
        self.studies.append(declare(w, "development", "original:0", items[0],
            features=("claim_links", "perspective"), strict=True))

    @property
    def done(self): return self.episode == 40

    @property
    def phase(self): return self.phases % 9, self.phases % 3

    @property
    def round(self): return self.episode // 4

    def _external_start(self):
        w = self.world
        if self.episode == 12:
            for n in range(10): w.execute(Tick(f"quiet:{n}"))
        order = SCENES if self.config["discovery"] == "forward" else tuple(reversed(SCENES))
        self.scene, self.item = order[self.episode % 4], self.items[self.episode]
        owns = self.scene in ("a", "c")
        if self.config["history"] == "west_reliable": owns = not owns
        if self.round >= 5: owns = not owns
        self.desired = BOB if owns else ALICE
        current = w.truth.current_fact(self.item, "owned_by", ROOM).object
        if current != self.desired:
            k = f"fixture:{self.episode}"
            if current == BOB:
                w.execute(Credit(k + ":credit", BOB, 2, 2, "exact external fixture transfer cost"))
                self.external_credit += 2
            event = w.execute(Attempt(k, k, ActionRequest(current, TRANSFER, (self.item, self.desired), ())))
            if event.outcome != WorkStatus.COMPLETED: raise AssertionError("external fixture failed")
            if current == BOB: self.external_spent += 2
        self.start_cost = self.spent
        self.previous = self.selected = self.proposed = None
        self.meaning_recall = self.selection_recall = self.recall = None
        self.account = self.application = self.memory = self.decision = None
        self.stage = "meaning"

    def _meaning_from_recall(self, ref):
        result = self.world.recall_result(BOB, ref)
        if result.truncated: raise ValueError("incomplete meaning access")
        if not result.hits: return None
        if len(result.hits) != 1: raise ValueError("ambiguous active contextual meaning")
        return read_meaning(self.world.read_revision(BOB, result.hits[0].memory), BOB)

    def _choose(self):
        # Pure owned association selection; no history condition or owner lookup.
        policy = self.config["policy"]
        self.cue = self.previous.cue if self.previous else allocate(self.cues, self.assignments)
        self.check = False if self.selected is None else self.selected.check
        guard = None if self.selected is None else self.selected.guard_memory
        if policy == "fixed_direct": self.check, guard = False, None
        if policy == "fixed_cautious": self.check, guard = True, None
        self.empty_account = self.check and guard is None
        self.target = (guard if self.check and guard else
            self.world.memory_head(BOB, f"original:{self.episode}").ref)
        self.stage = "decision"

    def _bind(self, key, cue, context, target):
        old = self.world.binding_head(BOB, key)
        basis = (target,) + (() if old is None else (old.ref,))
        return BindDraft(key, cue, context, target, SCOPE, None if old is None else old.ref), basis

    def _command(self, chunk):
        w, stage, e = self.world, self.stage, self.episode
        task = f"m:{e}:{stage}"
        metabolic = stage in ("theory", "apply", "embody")
        old = w.processing_job(BOB, task) if metabolic else w.memory_job(BOB, task)
        basis = ()
        if old:
            payload = old.command.payload
            if not metabolic: basis = old.command.based_on
        elif stage in ("meaning", "selection"):
            scene = self.scene if stage == "meaning" else {"a":"b", "b":"a", "c":"d", "d":"c"}[self.scene]
            payload = RecallQuery(self.cues, self.contexts[scene], w.now, relation="meaning.scene", visit_limit=8)
        elif stage == "decision":
            scope = TimeScope(w.now, None)
            values = (("decision.check", self.check), ("decision.empty", self.empty_account),
                ("decision.scene", self.scene), ("decision.source", "none" if self.selected is None else self.selected.ref))
            refs = () if self.selected is None else (self.selected.ref,)
            payload = WriteDraft(f"decision:{e}", tuple(Proposition(self.cue, k, v, ROOM, scope) for k, v in values),
                refs, ClaimStatus.TENTATIVE, None, "bounded selection from paid owned contextual recall")
            basis = tuple(dict.fromkeys((self.meaning_recall,) + (() if self.selection_recall is None else (self.selection_recall,)) + refs))
        elif stage == "bridge":
            payload, basis = self._bind("working:lesson", self.cue, ROOM, self.target)
            basis += (self.decision,)
        elif stage == "recall":
            cues = (EMPTY_CUE,) if self.empty_account else (self.original_cues[e], self.cue)
            payload = RecallQuery(cues, ROOM, w.now, relation="owned_by", visit_limit=16)
        elif stage == "theory": payload = TheorizeDraft(self.recall, self.item, ALICE)
        elif stage == "apply": payload = ApplyDraft(self.account)
        elif stage == "embody": payload = EmbodyDraft(self.application, f"experience:{e}")
        elif stage == "learn":
            frozen = self.config["policy"] == "frozen" and self.round >= 3
            key = f"candidate:{e}" if frozen else f"meaning:{self.scene}"
            old_memory = w.memory_head(BOB, key)
            memory = w.read_revision(BOB, self.memory)
            app = w.processing_record(BOB, self.application)
            first = w.processing_record(BOB, app.enactments[0])
            view, _ = w.select_input(BOB)
            obs = next(o for o in view.observations if o.ref == first.observation)
            unavailable = experienced_unavailability(BOB, self.item, first, obs)
            payload = learn(BOB, self.cue, self.contexts[self.scene], self.scene, self.previous,
                memory, unavailable, key, None if old_memory is None else old_memory.ref, w.now)
            basis = tuple(dict.fromkeys((memory.ref, obs.ref) + payload.links +
                (() if self.previous is None else (self.previous.ref,)) + (() if old_memory is None else (old_memory.ref,))))
        elif stage == "publish":
            frozen = self.config["policy"] == "frozen" and self.round >= 3
            # Frozen candidate gets a paid archive binding, not a live scene binding.
            key = f"candidate:{e}" if frozen else f"meaning:{self.scene}"
            cue = card("arcana:17").ref if frozen else self.cue
            context = ROOM if frozen else self.contexts[self.scene]
            payload, basis = self._bind(key, cue, context, self.proposed.ref)
        else: raise ValueError("stage has no paid command")
        if metabolic: return MetabolicCommand(f"paid:{self.paid_calls}", task, BOB, payload, chunk)
        return MemoryCommand(f"paid:{self.paid_calls}", task, BOB, payload, basis, chunk)

    def _begin(self, chunk):
        self.stage = "theory"
        self.trials = []
        for study in self.studies:
            key = f"{study.ref.key}:{self.episode}"
            self.world.execute(BeginTrial("begin:" + key, key, study.ref, True, self._command(chunk)))
            self.trials.append(Ref(Kind.DEMAND, "trial:" + key, 1))

    def _close(self):
        w = self.world
        trials = []
        for trial in self.trials:
            w.execute(EndTrial("end:" + trial.key, trial))
            r = w._trial_results[replace(trial, revision=2)]
            trials.append({"identity": r.identity.value, "path": r.path.value,
                           "discrepancy": r.discrepancy, "units": r.units})
        drain(w, f"assess:{self.episode}", 8)
        account = w.processing_record(BOB, self.account)
        app = w.processing_record(BOB, self.application)
        actions = [w.processing_record(BOB, r) for r in app.enactments]
        invalid = sum(a.request.operation == TRANSFER and a.outcome == WorkStatus.FAILED for a in actions)
        transferred = any(a.request.operation == TRANSFER and a.outcome == WorkStatus.COMPLETED for a in actions)
        appropriate = not invalid and (transferred if self.desired == BOB else not transferred)
        plans = [w.processing_job(BOB, f"m:{self.episode}:{s}").plan for s in ("theory", "apply", "embody")]
        frozen = self.config["policy"] == "frozen" and self.round >= 3
        self.rows.append({"episode": self.episode, "round": self.round, "scene": self.scene, "item": self.item.key,
            "actor_owned_at_demand": self.desired == BOB, "cue": self.cue.key,
            "meaning_before": describe(self.previous), "selected_meaning": describe(self.selected),
            "candidate_meaning": describe(self.proposed), "published": not frozen,
            "meaning_after": describe(self.previous if frozen else self.proposed),
            "selected_check": self.check, "empty_account": self.empty_account,
            "prediction": None if account.claim is None else account.claim.object.key,
            "guard": None if account.guard is None else encode(account.guard),
            "discrepancy": app.discrepancy, "appropriate": bool(appropriate), "invalid_transfers": invalid,
            "actions": [{"operation": a.request.operation.key, "outcome": a.outcome.value} for a in actions],
            "cost": self.spent - self.start_cost, "route_units": sum(sum(p.hop_units) for p in plans),
            "content_units": sum(p.content_units for p in plans), "paths": [list(p.path) for p in plans],
            "end_perspective": w.processing_state(BOB).perspective.value, "assessments": trials})
        if w.processing_state(BOB).perspective != Perspective.I: raise AssertionError("missing paid return to I")
        self.phases += 1
        if self.episode == 3:
            self.studies.append(declare(w, "retained", "experience:3", self.items[3],
                features=("capacity_rules",), strict=True))
        self.episode += 1
        self.stage = "done" if self.done else "start"

    def step(self, chunk=16):
        if type(chunk) is not int or chunk < 1: raise ValueError("positive work chunk required")
        self.history.append(["step", chunk])
        if self.done: return False
        if self.stage == "start": self._external_start(); return True
        if self.stage == "choose": self._choose(); return True
        if self.stage == "begin": self._begin(chunk); return True
        if self.stage == "close": self._close(); return True
        stage = self.stage
        command = self._command(chunk)
        before = owned_wallet(self.world)
        self.world.execute(command)
        self.paid_calls += 1
        after = owned_wallet(self.world)
        cost = before[0] - after[0]
        if cost != before[1] - after[1]: raise AssertionError("energy/time billing diverged")
        self.spent += cost
        self.costs[stage] += cost
        job = (self.world.memory_job(BOB, command.task_id) if isinstance(command, MemoryCommand)
               else self.world.processing_job(BOB, command.task_id))
        if job.outcome not in (WorkStatus.COMPLETED, WorkStatus.FAILED): return cost > 0
        if job.outcome == WorkStatus.FAILED and job.result is None: raise AssertionError("failed operation without usable result")
        if stage == "meaning":
            self.meaning_recall = job.result
            self.previous = self._meaning_from_recall(job.result)
            self.selected = self.previous
            self.stage = "selection" if self.config["policy"] == "shuffled" and self.round >= 3 else "choose"
        elif stage == "selection":
            self.selection_recall = job.result
            self.selected, self.stage = self._meaning_from_recall(job.result), "choose"
        elif stage == "decision":
            self.decision = self.world.memory_head(BOB, f"decision:{self.episode}").ref
            self.stage = "bridge"
        elif stage == "bridge": self.stage = "recall"
        elif stage == "recall": self.recall, self.stage = job.result, "begin"
        elif stage == "theory": self.account, self.stage = job.result, "apply"; self.phases += 1
        elif stage == "apply": self.application, self.stage = job.result, "embody"; self.phases += 1
        elif stage == "embody": self.memory, self.stage = job.result, "learn"
        elif stage == "learn":
            self.proposed = read_meaning(self.world.memory_head(BOB, command.payload.key), BOB)
            self.stage = "publish"
        elif stage == "publish":
            if not (self.config["policy"] == "frozen" and self.round >= 3): self.assignments[self.scene] = self.cue
            self.stage = "close"
        return True

    def run(self, chunk=16):
        for _ in range(40000):
            if self.done or not self.step(chunk): return self
        raise RuntimeError("bounded controller execution limit exceeded")

    def credit(self, energy, time, key="continuation-credit"):
        self.history.append(["credit", energy, time, key])
        self.world.execute(Credit(key, BOB, energy, time, "explicit continuation supply"))

    def result(self):
        if self.world.pending_assessments():
            self.history.append(["assess"])
            drain(self.world, f"final:{len(self.history)}", 8)
        reports = []
        for study in self.studies:
            r = self.world.report(study.ref)
            reports.append({"study": study.ref.key, "shell": r.shell, "closure": r.closure.value,
                "factual": r.results[0].status.value, "identity": r.results[1].status.value,
                "path": r.results[2].status.value, "retained_capacity": r.results[3].status.value})
        return {"config": self.config, "completed": self.episode, "done": self.done,
            "display_names": {f"arcana:{n}": (f"Cue {n - 18}" if self.config["labels"] == "anonymous" else card(f"arcana:{n}").symbol) for n in (19,20,21)},
            "pending_stage": self.stage, "completed_phases": self.phases, "phase": list(self.phase),
            "setup_cost": self.setup_cost, "paid_cost": self.spent, "cost_by_stage": dict(self.costs),
            "remaining_resources": list(owned_wallet(self.world)), "external_actor_credit": self.external_credit,
            "external_actor_fixture_cost": self.external_spent, "episodes": self.rows, "reports": reports}

    def checkpoint(self):
        state = {"episode": self.episode, "stage": self.stage, "phases": self.phases, "paid_calls": self.paid_calls,
            "spent": self.spent, "rows": self.rows, "assignments": {k:v.key for k,v in self.assignments.items()},
            "previous": describe(self.previous), "selected": describe(self.selected), "proposed": describe(self.proposed)}
        body = {"schema": "hle-holon-meaning-v1", "config": self.config,
                "history": self.history, "controller": state, "world": self.world.checkpoint()}
        return canonical({"body": body, "sha256": hashlib.sha256(canonical(body).encode()).hexdigest()})

    @classmethod
    def restore(cls, text):
        data = json.loads(text)
        if set(data) != {"body", "sha256"} or hashlib.sha256(canonical(data["body"]).encode()).hexdigest() != data["sha256"]:
            raise ValueError("invalid controller checksum")
        body = data["body"]
        if set(body) != {"schema", "config", "history", "controller", "world"} or body["schema"] != "hle-holon-meaning-v1":
            raise ValueError("invalid controller schema")
        out = cls(**body["config"])
        for entry in body["history"]:
            if entry[0] == "step" and len(entry) == 2: out.step(entry[1])
            elif entry[0] == "credit" and len(entry) == 4: out.credit(*entry[1:])
            elif entry == ["assess"]: out.result()
            else: raise ValueError("invalid continuation history")
        if out.checkpoint() != text: raise ValueError("state disagrees with verified execution")
        return out
