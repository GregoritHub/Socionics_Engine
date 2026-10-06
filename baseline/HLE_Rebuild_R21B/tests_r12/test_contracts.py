from dataclasses import replace, FrozenInstanceError
import unittest

from hle.contracts import Ref, Kind as K, Moment, TimeScope, WorkStatus as W, EvidenceStatus as E
from hle.crux import FormalMovement, Route, Perspective as P, Polarity
from hle.development_contracts import *
from hle.development_protocol import IdentityContract, ReturnProtocol, AcceptanceEvidence, acceptance_status


def ref(kind, key, revision=1):
    return Ref(kind, key, revision)


A = ref(K.ENTITY, "learner")
B = ref(K.ENTITY, "partner")
CTX = ref(K.CONTEXT, "room")
MAT = ref(K.MEMORY, "material")
OBS = ref(K.OBSERVATION, "receipt")
EV = ref(K.EVENT, "experience")
WORK = ref(K.WORK, "debit")
PROC = ref(K.PROCEDURE, "check-and-act")
PROTOCOL = ref(K.PROTOCOL, "temporal.v1")
MOVE = FormalMovement(Route(P.ITS, P.IT), Polarity.EXPENDITURE)
RESOURCE = ResourceEnvelope(100, 100, None)


def demand(**changes):
    value = DevelopmentalDemand(ref(K.DEMAND, "new"), Origin.CONSEQUENCE, (EV,), (OBS,),
        "temporal", PROTOCOL, ("honor valid obligation",), (MOVE,), CTX, (A, B), (MAT,),
        ("respect consent",), TimeScope(Moment(10, 0), Moment(20, 0)), RESOURCE,
        (Requirement("temporal_dependencies", 1), Requirement("missing_testimony", 0)),
        ref(K.DEMAND, "old"))
    return replace(value, **changes)


def opportunity(**changes):
    value = Opportunity(ref(K.EVIDENCE, "opportunity"), A, demand().ref, Moment(12, 0), True,
        (OBS,), MAT, PROC, 5, RESOURCE, (), 3, Moment(10, 0), (EV,))
    return replace(value, **changes)


def work(**changes):
    value = DevelopmentalWork(ref(K.WORK, "job"), A, demand().ref, PROC, MOVE, (OBS,),
        (EV,), (WORK,), 10, 4, W.PARTIAL, ())
    return replace(value, **changes)


def material(**changes):
    value = MaterialTreatment(ref(K.MEMORY, "treatment"), MAT, A, (EV,), A,
        Treatment.EXTERNALIZE, B, None, (OBS,), (WORK,), ())
    return replace(value, **changes)


class DemandTests(unittest.TestCase):
    def test_demand_requires_causal_discovery_not_just_label(self):
        for changes in ({"origin_events": ()}, {"discovered_from": ()}, {"required_outcomes": ()},
                        {"requirements": ()}, {"movements": ()}, {"material_lineage": ()}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): demand(**changes)

    def test_equal_and_shifted_duration(self):
        prior = demand(ref=ref(K.DEMAND, "prior"))
        later = demand(duration=TimeScope(Moment(30, 0), Moment(40, 0)))
        self.assertEqual(compare_demands(later, prior).relation, Comparison.EQUAL)

    def test_greater_requirement_has_exact_witness(self):
        harder = demand(requirements=(Requirement("temporal_dependencies", 3), Requirement("missing_testimony", 0)))
        result = compare_demands(harder, demand())
        self.assertEqual(result.relation, Comparison.GREATER)
        self.assertEqual(result.changes, (("temporal_dependencies", 1, 3),))
        self.assertEqual(compare_demands(demand(), harder).relation, Comparison.LESSER)

    def test_mixed_requirements_are_incomparable(self):
        other = demand(requirements=(Requirement("temporal_dependencies", 0), Requirement("missing_testimony", 1)))
        self.assertEqual(compare_demands(other, demand()).relation, Comparison.INCOMPARABLE)

    def test_changed_scope_not_automatically_harder(self):
        for changes in ({"resources": ResourceEnvelope(0, 0, None)}, {"context": ref(K.CONTEXT, "elsewhere")},
                        {"participants": (A,)}, {"material_lineage": (ref(K.MEMORY, "unrelated"),)},
                        {"duration": TimeScope(Moment(10, 0), Moment(15, 0))},
                        {"required_outcomes": ("different outcome",)}, {"comparison_protocol": ref(K.PROTOCOL, "v2")}):
            with self.subTest(changes=changes):
                self.assertEqual(compare_demands(demand(**changes), demand()).relation, Comparison.INCOMPARABLE)

    def test_exact_types_version_and_immutable_values(self):
        for changes in ({"schema_version": 2}, {"requirements": [Requirement("x", 1)]}):
            with self.assertRaises(ValueError): demand(**changes)
        with self.assertRaises(ValueError): Requirement("x", True)
        with self.assertRaises(FrozenInstanceError): demand().family = "other"


class OpportunityTests(unittest.TestCase):
    def test_delivery_interpretation_affordability_are_distinct(self):
        self.assertTrue(opportunity().eligible)
        for changes in ({"demand_active": False}, {"observation_refs": ()}, {"interpretation": None},
                        {"available_operator": None}, {"resources": ResourceEnvelope(4, 100, None)},
                        {"resources": ResourceEnvelope(100, 4, None)}, {"blocking_constraints": ("valid refusal",)}):
            with self.subTest(changes=changes): self.assertFalse(opportunity(**changes).eligible)

    def test_nonconsecutive_engagements_are_not_global_tick_streaks(self):
        e = (ref(K.EVENT, "event:10"), ref(K.EVENT, "event:20"), ref(K.EVENT, "event:50"))
        o = opportunity(at=Moment(50, 0), eligible_engagements=e)
        self.assertEqual(len(o.eligible_engagements), 3)
        self.assertTrue(o.eligible)
        with self.assertRaises(ValueError): opportunity(eligible_engagements=(EV, EV, EV))

    def test_residence_and_intensity_are_separate(self):
        value = ResidualObservations((EV,), Moment(1, 0), Moment(50, 0), (EV,), (WORK,))
        self.assertIsNone(value.intensity_measurement)
        with self.assertRaises(ValueError): replace(value, intensity_measurement=ref(K.EVIDENCE, "invented-score"))
        with self.assertRaises(ValueError): replace(value, queue_entered=Moment(51, 0))


class MaterialAndWorkTests(unittest.TestCase):
    def test_partial_work_cannot_publish_or_be_free_completion(self):
        for changes in ({"outputs": (MAT,)}, {"status": W.COMPLETED}, {"paid_units": 11},
                        {"work_refs": ()}, {"event_refs": ()}, {"status": W.PENDING}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): work(**changes)
        self.assertEqual(work(paid_units=10, status=W.COMPLETED, outputs=(MAT,)).paid_units, 10)

    def test_carrier_requires_owned_selection_evidence(self):
        for changes in ({"carrier": None}, {"carrier": A}, {"selection_evidence": ()}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): material(**changes)

    def test_reownership_preserves_origin_history(self):
        first = material()
        current = replace(first, ref=replace(first.ref, revision=2), previous_revision=first.ref,
                          treatment=Treatment.REOWN, carrier=None)
        validate_material_transition(first, current)
        for changes in ({"origin_actor": B}, {"lineage": ref(K.MEMORY, "new-origin")},
                        {"source_events": (ref(K.EVENT, "replacement"),)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_material_transition(first, replace(current, **changes))

    def test_capacity_is_a_bound_revision_with_acquisition_provenance(self):
        capacity = RetainedCapacity(ref(K.MEMORY, "capacity"), A, "ne", PROC, ref(K.BINDING, "cue"),
            CTX, (MAT,), (WORK,), (EV,), (MAT,), CapacityStatus.CURRENT, None)
        for changes in ({"acquisition_work": ()}, {"binding": OBS}, {"content_aspect": "mystery"},
                        {"supersedes": ref(K.MEMORY, "someone-else")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): replace(capacity, **changes)
        self.assertEqual(replace(capacity, status=CapacityStatus.WITHDRAWN).status, CapacityStatus.WITHDRAWN)


class AntiAwardTests(unittest.TestCase):
    def test_shell_label_alone_is_not_evidence(self):
        episode = ShellEpisode(ref(K.ASSESSMENT, "shell"), A, (MAT,), (demand().ref,), (),
            None, (), (), PROTOCOL, E.UNASSESSED, (), None)
        with self.assertRaises(ValueError): replace(episode, status=E.ESTABLISHED, signs=(ShellSign.FORECLOSURE,))

    def test_wrapper_and_censored_search_cannot_establish_closure(self):
        ev = ref(K.EVIDENCE, "observed-capacity")
        value = ClosureEvidence(ref(K.ASSESSMENT, "closure"), ref(K.PROCEDURE, "larger"), (PROC,),
            demand().ref, PROTOCOL, False, True, (), (), (), (), PROTOCOL, (), E.UNASSESSED)
        with self.assertRaises(ValueError): replace(value, status=E.ESTABLISHED)
        with self.assertRaises(ValueError): replace(value, status=E.ESTABLISHED, repertoire_exhausted=True,
            alternatives_evidence=(ev,), retained_lower_evidence=(ev,), new_capacity_evidence=(ev,), coherence_evidence=(ev,))
        with self.assertRaises(ValueError): replace(value, organization=PROC)

    def test_phase_and_scalar_do_not_award_development(self):
        state = DevelopmentalState(A, Moment(12, 0), StructuralFingerprint.for_tim("iee"), PROC,
            MOVE, (MAT,), (), Phase.UNASSESSED, (), ResidualObservations((), None, Moment(12, 0), (), ()),
            (demand().ref,), (), RESOURCE, (MAT,), (), (EV,))
        with self.assertRaises(ValueError): replace(state, phase=Phase.REOWNERSHIP)
        self.assertFalse(hasattr(state, "altitude"))

    def test_identity_must_discriminate_and_reference_its_scope(self):
        value = IdentityContract(ref(K.IDENTITY, "capacity"), "owned retained capacities", ("native", "complement"),
            (("helper_only", "owned_return"),), PROTOCOL)
        for changes in ({"features": ()}, {"discriminating_pairs": (("same", "same"),)}, {"scope": MAT}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): replace(value, **changes)

    def test_return_protocol_does_not_infer_general_closure(self):
        r = ReturnProtocol(PROTOCOL, ref(K.IDENTITY, "capacity"), PROC, PROC,
            ("eligible renewed demand",), PROTOCOL, ("no maintained target distortion",), (("renew",),), None)
        self.assertIsNone(r.equivalence_proof)
        with self.assertRaises(ValueError): replace(r, sequences=())

    def test_empty_and_fixture_evidence_cannot_complete_runtime_gate(self):
        digest = "0" * 64
        item = AcceptanceEvidence("case", digest, E.ESTABLISHED, "fixture", (ref(K.EVIDENCE, "result"),))
        self.assertEqual(acceptance_status(("case",), (), digest), E.UNASSESSED)
        self.assertEqual(acceptance_status(("case",), (item,), digest), E.UNASSESSED)
        self.assertEqual(acceptance_status(("case",), (item,), digest, "fixture"), E.ESTABLISHED)
        with self.assertRaises(ValueError): acceptance_status((), (), digest)

    def test_failures_and_protocol_identity_cannot_be_erased(self):
        digest = "0" * 64
        item = AcceptanceEvidence("case", digest, E.FAILED, "runtime", (ref(K.EVIDENCE, "failure"),))
        self.assertEqual(acceptance_status(("case", "missing"), (item,), digest), E.FAILED)
        with self.assertRaises(ValueError): acceptance_status(("case",), (item,), "1" * 64)
        with self.assertRaises(ValueError): acceptance_status(("case",), (item, item), digest)
        with self.assertRaises(ValueError): replace(item, evidence_refs=())
