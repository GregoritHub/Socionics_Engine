"""R12 acceptance declarations. Missing execution always remains unassessed."""
from dataclasses import dataclass

from .contracts import Ref, Kind, EvidenceStatus, _kind, _text
from .development_contracts import VersionOne, refs, unique


@dataclass(frozen=True)
class IdentityContract(VersionOne):
    ref: Ref
    state_domain: str
    features: tuple[str, ...]
    discriminating_pairs: tuple[tuple[str, str], ...]
    scope: Ref

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.IDENTITY)
        _kind(self.scope, Kind.PROTOCOL); _text(self.state_domain); unique(self.features)
        if not self.features or not self.discriminating_pairs:
            raise ValueError("identity must declare features and relevant distinctions")
        for feature in self.features: _text(feature)
        if any(a == b or not a or not b for a, b in self.discriminating_pairs):
            raise ValueError("identity control must distinguish different alternatives")


@dataclass(frozen=True)
class ReturnProtocol(VersionOne):
    ref: Ref
    identity: Ref
    transformation: Ref
    return_policy: Ref
    applicability: tuple[str, ...]
    resource_protocol: Ref
    path_conditions: tuple[str, ...]
    sequences: tuple[tuple[str, ...], ...]
    equivalence_proof: Ref | None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.PROTOCOL); _kind(self.identity, Kind.IDENTITY)
        _kind(self.transformation, Kind.PROCEDURE); _kind(self.return_policy, Kind.PROCEDURE)
        _kind(self.resource_protocol, Kind.PROTOCOL)
        if not self.applicability or not self.path_conditions or not self.sequences or any(not s for s in self.sequences):
            raise ValueError("return domain, path and tested sequences must be declared")
        if self.equivalence_proof is not None: _kind(self.equivalence_proof, Kind.EVIDENCE)


@dataclass(frozen=True)
class AcceptanceEvidence(VersionOne):
    case_id: str
    protocol_sha256: str
    status: EvidenceStatus
    run_kind: str
    evidence_refs: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _text(self.case_id)
        if len(self.protocol_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.protocol_sha256):
            raise ValueError("protocol digest required")
        if self.run_kind not in ("runtime", "fixture", "not_run"):
            raise ValueError("execution kind must be explicit")
        refs(self.evidence_refs, Kind.EVIDENCE, Kind.ASSESSMENT)
        if self.status != EvidenceStatus.UNASSESSED and (not self.evidence_refs or self.run_kind == "not_run"):
            raise ValueError("a reported result requires execution evidence")


def acceptance_status(case_ids, results, protocol_sha256, required_run_kind="runtime"):
    """Combine evidence statuses, not measurements or detector labels.

    All supplied executions must be bound to the frozen protocol. Fixture
    passes cannot stand in for generated-runtime cases. Failures are retained.
    Independent replay/provenance validation remains a later runtime gate.
    """
    case_ids, results = tuple(case_ids), tuple(results)
    unique(case_ids)
    if not case_ids:
        raise ValueError("empty acceptance panel is not a pass")
    unique(tuple(r.case_id for r in results))
    if any(r.case_id not in case_ids or r.protocol_sha256 != protocol_sha256 for r in results):
        raise ValueError("unexpected case or changed assessment protocol")
    selected = {r.case_id: r for r in results if r.run_kind == required_run_kind}
    if any(r.status == EvidenceStatus.FAILED for r in selected.values()):
        return EvidenceStatus.FAILED
    if any(k not in selected or selected[k].status != EvidenceStatus.ESTABLISHED for k in case_ids):
        return EvidenceStatus.UNASSESSED
    return EvidenceStatus.ESTABLISHED
