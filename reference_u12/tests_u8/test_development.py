import unittest
from tests_u8.fixtures import *


class DevelopmentTests(unittest.TestCase):
    def test_local_repair_preserves_other_bindings_and_original_material(self):
        e=setup8();p=generated(e);original=e.world.resolve(p.origin)
        release8(e,"local",p)
        good=respond8(e,"local-return",p)
        residual=respond8(e,"residual",p,(GROUP,),partner=ObjectRef(EVE,1))
        self.assertTrue(e._response_results[good]["completed_demand"])
        self.assertFalse(e._response_results[residual]["completed_demand"])
        self.assertEqual(e.world.resolve(p.origin),original)
        self.assertEqual(e._treatments[p.origin]["kind"],"displacement")
        self.assertEqual(e._treatments[p.origin]["carrier"],ObjectRef(EVE,1))
        self.assertEqual(len(e.pattern_view(ALICE)),1)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_support_enables_performance_without_mastery_and_withdrawal_recurs(self):
        e=setup8();p=generated(e)
        a=respond8(e,"supported",p,approved=True)
        ex=practice8(e,"supported-practice",p,a)
        self.assertTrue(e._response_results[a]["completed_demand"])
        self.assertFalse(ex["independent"])
        with self.assertRaises(ValueError):reorganize8(e,"no-free-mastery",p)
        b=respond8(e,"withdrawn",p)
        self.assertFalse(e._response_results[b]["completed_demand"])
        self.assertFalse(e._capacities)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_two_independent_practices_change_reusable_capacity(self):
        e,p=trained8()
        cap=e._capacities[p.ref]
        self.assertEqual(cap["max_load"],2)
        self.assertEqual(len(cap["examples"]),2)
        event=respond8(e,"transfer",p,(MEMORY,POSSIBILITY),partner=ObjectRef(EVE,1))
        response=e._response_results[event]
        self.assertTrue(response["completed_demand"])
        self.assertFalse(response["supported"])
        self.assertEqual(response["row.0.bases"],((p.ref,cap["ref"]),))
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_overload_remains_residual_and_does_not_inflate_capacity(self):
        e,p=trained8()
        event=respond8(e,"overload",p,(MEMORY,POSSIBILITY,ACTION))
        self.assertFalse(e._response_results[event]["completed_demand"])
        ex=practice8(e,"overload-practice",p,event)
        self.assertFalse(ex["independent"])
        self.assertEqual(e._capacities[p.ref]["max_load"],2)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_reownership_requires_later_independent_returns(self):
        e,p=trained8()
        with self.assertRaises(ValueError):reorganize8(e,"early-reown",p,"reown")
        returned8(e,p)
        treatment=e._treatments[p.origin]
        self.assertEqual(treatment["ownership"],"reowned")
        self.assertIsNone(treatment["carrier"])
        self.assertEqual(treatment["origin"],p.origin)
        self.assertEqual(e.world.resolve(p.origin).ref,p.origin)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_single_success_is_not_generalization(self):
        e=setup8();p=generated(e)
        release8(e,"local",p)
        practice8(e,"practice",p,respond8(e,"task",p))
        with self.assertRaises(ValueError):reorganize8(e,"too-soon",p)

    def test_duplicate_delivery_is_not_another_practice(self):
        e=setup8();p=generated(e);release8(e,"local",p)
        event=respond8(e,"task",p);practice8(e,"practice",p,event)
        with self.assertRaises(ValueError):practice8(e,"duplicate",p,event)
        self.assertEqual(len(e._practices[p.ref]),1)

    def test_actual_constraints_survive_generalization(self):
        e,p=trained8()
        for i,terms in enumerate(({"safe":False},{"available":False},
                {"requires_partner":True,"willing":False},{"approval_required":True})):
            event=respond8(e,"constraint-"+str(i),p,(MEMORY,),**terms)
            response=e._response_results[event]
            self.assertEqual(response["row.0.route"],"wait")
            self.assertEqual(response["row.0.patterns"],())
            self.assertFalse(response["completed_demand"])
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_quiet_is_not_success(self):
        e=setup8();p=generated(e)
        event=respond8(e,"rest",p,demand=False)
        self.assertEqual(e._response_results[event]["row.0.route"],"rest")
        self.assertFalse(practice8(e,"rest-practice",p,event)["independent"])

    def test_corrected_shell_encounter_uses_retained_account(self):
        e=setup8();p=generated(e)
        release8(e,"local",p)
        sources=opportunity(e.participant_view(ALICE),SAW,ROOM)[1]
        result=attrs(e.world.resolve(meet(e,"encounter",sources[0])))
        self.assertEqual(result["route"],"engage")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_retained_capacity_changes_u6_action_and_actual_material_effect(self):
        e,p=trained8(setup8(serviceable=True,prior="serviceable"),reorganize=False)
        control=DevelopmentEngine.restore(e.checkpoint())
        self.assertEqual(first_choice(control),"inspect")
        reorganize8(e,"reorganize",p)
        self.assertNotIn((p.ref,SAW),e._corrections)
        choice=first_choice(e)
        drive(e,delivery=False,prefix="execute")
        self.assertEqual(choice,"use")
        self.assertEqual(attrs(e.world.head(SAW.identity))["wear"],1)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_restore_retains_scoped_capacity_and_future_choices(self):
        e,p=trained8();checkpoint=e.checkpoint();restored=DevelopmentEngine.restore(checkpoint)
        self.assertEqual(restored.checkpoint(),checkpoint)
        for x in (e,restored):respond8(x,"next",p,(MEMORY,POSSIBILITY),partner=ObjectRef(EVE,1))
        self.assertEqual(e.checkpoint(),restored.checkpoint())


if __name__=="__main__":unittest.main()
