import unittest
from hle.model_a import TYPES,fields,element_at,neighbors
from hle.crux import Perspective
from tests_u5.fixtures import *
from hle_unified.cognitive_routes import route,flatten_route,progress
from hle_unified.cognitive_audit import audit_extent


class Geometry(unittest.TestCase):
    def test_all_types_and_same_history_have_same_grounded_action(self):
        costs=set()
        for tim in TYPES:
            e=setup5(tim)
            p=think(e,request5(e))
            d=e.job_status(ALICE,"plan")
            costs.add(d["spent"])
            self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"repair",tim)
            audit_extent(d)
        self.assertGreater(len(costs),1)
        self.assertEqual([fields(i)["dimensionality"] for i in range(1,9)],[4,3,2,1,1,2,3,4])

    def test_equal_limited_work_changes_progress_not_hidden_information(self):
        signatures=set()
        views=set()
        for tim in TYPES:
            e=setup5(tim)
            views.add(e.participant_view(ALICE).bytes())
            e.start("start",request5(e))
            required=e.job_status(ALICE,"plan")["required"]
            e.advance("work",ALICE,"plan",18)
            d=e.job_status(ALICE,"plan")
            self.assertEqual(d["spent"],18)
            signatures.add(progress(d))
        self.assertGreater(len(signatures),1)
        self.assertEqual(len(views),1)

    def test_missing_single_function_crossings_rejected_for_all_types(self):
        for tim in TYPES:
            for origin,destination in (("I","IT"),("WE","ITS"),("IT","I"),("ITS","WE")):
                for element in ("fi","fe","ti","te","si","se","ni","ne"):
                    with self.assertRaises(ValueError):
                        route(tim,element_at(tim,1),(element,),origin,destination,"expenditure")

    def test_all_incident_source_edges_have_two_polarities(self):
        from hle.concept_structure import EDGES
        for tim in TYPES:
            for element in ("fi","fe","ti","te","si","se","ni","ne"):
                for origin in EDGES[element[0]]:
                    destination=next(x for x in EDGES[element[0]] if x!=origin)
                    for polarity in ("accumulation","expenditure"):
                        rows=route(tim,element_at(tim,1),(element,),origin,destination,polarity)
                        row=rows[0]
                        self.assertEqual(row["origin"],origin.value)
                        self.assertTrue(all(b in neighbors(tim,a) for a,b in zip(row["path"],row["path"][1:])))
                        self.assertIn(row["support_seat"],(5,7) if polarity=="accumulation" else (6,8))

    def test_alternative_lawful_composition_is_paid_and_actionable(self):
        e=setup5()
        p=think(e,request5(e,elements=("ne","te")))
        d=e.job_status(ALICE,"plan")
        self.assertEqual(d["route.0.destination"],"ITS")
        self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"repair")
        audit_extent(d)

    def test_source_rank_suit_and_unspecified_meanings_are_distinct(self):
        e=setup5()
        from hle_unified.cognitive_records import reference
        ace=e.world.resolve(reference("minor:Coin:1"))
        ten=e.world.resolve(reference("minor:Coin:10"))
        self.assertNotEqual(ace.ref,ten.ref)
        self.assertEqual(attrs(ace)["folded_location"],attrs(ten)["folded_location"])
        self.assertNotEqual(attrs(ace)["rank"],attrs(ten)["rank"])
        self.assertIsNone(ace.facet(Definition).meaning)
        self.assertEqual(ace.facet(Definition).source_status,SourceStatus.UNSPECIFIED)
        self.assertEqual(ten.facet(Definition).meaning,"Security")
        self.assertIsNone(attrs(e.world.resolve(reference("arcana:0")))["folded_location"])

    def test_contextual_recall_and_linked_cues_have_variable_structure(self):
        e=setup5()
        other=ref("second-room")
        e.declare("room",(ObjectVersion(other,WRITER,"Second context",(Role.CONTEXT,)),))
        show(e,ALICE,other)
        seed(e,"other-context","serviceable",context=other)
        alternative=reference("minor:Wand:10")
        show(e,ALICE,alternative)
        linked=seed(e,"linked","damaged",cue=alternative,links=(ref("initial-account"),))
        view=e.participant_view(ALICE)
        self.assertEqual(len(view.traverse(CUE5,ROOM).visited),1)
        self.assertEqual(len(view.traverse(alternative,ROOM).visited),2)
        self.assertEqual(view.traverse(CUE5,other).bindings[0].content[0].object,"serviceable")

    def test_generalized_property_reconciliation_works_for_wear(self):
        e=setup5()
        wear_rule=ref("wear-policy")
        e.declare("wear-rule",(ObjectVersion(wear_rule,WRITER,"Wear rule",(Role.DEFINITION,),
            (Definition("Wear evidence remains independent of condition",SourceStatus.ENGINEERING,
                attributes({"relation":"wear","default":"inspect","when.0":"use"})),)),))
        show(e,ALICE,wear_rule,selectors=(Selector("rule","definition",("facets","0")),))
        seed(e,"wear-belief",0,relation="wear")
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        obs=receive(e,event,ALICE,"wear-observation")
        retained=think(e,request5(e,"wear-retain","integrate",source=obs,rule=wear_rule))
        claim=e.world.resolve(retained).facet(Account).content[0]
        self.assertEqual((claim.relation,claim.object),("wear",3))
