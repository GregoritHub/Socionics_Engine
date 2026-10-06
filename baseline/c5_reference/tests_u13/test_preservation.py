import dataclasses
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from hle.contracts import _typed, Ref, Kind, Moment, TimeScope, ResourceAmount
from hle_unified.efficiency import validator, share_validated_graph, exact_equal
from hle_unified.compact import ValuePool, CompactStore, seal, unseal
from hle_unified.store import ObjectStore, next_version
from hle_unified.records import ObjectId, ObjectRef, ObjectVersion, Attribute, Role
from hle_unified.archive import write_history, HistoryArchive, SCHEMA
from hle_unified import codec


class Preservation(unittest.TestCase):
    def test_compiled_validation_matches_original_predicate(self):
        hints = (int, bool, str, Ref, int | str | bool | None,
                 tuple[int, ...], tuple[Ref, str, bool], tuple[tuple[int | bool, ...], ...])
        values = (0, 1, True, False, None, '', 'x', Ref(Kind.ENTITY, 'x', 1),
                  (), [], {}, (1, 2), (True, 0), ((1, False),),
                  (Ref(Kind.ENTITY, 'x', 1), 's', False))
        for hint in hints:
            for value in values:
                with self.subTest(hint=hint, value=value):
                    self.assertEqual(validator(hint)(value), _typed(value, hint))

    def test_local_validation_still_rejects_invalid_extent(self):
        with self.assertRaises(ValueError):
            Moment(-1, 0)
        with self.assertRaises(ValueError):
            Ref(Kind.ENTITY, '', 1)
        with self.assertRaises(ValueError):
            Ref(Kind.ENTITY, 'a', True)
        with self.assertRaises(ValueError):
            TimeScope(Moment(3, 0), Moment(1, 0))

    def test_structural_pool_distinguishes_nested_bool_and_int(self):
        p = ValuePool()
        a, b = p.put((False, (True,))), p.put((0, (1,)))
        self.assertNotEqual(a, b)
        self.assertIs(type(p.get(a)[0]), bool)
        self.assertIs(type(p.get(b)[0]), int)
        self.assertFalse(exact_equal((Attribute('a', False),), (Attribute('a', 0),)))

    def test_pool_reuses_structure_without_merging_referents(self):
        p = ValuePool()
        a = ObjectRef(ObjectId('person', 'alice'), 1)
        b = ObjectRef(ObjectId('person', 'bob'), 1)
        self.assertEqual(p.put((a,)), p.put((a,)))
        self.assertNotEqual(p.put((a,)), p.put((b,)))
        self.assertNotEqual(p.put((a,)), p.put((dataclasses.replace(a, revision=2),)))

    def test_structural_hash_collisions_verify_equality_before_reuse(self):
        p = ValuePool(); p._node_hash = lambda signature: 7
        a, b = p.put(('a',)), p.put(('b',))
        self.assertNotEqual(a, b)
        self.assertEqual(p.put(('a',)), a)
        self.assertEqual(p.get(b), ('b',))

    def test_graph_sharing_keeps_mutable_containers_and_distinct_revisions(self):
        a = Ref(Kind.ENTITY, 'alice', 1)
        aa = Ref(Kind.ENTITY, 'alice', 1)
        b = Ref(Kind.ENTITY, 'alice', 2)
        left, right = [a], [aa, b]
        root = {'left': left, 'right': right, 'flag': False, 'number': 0}
        root['cycle'] = root
        share_validated_graph(root)
        self.assertIs(root['cycle'], root)
        self.assertIs(root['left'], left); self.assertIs(root['right'], right)
        self.assertIs(left[0], right[0]); self.assertIsNot(right[0], right[1])
        self.assertIs(type(root['flag']), bool); self.assertIs(type(root['number']), int)

    def test_graph_sharing_has_no_cross_world_table(self):
        a = share_validated_graph([Ref(Kind.ENTITY, 'alice', 1)])
        b = share_validated_graph([Ref(Kind.ENTITY, 'alice', 1)])
        self.assertEqual(a, b); self.assertIsNot(a[0], b[0])

    def test_long_revisions_have_bounded_lookup_and_exact_reconstruction(self):
        compact, full = CompactStore(), ObjectStore()
        ref = ObjectRef(ObjectId('history', 'unique'), 1)
        v = ObjectVersion(ref, 'writer', 'origin', (Role.RECORD,), attributes=(Attribute('n', 0),))
        for s in (compact, full): s.create('start', 'writer', (v,))
        for i in range(1, 4097):
            v = next_version(v, attributes=(Attribute('n', i),))
            for s in (compact, full): s.revise('r' + str(i), 'writer', v)
        for index in (1, 31, 32, 33, 100, 1000, 4096, 4097):
            r = ObjectRef(ref.identity, index)
            self.assertEqual(codec.dumps(compact.resolve(r)), codec.dumps(full.resolve(r)))
            self.assertLessEqual(compact._versions.last_visits, 32)
        self.assertEqual(compact.canonical_checkpoint(), full.checkpoint())

    def test_unresolved_instance_and_ref_still_rejected_atomically(self):
        w = CompactStore(); before = w.checkpoint()
        bad = ObjectVersion(ObjectRef(ObjectId('record', 'x'), 1), 'w', 'x', (Role.RECORD,),
                            attributes=(Attribute('owner', ObjectId('person', 'missing')),))
        with self.assertRaises(ValueError): w.create('bad', 'w', (bad,))
        self.assertEqual(w.checkpoint(), before)

    def test_hidden_update_invalidates_cache_without_changing_view(self):
        from tests_u3.fixtures import setup, basics, ALICE, FORM, WRITER
        w, a = setup(); basics(a, ALICE.identity)
        before = a.view(ALICE.identity)
        w.revise('hidden', WRITER, next_version(w.resolve(FORM), label='unreceived new label'))
        after = a.view(ALICE.identity)
        self.assertIsNot(before, after); self.assertEqual(before.bytes(), after.bytes())

    def test_segment_history_exact_full_and_selective_reconstruction(self):
        w = CompactStore()
        for i in range(13):
            v = ObjectVersion(ObjectRef(ObjectId('archive', str(i)), 1), 'w', 'label', (Role.RECORD,))
            w.create(str(i), 'w', (v,))
        with tempfile.TemporaryDirectory() as d:
            archive = write_history(w, Path(d)/'history', segment_size=4)
            self.assertEqual(archive.transaction(8), w.journal()[8])
            self.assertEqual(archive.segments_read, 1)
            restored = archive.restore(CompactStore)
            self.assertEqual(restored.checkpoint(), w.checkpoint())

    def test_segment_corruption_and_manifest_reordering_reject(self):
        w = CompactStore()
        for i in range(3):
            v = ObjectVersion(ObjectRef(ObjectId('archive', str(i)), 1), 'w', 'label', (Role.RECORD,))
            w.create(str(i), 'w', (v,))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'history'; archive = write_history(w, path, segment_size=1)
            name = path/archive.manifest['segments'][1]['name']
            name.write_bytes(name.read_bytes() + b'x')
            with self.assertRaises(ValueError): archive.transaction(1)
            payload = archive.manifest; payload['segments'].reverse()
            (path/'manifest.json').write_text(seal(SCHEMA, payload))
            with self.assertRaises(ValueError): HistoryArchive(path)

    def test_empty_archive_is_exact(self):
        with tempfile.TemporaryDirectory() as d:
            a = write_history(CompactStore(), Path(d)/'empty')
            self.assertEqual(a.restore(CompactStore).journal(), ())


if __name__ == '__main__': unittest.main()
