from dataclasses import replace
from itertools import combinations
import json
from pathlib import Path
import unittest

from hle.contracts import Ref, Kind as K, EvidenceStatus as E
from hle.crux import Perspective as P, routes
from hle.model_a import TYPES, position, element_at
from hle.development_contracts import StructuralFingerprint
from hle.development_structure import FUNCTION_EDGES, PORTAGES, QUOTIENTS, portage, lap, LensContent, quotient, observe_trajectory
from hle.idea import FiniteIDEA, FiniteProtocol


class Structure(unittest.TestCase):
    def test_fixed_structure_all_types(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/stack_fixture.json").read_text())
        for tim in TYPES:
            g = StructuralFingerprint.for_tim(tim)
            self.assertEqual(g.model_a_stack, tuple(fixture[tim]))
            self.assertEqual(g.dimensions, (4, 3, 2, 1, 1, 2, 3, 4))
            with self.assertRaises(ValueError): replace(g, dimensions=(4,) * 8)

    def test_no_horizontal_primitive(self):
        edges = tuple(FUNCTION_EDGES.values())
        self.assertEqual(len(set(edges)), 4)
        for q in P: self.assertEqual(sum(q in edge for edge in edges), 2)
        self.assertNotIn(frozenset((P.I, P.IT)), edges)
        self.assertNotIn(frozenset((P.WE, P.ITS)), edges)
        self.assertEqual(len(routes()), 16)

    def test_portages_and_laps(self):
        cp_pairs = {"ne":"si", "si":"ne", "ni":"se", "se":"ni", "fe":"ti", "ti":"fe", "te":"fi", "fi":"te"}
        for p in range(1, 9):
            self.assertEqual(lap(lap(lap(lap(p)))), p)
            for name in PORTAGES:
                other = portage(p, name)
                self.assertEqual(position(p)[0], position(other)[0])
                self.assertEqual(portage(other, name), p)
                expected = lap(p) if name == "n" else lap(lap(lap(p)))
                self.assertEqual(portage(lap(portage(p, name)), name), expected)
            for tim in TYPES:
                self.assertEqual(element_at(tim, portage(p, "cp")), cp_pairs[element_at(tim, p)])
        for start in (1, 3):
            seats = (start, lap(start), lap(lap(start)), lap(lap(lap(start))))
            self.assertEqual(len(set(seats)), 4)
            self.assertEqual(tuple(position(p)[0] for p in seats), (0, 0, 1, 1))

    def test_exact_recovered_quotient_cardinalities(self):
        domains = [tuple(c) for n in range(5) for c in combinations(P, n)]
        context, contract = Ref(K.CONTEXT, "c", 1), Ref(K.PROTOCOL, "lens", 1)
        for tim in TYPES:
            for depth, expected in (("dom", 16), ("access", 10), ("route", 4), ("top", 1)):
                values = {quotient(tim, LensContent(d, (), context, contract), (depth, "top")) for d in domains}
                self.assertEqual(len(values), expected, (tim, depth))
        self.assertEqual(len(QUOTIENTS), 12)

    def test_oig_cancellation_and_benign_return_do_not_label_shells(self):
        a = LensContent((P.I,), (), Ref(K.CONTEXT, "c", 1), Ref(K.PROTOCOL, "lens", 1))
        b = replace(a, domains=(P.ITS,))
        data = observe_trajectory("iee", (a, b, a))
        self.assertTrue(data["V"])
        self.assertFalse(data["N"])
        self.assertEqual(data["K"], data["V"])
        self.assertEqual(data["R"][("dom", "top")], ((0, 2), (1,)))
        self.assertNotIn("shell", data)
        quiet = observe_trajectory("iee", (a, a))
        self.assertEqual((quiet["V"], quiet["N"], quiet["K"]), (frozenset(), frozenset(), frozenset()))
        self.assertTrue(all(groups == ((0, 1),) for groups in quiet["R"].values()))

    def test_foreign_appearance_is_different_from_origin_foreign(self):
        a = LensContent((P.I,), (), Ref(K.CONTEXT, "c", 1), Ref(K.PROTOCOL, "lens", 1))
        b = replace(a, foreign=(Ref(K.MEMORY, "foreign", 1),))
        appeared = observe_trajectory("sli", (a, b))
        existing = observe_trajectory("sli", (b, b))
        self.assertIn(("top", "paired"), appeared["V"])
        self.assertFalse(existing["V"])

    def test_oig_scope_and_foreign_revision_are_explicit(self):
        a = LensContent((P.I,), (Ref(K.MEMORY, "foreign", 1),), Ref(K.CONTEXT, "c", 1), Ref(K.PROTOCOL, "lens", 1))
        b = replace(a, foreign=(Ref(K.MEMORY, "foreign", 2),))
        data = observe_trajectory("sli", (a, b))
        self.assertIn(("top", "unpaired"), data["V"])
        self.assertNotIn(("top", "paired"), data["V"])
        with self.assertRaises(ValueError): observe_trajectory("sli", (a, replace(b, context=Ref(K.CONTEXT, "other", 1))))

    def test_canon_repeated_return(self):
        x = FiniteIDEA((0, 0, 1), (FiniteProtocol("h", (1, 2, 2), (0, 1, 2)),))
        self.assertEqual(x.sequence(0, (0,))[0], E.ESTABLISHED)
        self.assertEqual(x.sequence(0, (0, 0))[0], E.FAILED)
        self.assertEqual(x.closure(0), E.UNASSESSED)
