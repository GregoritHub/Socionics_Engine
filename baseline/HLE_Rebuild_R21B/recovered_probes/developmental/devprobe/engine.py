"""Experimental developmental controller. The bundled R11 runtime is unchanged.

The controller supplies demands and operation ordering, never owners to the
participant. R4 derives accounts, acts, learns, and embodies from permitted data.
R5 is an evaluator only. No capability object is created by this module.
"""
from dataclasses import replace
import hashlib
import json
import random

from hle.assessment_demo import declare, drain
from hle.assessment_records import BeginTrial, EndTrial
from hle.cards import card
from hle.codec import canonical
from hle.contracts import ActionRequest, Kind, Moment, Ref, TimeScope, WorkStatus
from hle.crux import Perspective
from hle.demo import ALICE, BOB, ROOM
from hle.memory import observed_revision
from hle.memory_records import BindDraft, MemoryCommand, RecallQuery
from hle.metabolism_records import ApplyDraft, EmbodyDraft, MetabolicCommand, ProcessingPolicy, Profile, TheorizeDraft
from hle.organization import OrganizationWorld
from hle.socion_records import AgentPolicy
from hle.world_records import Attempt, Credit, Entity, INSPECT, Ownership, Tick, TRANSFER, Wallet, WorldConfig

POLICIES = ("coupled", "episode_only", "feedback_off", "once_per_outer", "generic_coupled")
ITEM_ORDER = (0, 1, 0, 2, 1, 3, 2, 3, 4, 5, 4, 6)
VOLATILE = (False, False, True, False, True, True, True, False, False, True, True, False)
SCOPE = TimeScope(Moment(0, 0), None)


def address(ref):
    return None if ref is None else f"{ref.kind.value}:{ref.key}@{ref.revision}"


def owned_wallet(w):
    view, _ = w.select_input(BOB)
    # Resource accounting is participant-visible; no ownership facts are read.
    resources = {r.unit.key: r.amount for r in view.available}
    return resources["r2.energy_quantum"], resources["r2.time_quantum"]


class Session:
    def __init__(self, tim="iee", seed=17, regime="volatile", budget=2400,
                 policy="coupled", neutral=False, time_budget=None):
        if policy not in POLICIES or regime not in ("volatile", "always_executable"):
            raise ValueError("unknown controller policy or fixture regime")
        self.config = dict(tim=tim, seed=seed, regime=regime, budget=budget,
            policy=policy, neutral=neutral, time_budget=time_budget)
        self.history = []
        self.episode, self.stage, self.phases, self.paid_calls = 0, "start", 0, 0
        self.spent, self.external_credit, self.external_spent = 0, 0, 0
        self.rows, self.trials, self.studies = [], [], []
        self.recall = self.account = self.application = self.memory = None
        self.start_cost = 0
        self.item = None
        self.desired = None  # Evaluator's fixture condition; never used in an R4 payload.
        self.seen = set()
        self.heldout = False
        items = [Ref(Kind.ENTITY, f"object:{i}", 1) for i in range(7)]
        random.Random(seed).shuffle(items)
        self.items = tuple(items)
        # Seven writes (2 each) and fourteen bindings (2 each): 42 setup units.
        cfg = WorldConfig(ROOM, tuple(Entity(a, a.key, "actor") for a in (ALICE, BOB)) +
            tuple(Entity(i, i.key, "object") for i in self.items), (ALICE, BOB),
            tuple(Ownership(i, BOB) for i in self.items),
            (Wallet(ALICE, 100000, 100000), Wallet(BOB, budget + 42, (budget if time_budget is None else time_budget) + 42)),
            (), ((ALICE, BOB), (BOB, ALICE)))
        self.world = OrganizationWorld(cfg, (Profile(ALICE, "lse"), Profile(BOB, tim)),
            ProcessingPolicy(not neutral, not neutral), (AgentPolicy(ALICE), AgentPolicy(BOB)))
        view, _ = self.world.select_input(BOB)
        for n, item in enumerate(self.items):
            obs = next(o for o in view.observations if any(p.subject == item and p.relation == "owned_by" for p in o.content))
            draft, basis = observed_revision(view, obs.ref, item, "owned_by", item.key)
            key = f"setup:write:{n}"
            self.world.execute(MemoryCommand(key, key, BOB, draft, basis))
            memory = self.world.memory_head(BOB, item.key)
            for label, rank in (("original", n + 1), ("current", n + 10)):
                key = f"setup:bind:{label}:{n}"
                self.world.execute(MemoryCommand(key, key, BOB, BindDraft(f"{label}:{n}",
                    card(f"arcana:{rank}").ref, ROOM, memory.ref, SCOPE), (memory.ref,)))
        assert owned_wallet(self.world) == (budget, budget if time_budget is None else time_budget)
        self.studies.append(declare(self.world, "development", self.items[0].key, self.items[0],
            features=("claim_links", "perspective"), strict=True))

    @property
    def done(self): return self.episode == len(ITEM_ORDER)

    @property
    def phase(self): return self.phases % 9, self.phases % 3

    def _external_start(self):
        w, e = self.world, self.episode
        if e == 6:
            for n in range(10): w.execute(Tick(f"quiet:{n}"))
        index = ITEM_ORDER[e]
        self.item = self.items[index]
        self.heldout = self.item not in self.seen and e > 0
        self.desired = BOB if self.config["regime"] == "always_executable" or VOLATILE[e] else ALICE
        # This is an explicit external fixture intervention, not participant selection.
        current = w.truth.current_fact(self.item, "owned_by", ROOM).object
        if current != self.desired:
            if current == BOB:
                w.execute(Credit(f"fixture-credit:{e}", BOB, 2, 2, "exact external fixture transfer cost"))
                self.external_credit += 2
            key = f"fixture-transfer:{e}"
            event = w.execute(Attempt(key, key, ActionRequest(current, TRANSFER, (self.item, self.desired), ())))
            if event.outcome != WorkStatus.COMPLETED: raise AssertionError("external transfer failed")
            if current == BOB: self.external_spent += 2
        self.start_cost = self.spent
        self.recall = self.account = self.application = self.memory = None
        self.trials = []
        self.stage = "recall"

    def _command(self, chunk):
        w, e, stage = self.world, self.episode, self.stage
        task = f"d:{e}:{stage}"
        if stage == "recall":
            old = w.memory_job(BOB, task)
            if old is not None:
                payload = old.command.payload
            else:
                n = ITEM_ORDER[e]
                rank = n + 1 if self.config["policy"] == "feedback_off" else n + 10
                cues = (card(f"arcana:{rank}").ref,)
                if self.config["policy"] in ("coupled", "generic_coupled", "once_per_outer"):
                    cues += (card("arcana:21").ref,)
                payload = RecallQuery(cues, ROOM, w.now, relation="owned_by", visit_limit=4096)
            return MemoryCommand(f"paid:{self.paid_calls}", task, BOB, payload, (), chunk)
        if stage in ("rebind", "publish"):
            key = f"current:{ITEM_ORDER[e]}" if stage == "rebind" else "shared"
            rank = ITEM_ORDER[e] + 10 if stage == "rebind" else 21
            oldjob = w.memory_job(BOB, task)
            if oldjob:
                payload, basis = oldjob.command.payload, oldjob.command.based_on
            else:
                old = w.binding_head(BOB, key)
                basis = (self.memory,) + (() if old is None else (old.ref,))
                payload = BindDraft(key, card(f"arcana:{rank}").ref, ROOM, self.memory, SCOPE,
                    None if old is None else old.ref)
            return MemoryCommand(f"paid:{self.paid_calls}", task, BOB, payload, basis, chunk)
        old = w.processing_job(BOB, task)
        if old:
            payload = old.command.payload
        elif stage == "theory":
            payload = TheorizeDraft(self.recall, self.item, ALICE)
        elif stage == "apply":
            payload = ApplyDraft(self.account)
        elif stage == "embody":
            prior = w.memory_head(BOB, self.item.key)
            payload = EmbodyDraft(self.application, self.item.key, prior.ref)
        else:
            raise ValueError("stage has no paid command")
        return MetabolicCommand(f"paid:{self.paid_calls}", task, BOB, payload, chunk)

    def _begin(self, chunk):
        self.stage = "theory"
        offer = self._command(chunk)
        for study in self.studies:
            key = f"{study.ref.key}:{self.episode}"
            self.world.execute(BeginTrial("begin:" + key, key, study.ref, True, offer))
            self.trials.append(Ref(Kind.DEMAND, "trial:" + key, 1))

    def _close(self):
        w = self.world
        reports = []
        for trial in self.trials:
            w.execute(EndTrial("end:" + trial.key, trial))
            r = w._trial_results[replace(trial, revision=2)]
            reports.append({"study": r.study.key, "identity": r.identity.value, "path": r.path.value,
                "units": r.units, "discrepancy": r.discrepancy, "blocked": r.blocked,
                "reconstruction": r.reconstruction, "capacity_items": [i.key for i in r.successful_capacity_items],
                "visible_features": list(r.visibility), "net_features": list(r.net),
                "cancellation": list(r.cancellation), "recurrence_pairs": [list(x) for x in r.recurrence]})
        drain(w, f"assess:{self.episode}", 8)
        account = w.processing_record(BOB, self.account)
        app = w.processing_record(BOB, self.application)
        memory = w.read_revision(BOB, self.memory)
        actions = [w.processing_record(BOB, ref) for ref in app.enactments]
        invalid = sum(a.request.operation == TRANSFER and a.outcome == WorkStatus.FAILED for a in actions)
        transferred = any(a.request.operation == TRANSFER and a.outcome == WorkStatus.COMPLETED for a in actions)
        appropriate = invalid == 0 and (transferred if self.desired == BOB else not transferred)
        plans = [w.processing_job(BOB, f"d:{self.episode}:{s}").plan for s in ("theory", "apply", "embody")]
        self.rows.append({"episode": self.episode, "item": self.item.key, "heldout": self.heldout,
            "actor_owned_at_demand": self.desired == BOB, "prediction": None if account.claim is None else account.claim.object.key,
            "guard": address(account.guard), "memory": address(memory.ref), "capabilities": [address(c) for c in memory.capabilities],
            "discrepancy": app.discrepancy, "appropriate": appropriate, "invalid_transfers": invalid,
            "actions": [{"operation": a.request.operation.key, "outcome": a.outcome.value} for a in actions],
            "cost": self.spent - self.start_cost, "route_units": sum(sum(p.hop_units) for p in plans),
            "content_units": sum(p.content_units for p in plans), "action_units": sum(1 if a.request.operation == INSPECT else 2 for a in actions),
            "paths": [list(p.path) for p in plans], "end_active": w.processing_state(BOB).active,
            "end_perspective": w.processing_state(BOB).perspective.value, "assessments": reports})
        self.phases += 1
        if w.processing_state(BOB).perspective != Perspective.I:
            raise AssertionError("completed developmental return did not reach I")
        if self.episode == 0:
            self.studies.append(declare(w, "retained", self.items[0].key, self.items[0],
                features=("capacity_rules",), strict=True))
        self.seen.add(self.item)
        self.episode += 1
        self.stage = "done" if self.done else "start"

    def step(self, chunk=16):
        if type(chunk) is not int or chunk < 1: raise ValueError("positive work chunk required")
        self.history.append(["step", chunk])
        if self.done: return False
        if self.stage == "start": self._external_start(); return True
        if self.stage == "begin": self._begin(chunk); return True
        if self.stage == "close": self._close(); return True
        command = self._command(chunk)
        before = owned_wallet(self.world)
        self.world.execute(command)
        self.paid_calls += 1
        after = owned_wallet(self.world)
        cost = before[0] - after[0]
        if before[1] - after[1] != cost: raise AssertionError("energy/time billing diverged")
        self.spent += cost
        job = self.world.memory_job(BOB, command.task_id) if isinstance(command, MemoryCommand) else self.world.processing_job(BOB, command.task_id)
        if job.outcome not in (WorkStatus.COMPLETED, WorkStatus.FAILED):
            return cost > 0
        if job.outcome == WorkStatus.FAILED and job.result is None:
            raise AssertionError("operation failed without usable outcome")
        if self.stage == "recall": self.recall, self.stage = job.result, "begin"
        elif self.stage == "theory": self.account, self.stage = job.result, "apply"; self.phases += 1
        elif self.stage == "apply": self.application, self.stage = job.result, "embody"; self.phases += 1
        elif self.stage == "embody": self.memory, self.stage = job.result, "rebind"
        elif self.stage == "rebind":
            self.stage = "close" if self.config["policy"] == "once_per_outer" and (self.episode + 1) % 3 else "publish"
        elif self.stage == "publish": self.stage = "close"
        return True

    def run(self, chunk=16):
        for _ in range(20000):
            if self.done or not self.step(chunk): return self
        raise RuntimeError("controller exceeded bounded execution limit")

    def credit(self, energy, time, key="test-credit"):
        self.history.append(["credit", energy, time, key])
        self.world.execute(Credit(key, BOB, energy, time, "explicit experimental continuation supply"))

    def assess(self):
        self.history.append(["assess"])
        drain(self.world, f"final-assess:{len(self.history)}", 8)

    def result(self):
        if self.world.pending_assessments(): self.assess()
        reports = []
        for study in self.studies:
            r = self.world.report(study.ref)
            reports.append({"study": study.ref.key, "shell": r.shell,
                "factual": r.results[0].status.value, "identity": r.results[1].status.value,
                "path": r.results[2].status.value, "retained_capacity": r.results[3].status.value,
                "closure": r.closure.value, "capacity_items": [i.key for i in self.world._aggregates[study.ref].capacity_items]})
        return {"config": self.config, "completed": self.episode, "done": self.done,
            "pending_stage": self.stage, "phase": list(self.phase), "completed_phases": self.phases,
            "recall_processing_retention_cost": self.spent, "remaining_resources": list(owned_wallet(self.world)),
            "external_actor_credit": self.external_credit, "external_actor_fixture_cost": self.external_spent,
            "episodes": self.rows, "reports": reports}

    def checkpoint(self):
        state = {"episode": self.episode, "stage": self.stage, "phases": self.phases,
            "paid_calls": self.paid_calls, "spent": self.spent, "rows": self.rows}
        body = {"schema": "hle-developmental-recurrence-v1", "config": self.config,
            "history": self.history, "controller": state, "world": self.world.checkpoint()}
        return canonical({"body": body, "sha256": hashlib.sha256(canonical(body).encode()).hexdigest()})

    @classmethod
    def restore(cls, text):
        data = json.loads(text)
        if set(data) != {"body", "sha256"} or hashlib.sha256(canonical(data["body"]).encode()).hexdigest() != data["sha256"]:
            raise ValueError("invalid controller checkpoint checksum")
        body = data["body"]
        if set(body) != {"schema", "config", "history", "controller", "world"} or body["schema"] != "hle-developmental-recurrence-v1":
            raise ValueError("invalid controller checkpoint schema")
        out = cls(**body["config"])
        for entry in body["history"]:
            if entry[0] == "step" and len(entry) == 2: out.step(entry[1])
            elif entry[0] == "credit" and len(entry) == 4: out.credit(*entry[1:])
            elif entry == ["assess"]: out.assess()
            else: raise ValueError("invalid controller continuation history")
        if out.checkpoint() != text:
            raise ValueError("controller or engine state disagrees with verified execution")
        return out
