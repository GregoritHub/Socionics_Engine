"""Paid experimental content operators over unmodified R11 world transactions.

This adapter is a cooperative-policy API, not a Python security sandbox. It does
not add a Crux route or change a participant's perspective/TIM. Content aspect
is determined by the explicit finite contract, independently of current activity.
"""
from dataclasses import dataclass, replace
import hashlib
import json

from hle.contracts import (ActionRequest, Cause, ClaimStatus, Kind, MemoryRevision,
                          Moment, Observation, Proposition, Ref, ResourceAmount,
                          TimeScope, WorkRecord, WorkStatus, WorldEvent)
from hle.crux import Polarity
from hle.language import LanguageWorld
from hle.metabolism_records import ProcessingState, RoutePlan
from hle.processing import _route_geometry, route_active
from hle.socion_records import Notice, ReceiveCommand
from hle.world import amounts
from hle.world_records import (Attempt, Credit, ENERGY, Message, MessageDraft,
                              MemoryDraft, RETAIN, SEND, TIME, Tick, Wallet)
from .operators import ASPECT, TARGET, transform, validate

RULE = Ref(Kind.RULE, "experiment.content_contract.v1", 1)
WORK = Ref(Kind.PROCEDURE, "experiment.content_work.v1", 1)
WIRE = "experiment.content.v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def pack(body):
    # JSON roundtrip detaches all participant-owned mutable containers.
    payload = canonical(validate(body))
    return canonical({"body": body, "sha256": hashlib.sha256(payload.encode()).hexdigest()})


def unpack(text):
    envelope = json.loads(text)
    body = envelope["body"]
    if body["kind"] not in ASPECT or envelope["sha256"] != hashlib.sha256(canonical(body).encode()).hexdigest():
        raise ValueError("invalid content identity")
    return validate(body)


@dataclass(frozen=True)
class Process:
    command_id: str
    task_id: str
    actor: Ref
    operator: str
    sources: tuple[Ref, ...]
    work_limit: int = 64


@dataclass(frozen=True)
class Job:
    command: Process
    plan: RoutePlan
    candidate: str
    paid: int = 0
    result: Ref | None = None
    status: WorkStatus = WorkStatus.PENDING


@dataclass(frozen=True)
class ProcessTransaction:
    command: Process
    event: WorldEvent
    works: tuple
    observations: tuple
    state: ProcessingState
    job: Job
    messages: tuple = ()
    memories: tuple = ()
    task: None = None


class ContentWorld(LanguageWorld):
    def __init__(self, *args, **kwargs):
        self.content_jobs = {}
        super().__init__(*args, **kwargs)
        for ref in (RULE, WORK):
            self._records[ref] = ref

    def content(self, actor, ref):
        record = self._owned(actor, ref, (Observation, MemoryRevision))
        if type(record) is Observation and type(self._records.get(record.source)) is Message:
            if (actor, ref) not in self._completed_reception:
                raise ValueError("message must finish paid reception before use")
        if len(record.content) != 1 or record.content[0].relation != WIRE:
            raise ValueError("not a finite content record")
        body = unpack(record.content[0].object)
        if type(record) is MemoryRevision and body["kind"].endswith("_rule"):
            if (record.claim_status != ClaimStatus.ENDORSED
                    or self._memory_heads[actor][record.ref.key].ref != record.ref):
                raise ValueError("capacity is withdrawn or superseded")
        return body

    def execute(self, cmd):
        if type(cmd) is Process:
            return self._process(cmd)
        actor = cmd.action.actor if type(cmd) is Attempt else getattr(cmd, "actor", None)
        if actor in self._processing_states and type(cmd) not in (Credit, Tick):
            busy = self.processing_state(actor).busy
            if busy and busy.startswith("experiment:"):
                raise ValueError("finish experimental content work first")
        if type(cmd) is Attempt:
            for draft in (cmd.message, cmd.memory):
                if draft is None:
                    continue
                for prop in draft.content:
                    if prop.relation == WIRE:
                        if len(draft.content) != 1:
                            raise ValueError("one content envelope per record")
                        body = unpack(prop.object)
                        if cmd.memory is not None and body["kind"].endswith("_rule"):
                            expected = "experiment.infer_" + body["kind"].removesuffix("_rule")
                            valid = False
                            for basis in cmd.action.based_on:
                                record = self._owned(actor, basis, (Observation,))
                                source = self._records.get(record.source)
                                valid |= (type(source) is WorldEvent and source.action == expected
                                          and source.outcome == WorkStatus.COMPLETED and self.content(actor, basis) == body)
                            if not valid:
                                raise ValueError("retained rule needs its own completed inference")
        return super().execute(cmd)

    def _process(self, cmd):
        if cmd.operator not in TARGET or cmd.work_limit < 1 or not cmd.sources or len(set(cmd.sources)) != len(cmd.sources):
            raise ValueError("invalid content operation")
        prior = self._commands.get(cmd.command_id)
        if prior:
            if prior.command != cmd:
                raise ValueError("command ID reused")
            return prior.event
        state = self.processing_state(cmd.actor)
        old = self.content_jobs.get((cmd.actor, cmd.task_id))
        if old is None:
            if state.busy is not None or cmd.actor in self._receiving:
                raise ValueError("processing is busy")
        elif (old.status == WorkStatus.COMPLETED or state.busy != "experiment:" + cmd.task_id
              or (old.command.operator, old.command.sources) != (cmd.operator, cmd.sources)):
            raise ValueError("terminal or changed continuation")
        values = [self.content(cmd.actor, ref) for ref in cmd.sources]
        output, extent = transform(cmd.operator, values)
        candidate = pack(output)
        if old is None:
            profile = self._profiles[cmd.actor]
            tim = profile.tim if self.policy.typed_routing else "ile"
            target = TARGET[cmd.operator]
            face = Polarity.ACCUMULATION if target in ("ne", "ti") else Polarity.EXPENDITURE
            path, seats, support, offset, units, price = _route_geometry(
                tim, state.active, target, face, self.policy.positional_prices)
            plan = RoutePlan(profile.tim, tim, path, seats, support, offset, units, max(1, extent) * price)
            old = Job(cmd, plan, candidate)
        if old.candidate != candidate:
            raise ValueError("content changed during work")
        wallet = self._wallets[cmd.actor]
        spent = min(old.plan.required - old.paid, cmd.work_limit, wallet.energy, wallet.time)
        paid = old.paid + spent
        status = (WorkStatus.COMPLETED if paid == old.plan.required else
                  WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED)
        when = Moment(len(self._journal), 0)
        event_ref = Ref(Kind.EVENT, f"event:{when.tick}", 1)
        observations = ()
        if status == WorkStatus.COMPLETED:
            prop = Proposition(cmd.actor, WIRE, candidate, self.config.context, TimeScope(when, None))
            observations = (self._observation(cmd.actor, event_ref, when, (prop,),
                            "owned completed content operation", "finite contract only"),)
        job = replace(old, paid=paid, status=status, result=observations[0].ref if observations else None)
        state_after = replace(state, ref=replace(state.ref, revision=state.ref.revision + 1),
                              active=route_active(old.plan, paid),
                              busy=None if observations else "experiment:" + cmd.task_id)
        work = WorkRecord(Ref(Kind.WORK, f"work:{when.tick}:content", 1), cmd.actor, WORK,
                          amounts(wallet), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                          amounts(Wallet(cmd.actor, wallet.energy - spent, wallet.time - spent)),
                          old.plan.required - old.paid, spent, status, "declared finite content work")
        causes = tuple(dict.fromkeys(Cause(self._origins[r], RULE) for r in (state.ref,) + cmd.sources))
        event = WorldEvent(event_ref, when, (cmd.actor,), (), "experiment." + cmd.operator,
                           self.config.context, (), causes, (work.ref,), status, "paid content contract")
        self._commit(ProcessTransaction(cmd, event, (work,), observations, state_after, job))
        return event

    def _commit(self, tx):
        super()._commit(tx)
        if type(tx) is ProcessTransaction:
            state = tx.state
            self._records[state.ref] = state
            self._origins[state.ref] = tx.event.ref
            self._known[state.owner].add(state.ref)
            self._processing_states[state.owner] = state
            self._processing_changes[-1] = (tx.event.ref, (state.owner,))
            self.content_jobs[(tx.command.actor, tx.command.task_id)] = tx.job
        for observation in tx.observations:
            message = self._records.get(observation.source)
            if type(message) is Message and len(observation.content) == 1 and observation.content[0].relation == WIRE:
                body = unpack(observation.content[0].object)
                notice = Notice(observation.ref, observation.source, message.sender, "content",
                                observation.content[0], None, self._profiles[message.sender].tim, ASPECT[body["kind"]])
                self._notice_by_observation[(observation.observer, observation.ref)] = notice

    def process(self, actor, key, operator, sources, work_limit=64):
        for step in range(10000):
            event = self.execute(Process(f"{key}:{step}", key, actor, operator, tuple(sources), work_limit))
            job = self.content_jobs[(actor, key)]
            if event.outcome == WorkStatus.COMPLETED or not min(self._wallets[actor].energy, self._wallets[actor].time):
                return job.result
        raise RuntimeError("unfinished content job")

    def retain_content(self, actor, key, body, basis=()):
        """Fixture declarations may use empty basis; learned rules MUST cite output."""
        prop = Proposition(actor, WIRE, pack(body), self.config.context, TimeScope(self.now, None))
        command_key = key + ":retain:" + str(len(self._journal))
        cmd = Attempt(command_key, command_key, ActionRequest(actor, RETAIN, (), tuple(basis)),
                      memory=MemoryDraft(key, (prop,), ClaimStatus.ENDORSED, "retain explicit finite content"))
        event = self.execute(cmd)
        return self.memory_head(actor, key).ref if event.outcome == WorkStatus.COMPLETED else None

    def send_content(self, actor, ref, recipient, key):
        body = self.content(actor, ref)
        prop = Proposition(actor, WIRE, pack(body), self.config.context, TimeScope(self.now, None))
        event = self.execute(Attempt(key, key, ActionRequest(actor, SEND, (recipient,), (ref,)), MessageDraft((prop,))))
        if event.outcome != WorkStatus.COMPLETED:
            return None
        delivered = [o for o in self._journal[-1].observations if o.observer == recipient]
        return delivered[0].ref if delivered else None

    def receive_content(self, actor, observation, key):
        for step in range(10000):
            self.execute(ReceiveCommand(f"{key}:{step}", key, actor, observation))
            if (actor, observation) in self._completed_reception:
                return observation
            if not min(self._wallets[actor].energy, self._wallets[actor].time):
                return None
        raise RuntimeError("unfinished reception")

    def checkpoint(self):
        raise NotImplementedError("experimental content commands need a versioned codec; rerun this finite study")

    @classmethod
    def restore(cls, text):
        raise NotImplementedError("experimental content commands do not support checkpoint restore")
