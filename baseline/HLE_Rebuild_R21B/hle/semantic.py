"""Shared paid Model A processing for actual R8/R9 content operations.

The mapping and personal I -> I boundary are R11 hypotheses. No Truth input.
"""
from dataclasses import replace
from types import MappingProxyType
from .contracts import (Cause, Kind, Moment, Ref, ResourceAmount, WorkRecord,
                        WorkStatus, WorldEvent)
from .crux import FormalMovement, Perspective, Polarity, Route
from .metabolism_records import MetabolicCommand, ProcessingState, RoutePlan
from .processing import _route_geometry, route_active
from .semantic_records import CancelSemantic, SemanticRoute
from .world import amounts
from .world_records import ENERGY, TIME, Wallet

A, E = Polarity.ACCUMULATION, Polarity.EXPENDITURE
TARGETS = MappingProxyType({
    'Learn': ('ti', A), 'Produce': ('fe', E), 'Interpret': ('ti', A),
    'Intend': ('fi', E), 'Formulate': ('ne', A), 'ReviewTerms': ('ti', A),
    'Ratify': ('fi', E), 'Join': ('fi', E), 'Attend': ('ni', A),
    'Dispute': ('ti', A), 'Leave': ('fi', E), 'Perform': ('te', E),
})
DONE = (WorkStatus.COMPLETED, WorkStatus.FAILED)


def semantic_route(profile, state, family, payload, extent, policy, enabled=True):
    target, face = TARGETS[type(payload).__name__]
    formal = FormalMovement(Route(Perspective.I, Perspective.I), face)
    plan = None
    if enabled:
        tim = profile.tim if policy.typed_routing else 'ile'
        path, seats, support, offset, units, price = _route_geometry(
            tim, state.active, target, face, policy.positional_prices)
        plan = RoutePlan(profile.tim, tim, path, seats, support, offset,
                         units, max(1, extent) * price)
    return SemanticRoute(family, type(payload).__name__, state.ref, formal, extent, plan)


class SemanticRouting:
    def _semantic_guard(self, cmd, family, old):
        state = self.processing_state(cmd.actor)
        owner = self._semantic_owners.get(cmd.actor)
        if owner is not None and owner != (family, cmd.task_id):
            raise ValueError('another semantic family/task owns processing')
        if (cmd.actor in self._receiving or state.perspective != Perspective.I
                or state.busy is not None and owner is None):
            raise ValueError('semantic work requires available personal processing')
        if old is not None and (old.outcome in DONE or owner != (family, cmd.task_id)):
            raise ValueError('terminal or unowned semantic continuation')
        return state

    def _semantic_execute(self, cmd, family, prepare):
        from .language_records import LanguageJob, LanguageTransaction, LANGUAGE, LANGUAGE_WORK
        from .organization_records import OrganizationJob, OrganizationTransaction, ORGANIZATION, ORGANIZE
        Job, Transaction, rule, operation, jobs = (
            (LanguageJob, LanguageTransaction, LANGUAGE, LANGUAGE_WORK, self._language_jobs)
            if family == 'language' else
            (OrganizationJob, OrganizationTransaction, ORGANIZATION, ORGANIZE, self._organization_jobs))
        prior = self._commands.get(cmd.command_id)
        if prior is not None:
            if prior.command != cmd: raise ValueError('command ID reused')
            return prior.event
        old = jobs.get((cmd.actor, cmd.task_id))
        state = self._semantic_guard(cmd, family, old)
        cancelling = type(cmd) is CancelSemantic
        if cancelling and old is None: raise ValueError('no unfinished semantic job to cancel')
        if not cancelling and old is not None and old.command.payload != cmd.payload:
            raise ValueError('changed semantic continuation')
        when = Moment(len(self._journal), 0)
        invalid = None
        if cancelling:
            extent, result, basis = old.route.extent, old.candidate, ()
            invalid = 'cancelled: ' + cmd.reason
        else:
            try:
                extent, result, basis = prepare()
            except ValueError as error:
                if old is None: raise
                extent, result, basis = old.route.extent, old.candidate, ()
                invalid = 'evidence no longer admissible: ' + str(error)
        if old is None:
            route = semantic_route(self._profiles[cmd.actor], state, family,
                cmd.payload, extent, self.policy, self.semantic_policy.enabled)
            required = extent if route.plan is None else route.plan.required
            old = Job(cmd, required, result, route=route)
        elif not cancelling and (extent != old.route.extent or result != old.candidate):
            invalid = 'local evidence, meaning or terms changed during processing'
        wallet = self._wallets[cmd.actor]
        spent = 0 if invalid else min(old.required-old.paid, cmd.work_limit, wallet.energy, wallet.time)
        paid = old.paid + spent
        status = (WorkStatus.FAILED if invalid else WorkStatus.COMPLETED if paid == old.required
                  else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED)
        extra = (result,) if status == WorkStatus.COMPLETED else ()
        job = replace(old, paid=paid, outcome=status, result=result.ref if extra else None)
        active = state.active if old.route.plan is None else route_active(old.route.plan, paid)
        newstate = ProcessingState(replace(state.ref, revision=state.ref.revision+1),
            cmd.actor, active, state.perspective,
            None if status in DONE else 'semantic:' + family + ':' + cmd.task_id)
        reason = invalid or 'paid Model A route and local semantic content'
        work = WorkRecord(Ref(Kind.WORK, f'work:{when.tick}:0', 1), cmd.actor, operation,
            amounts(wallet), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
            amounts(Wallet(cmd.actor, wallet.energy-spent, wallet.time-spent)),
            old.required-old.paid, spent, status, reason)
        # Include the prior processing state as an explicit causal input.
        origins = [self._origins[state.ref]] + [x if x.kind == Kind.EVENT else self._origins[x] for x in basis]
        causes = tuple(dict.fromkeys(Cause(x, rule) for x in origins))
        event = WorldEvent(Ref(Kind.EVENT, f'event:{when.tick}', 1), when, (cmd.actor,), (),
            'r11.cancel' if cancelling else 'r8.language' if family == 'language' else 'r9.'+type(cmd.payload).__name__,
            self.config.context, (), causes, (work.ref,), status, reason)
        self._commit(Transaction(cmd, event, (work,), extra=extra, job=job, state=newstate))
        return event

    def _commit_semantic_state(self, tx, family):
        state, job = tx.state, tx.job
        if state.ref in self._records: raise ValueError('duplicate processing state')
        self._records[state.ref] = state
        self._origins[state.ref] = tx.event.ref
        self._known[state.owner].add(state.ref)
        self._processing_states[state.owner] = state
        self._processing_changes[-1] = (tx.event.ref, (state.owner,))
        if job.outcome in DONE:
            self._semantic_owners.pop(state.owner, None)
        else:
            self._semantic_owners[state.owner] = (family, job.command.task_id)
