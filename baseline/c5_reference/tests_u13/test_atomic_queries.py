"""Independent state transitions test the host-query cache boundary."""
import unittest
from hle_unified.efficiency import install_command_query_cache


class Reference:
    def __init__(self):
        self.allowed={'alice':True,'bob':False}
        self.capacities={'alice':{'care':1},'bob':{}}
        self.calls=0

    def _root_available(self,actor):
        self.calls+=1
        return self.allowed[actor]

    def _current_aspects(self,actor):
        self.calls+=1
        return dict(self.capacities[actor]) if self._root_available(actor) else {}

    def _signature(self,actor):
        self.calls+=1
        return tuple(sorted(self._current_aspects(actor).items()))

    def _commit(self,actor):
        before=self._root_available(actor)
        self.allowed[actor]=False
        after=self._root_available(actor)
        return before,after

    def _circuit_work_step(self,mode):
        if mode=='error':
            self._signature('alice')
            raise ValueError('no completed effect')
        before=self._signature('alice')
        again=self._signature('alice')
        other=self._signature('bob')
        local=self._current_aspects('alice');local['unearned']=99
        retained=self._current_aspects('alice')
        if mode=='nested':
            self._circuit_work_step('commit')
            return before,self._signature('alice')
        change=self._commit('alice')
        return before,again,other,retained,change,self._signature('alice')


class AtomicQueryTests(unittest.TestCase):
    def optimized(self):
        class Optimized(Reference):pass
        install_command_query_cache(Optimized)
        return Optimized()

    def test_actor_ownership_and_publication_match_independent_reference(self):
        r,c=Reference(),self.optimized()
        self.assertEqual(r._circuit_work_step('commit'),c._circuit_work_step('commit'))
        self.assertLess(c.calls,r.calls)
        self.assertNotIn('_u13_command_queries',vars(c))
        self.assertEqual(c._current_aspects('alice'),{})

    def test_no_cached_check_survives_a_later_command(self):
        r,c=Reference(),self.optimized()
        for w in (r,c):w._circuit_work_step('commit');w.allowed['alice']=True;w.capacities['alice']['repair']=2
        self.assertEqual(r._circuit_work_step('commit'),c._circuit_work_step('commit'))

    def test_nested_publication_clears_outer_checks(self):
        r,c=Reference(),self.optimized()
        self.assertEqual(r._circuit_work_step('nested'),c._circuit_work_step('nested'))
        self.assertNotIn('_u13_command_queries',vars(c))

    def test_exception_clears_every_uncommitted_check(self):
        c=self.optimized()
        with self.assertRaises(ValueError):c._circuit_work_step('error')
        self.assertNotIn('_u13_command_queries',vars(c))
        c.allowed['alice']=False
        self.assertEqual(c._signature('alice'),())


if __name__=='__main__':unittest.main()
