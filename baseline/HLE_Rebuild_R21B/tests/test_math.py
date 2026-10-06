import json
import math
import unittest
from collections import Counter, deque
from itertools import product
from pathlib import Path

from hle import gf2 as g, model_a as a, relations as r
from .support import rules


class FiniteMathematics(unittest.TestCase):
    @rules("M01", "E01")
    def test_all_three_by_three_matrices_against_image_cardinality(self):
        invertible = 0
        for bits in product((0, 1), repeat=9):
            m = tuple(tuple(bits[i:i+3]) for i in range(0, 9, 3))
            # Image enumeration is independent of Gaussian elimination.
            image = {g.matvec(m, x) for x in g.vectors(3)}
            self.assertEqual(len(image), 2 ** g.rank(m))
            if len(image) == 8:
                invertible += 1
                inv = g.inverse(m)
                self.assertEqual(g.matmul(m, inv), g.identity(3))
                self.assertEqual(g.matmul(inv, m), g.identity(3))
            else:
                with self.assertRaises(ValueError): g.inverse(m)
        self.assertEqual(invertible, 168)

    @rules("M01")
    def test_all_invertible_affine_maps_roundtrip_every_point(self):
        count = 0
        for bits in product((0, 1), repeat=9):
            m = tuple(tuple(bits[i:i+3]) for i in range(0, 9, 3))
            if g.rank(m) != 3: continue
            for b in g.vectors(3):
                f = g.Affine(m, b)
                count += 1
                self.assertEqual(f.compose(f.inverse()), g.unit())
                for x in g.vectors(3): self.assertEqual(f.inverse()(f(x)), x)
        self.assertEqual(count, 1344)

    @rules("E01")
    def test_bad_bits_shapes_and_singular_affines_rejected(self):
        for f in (lambda: g.add((0,1), (1,)), lambda: g.dot((0,1), (1,)),
                  lambda: g.vector((True,0)), lambda: g.vector((2,0)),
                  lambda: g.vector([0,1]), lambda: g.inverse(((1,0),)),
                  lambda: g.matrix(((1,), (0,1))), lambda: g.vectors(0),
                  lambda: g.Affine(((0,),), (0,)),
                  lambda: g.Affine(((1,),), (0,0))):
            with self.assertRaises(ValueError): f()

    @rules("M02")
    def test_position_fields_match_source_sets(self):
        self.assertEqual(set(a.POSITION.values()), set(g.vectors(3)))
        self.assertEqual(set(a.ELEMENT.values()), set(g.vectors(3)))
        self.assertEqual([a.fields(p)["dimensionality"] for p in a.POSITION], [4,3,2,1,1,2,3,4])
        self.assertEqual({p for p in a.POSITION if a.fields(p)["strong"]}, {1,2,7,8})
        self.assertEqual({p for p in a.POSITION if a.fields(p)["contact"]}, {2,3,5,8})
        self.assertEqual({p for p in a.POSITION if a.fields(p)["bold"]}, {1,3,6,8})

    @rules("M03", "M04")
    def test_generated_frames_match_preserved_stack_fixture(self):
        fixture = json.loads(Path(__file__).with_name("stack_fixture.json").read_text())
        self.assertEqual(set(fixture), set(a.TYPES))
        frames = set()
        for tim in a.TYPES:
            f = a.frame(tim); frames.add(f)
            self.assertEqual(a.stack(tim), tuple(fixture[tim]))
            self.assertEqual(len(set(a.stack(tim))), 8)
            for p in range(1, 9): self.assertEqual(a.position_of(tim, a.element_at(tim, p)), p)
        self.assertEqual(len(frames), 16)
        self.assertEqual(a.stack("iee"), ("ne","fi","se","ti","si","te","ni","fe"))

    @rules("M04")
    def test_exhausts_sixteen_lawful_frames(self):
        expected = {g.Affine(tuple(zip(t, (0,0,1), (0,1,1))), l)
                    for l in g.vectors(3) for t in ((1,1,0), (1,1,1))}
        self.assertEqual({a.frame(t) for t in a.TYPES}, expected)

    @rules("M05")
    def test_routing_distances_against_independent_stack_bfs(self):
        fixture = json.loads(Path(__file__).with_name("stack_fixture.json").read_text())
        for tim, stack in fixture.items():
            graph = {e: {stack[j] for j in range(8) if (i ^ j).bit_count() == 1}
                     for i, e in enumerate(stack)}
            self.assertEqual(sum(map(len, graph.values())), 24)
            for start in stack:
                self.assertEqual(set(a.neighbors(tim, start)), graph[start])
                queue, distances = deque([start]), {start: 0}
                while queue:
                    current = queue.popleft()
                    for nxt in graph[current]:
                        if nxt not in distances:
                            distances[nxt] = distances[current] + 1; queue.append(nxt)
                for end in stack:
                    self.assertEqual(a.distance(tim, start, end), distances[end])
                    paths = a.shortest_paths(tim, start, end)
                    self.assertEqual(len(paths), math.factorial(distances[end]))
                    for path in paths:
                        self.assertEqual((path[0], path[-1]), (start, end))
                        self.assertEqual(len(path) - 1, distances[end])
                        self.assertTrue(all(y in graph[x] for x,y in zip(path, path[1:])))

    @rules("M05")
    def test_iee_source_worked_example_and_nonprimitive_return(self):
        self.assertEqual(set(a.neighbors("iee", "ti")), {"se","fi","fe"})
        self.assertEqual(a.distance("iee", "ti", "si"), 3)
        self.assertNotIn("si", a.neighbors("iee", "ti"))

    @rules("M06")
    def test_jungian_atlas_and_fifteen_balanced_characters(self):
        self.assertEqual({a.jungian(t) for t in a.TYPES}, set(g.vectors(4)))
        self.assertEqual(len(a.REININ), 15)
        for w in a.REININ: self.assertEqual(sum(a.character(w, t) for t in a.TYPES), 8)
        for tim in a.TYPES:
            l = a.frame(tim).offset
            d = a.frame(tim).linear[2][0]
            q,e,n = l
            self.assertEqual(a.jungian(tim), (e,n^(q*d),1^n^d^(q*d),1^q))
        self.assertEqual(Counter(a.club(t) for t in a.TYPES), {"NF":4,"NT":4,"SF":4,"ST":4})

    @rules("M07")
    def test_relation_group_source_structure_and_action(self):
        group = r.all_relations()
        self.assertEqual(len(group), 16)
        self.assertEqual(Counter(f.linear for f in group), {g.identity(3):8, ((1,0,0),(1,1,0),(0,0,1)):8})
        orders = Counter()
        for f in group:
            cur, order = f, 1
            while cur != g.unit(): cur = f.compose(cur); order += 1; self.assertLessEqual(order,4)
            orders[order] += 1
            self.assertIn(f.inverse(), group)
            for h in group: self.assertIn(f.compose(h), group)
        self.assertEqual(orders, {1:1,2:11,4:4})
        self.assertTrue(any(f.compose(h) != h.compose(f) for f in group for h in group))
        for source in a.TYPES:
            self.assertEqual({r.apply_relation(source, f) for f in group}, set(a.TYPES))
            self.assertEqual({r.relation(source,t) for t in a.TYPES}, group)

    @rules("M07")
    def test_relation_composition_all_type_triples(self):
        for first, second, third in product(a.TYPES, repeat=3):
            self.assertEqual(r.relation(first,third),
                             r.relation(first,second).compose(r.relation(second,third)))

    @rules("M07")
    def test_every_transfer_matches_same_element_in_receiver(self):
        for sender, receiver in product(a.TYPES, repeat=2):
            self.assertEqual(set(r.landing_permutation(sender,receiver)), set(range(1,9)))
            for p in range(1,9):
                landing = r.landing_position(sender,p,receiver)
                self.assertEqual(a.element_at(sender,p), a.element_at(receiver,landing))
                self.assertEqual(r.landing_position(receiver,landing,sender), p)

    @rules("M08")
    def test_estafette_is_only_a_permutation_and_generates_64_group(self):
        f = r.ESTAFETTE
        for x in g.vectors(3):
            self.assertEqual(f(x), (x[2],x[1],1^x[0]))
            self.assertEqual(f.compose(f)(x), (1^x[0],x[1],1^x[2]))
            self.assertEqual(f.compose(f).compose(f).compose(f)(x), x)
        group = r.extended_group()
        self.assertEqual(len(group),64)
        center = {f for f in group if all(f.compose(h)==h.compose(f) for h in group)}
        self.assertEqual(len(center),2)
        for f in group:
            self.assertEqual(f.compose(f).compose(f).compose(f),g.unit())
            for h in group: self.assertIn(f.compose(h),group)

    @rules("E01")
    def test_invalid_type_element_position_and_action(self):
        for call in (lambda:a.frame("invalid"), lambda:a.element("invalid"),
                     lambda:a.element_at("iee",0), lambda:a.element_at("iee",True),
                     lambda:a.position_of("iee","invalid"),
                     lambda:a.shortest_paths("invalid","ne","ne"),
                     lambda:r.landing_position("iee",9,"ile"),
                     lambda:r.apply_relation("iee",g.unit(2))):
            with self.assertRaises(ValueError):call()
        with self.assertRaises(TypeError): a.EGO["iee"] = ("ne","ti")
