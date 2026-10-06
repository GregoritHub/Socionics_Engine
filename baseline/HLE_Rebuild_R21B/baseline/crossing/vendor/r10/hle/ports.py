"""Structural interfaces, implemented in part by the R2/R3 world.

World.apply, participant views and TruthView implement the relevant boundaries.
The R2 Attempt envelope carries message/belief payloads. R3 RelationalWorld
implements MemoryPort and selective retrieval. Full assessment remains R5.
Python typing is not a sandbox.
"""
from typing import Protocol
from .contracts import (ActionRequest, AssessmentResult, AssessmentSpec, CueBinding,
                        MemoryRevision, Observation, ParticipantInput, Ref, WorldEvent)


class ParticipantPolicy(Protocol):
    def choose(self, view: ParticipantInput) -> ActionRequest | None: ...


class MemoryPort(Protocol):
    def read_revision(self, owner: Ref, ref: Ref) -> MemoryRevision: ...
    def resolve_binding(self, owner: Ref, binding: Ref) -> CueBinding: ...


class DeliveryPort(Protocol):
    def deliver(self, event: WorldEvent) -> tuple[Observation, ...]: ...


class WorldPort(Protocol):
    def apply(self, action: ActionRequest) -> WorldEvent: ...


class EvaluatorTruthPort(Protocol):
    """Must never be supplied to ParticipantPolicy or MemoryPort."""
    def event(self, ref: Ref) -> WorldEvent: ...


class AssessmentPort(Protocol):
    def evaluate(self, spec: AssessmentSpec, truth: EvaluatorTruthPort,
                 evidence: tuple[Ref, ...]) -> tuple[AssessmentResult, ...]: ...
