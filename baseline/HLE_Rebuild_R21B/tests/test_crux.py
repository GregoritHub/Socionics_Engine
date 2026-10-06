import unittest
from itertools import product
from hle.crux import *
from hle.contracts import IdeaCell, IdeaPhase
from .support import rules


class FormalRoutes(unittest.TestCase):
    @rules("C01", "C02")
    def test_exact_source_route_table(self):
        expected = ["Contemplate","Express","Share","Theorize", "Embody","Act","Coordinate","Organize",
                    "Identify","Mobilize","Commune","Institutionalize", "Understand","Apply","Educate","Integrate"]
        self.assertEqual([r.name for r in routes()],expected)
        self.assertEqual(len(set(routes())),16)
        self.assertEqual(dict(CODE), {Perspective.I:0,Perspective.IT:1,Perspective.WE:2,Perspective.ITS:3})

    @rules("C02")
    def test_all_route_pairs_composition_and_inverses(self):
        composable = 0
        for first,second in product(routes(),repeat=2):
            if first.destination==second.origin:
                composable += 1
                self.assertEqual(first.then(second),Route(first.origin,second.destination))
                self.assertEqual(first.then(second).displacement, first.displacement^second.displacement)
            else:
                with self.assertRaises(ValueError):first.then(second)
        self.assertEqual(composable,64)
        for route in routes():
            self.assertEqual(route.then(route.inverse()),Route(route.origin,route.origin))
            self.assertEqual(route.inverse().then(route),Route(route.destination,route.destination))

    @rules("C02")
    def test_all_composable_triples_associative(self):
        for a,b,c,d in product(Perspective,repeat=4):
            first,second,third=Route(a,b),Route(b,c),Route(c,d)
            self.assertEqual(first.then(second).then(third),first.then(second.then(third)))

    @rules("C03")
    def test_32_formal_movements_and_bad_inputs(self):
        self.assertEqual({m.bits for m in movements()},set(range(32)))
        for args in (("I",Perspective.IT),(Perspective.I,"WE"),(None,Perspective.I)):
            with self.assertRaises(ValueError):Route(*args)
        with self.assertRaises(ValueError):FormalMovement(routes()[0],"accumulation")

    @rules("C04", "E07")
    def test_formal_inverse_is_not_a_realized_return_or_idea_cell(self):
        route=Route(Perspective.I,Perspective.ITS)
        self.assertEqual(route.then(route.inverse()).displacement,0)
        self.assertFalse(hasattr(route,"execute"))
        self.assertNotEqual(route,IdeaCell(IdeaPhase.INITIATE,Perspective.ITS))
        with self.assertRaises(ValueError):route.then(IdeaCell(IdeaPhase.ENGAGE,Perspective.I))
