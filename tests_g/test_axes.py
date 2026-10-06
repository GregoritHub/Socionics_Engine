import itertools,json,unittest
from pathlib import Path
from hle import model_a
from hle_unified import axes, model_g
ROOT=Path(__file__).resolve().parents[1]
TABLE=json.loads((ROOT/'contracts/sources/Axis_Table_v1.json').read_text())

class AxisTests(unittest.TestCase):
    def test_all_sixteen_table_rows(self):
        for tim,row in TABLE['types'].items():
            self.assertEqual(list(axes.axis_cells(tim)),row['cells'])
            for cell in 'DCNH':self.assertEqual(list(axes.formula_positions(tim,cell)),row['formulas'][cell])

    def test_axis_pairs_are_the_four_core_element_pairs(self):
        core={'D':{'te','fe'},'C':{'se','ne'},'N':{'ti','fi'},'H':{'si','ni'}}
        self.assertEqual(axes.AXES,((1,3),(2,4),(5,7),(6,8)))
        for tim in model_a.TYPES:
            for pair,cell in zip(axes.AXES,axes.axis_cells(tim)):
                self.assertEqual({model_a.element_at(tim,p) for p in pair},core[cell])

    def test_formulas_fill_three_positions_of_the_expected_plane(self):
        for tim in model_a.TYPES:
            extravert=bool(model_a.jungian(tim)[0])
            for cell in 'DCNH':
                expected='external' if (cell in 'DC')==extravert else 'internal'
                self.assertEqual(axes.formula_plane(tim,cell),expected)
                ps=axes.formula_positions(tim,cell)
                self.assertEqual(len(set(ps)),3)
                self.assertTrue(all(bool(model_a.fields(p)['bold'])==(expected=='external') for p in ps))

    def test_sign_patterns_and_parities(self):
        cases=[('valued',(1,1,1,1),0),('strong',(1,1,-1,-1),0),('contact',(-1,1,1,-1),0)]
        for name,signs,parity in cases:
            f={p:int(model_a.fields(p)[name]) for p in range(1,9)}
            self.assertEqual(axes.sign_vector(f),signs);self.assertEqual(axes.parity(f),parity)
        f={p:model_g.grade(p)>>1 for p in range(1,9)}
        self.assertEqual(axes.sign_vector(f),(1,1,1,-1));self.assertEqual(axes.parity(f),1)

    def test_grade_identity_on_all_positions(self):
        for p in range(1,9):
            f=model_a.fields(p)
            self.assertEqual(model_g.grade(p),2*int(f['valued'] if f['accepting'] else f['strong'])+int(f['ring']=='mental'))

    def test_integer_recovery_exhaustive_small_fields_and_large_basis(self):
        for vals in itertools.product((-1,0,1),repeat=8):
            f=dict(zip(range(1,9),vals));self.assertEqual(axes.recover(axes.load(f),axes.tilt(f)),f)
        for p in range(1,9):
            for value in (-(10**100),10**100+1):
                f={q:value if p==q else 0 for q in range(1,9)}
                self.assertEqual(axes.recover(axes.load(f),axes.tilt(f)),f)

    def test_load_tilt_equations_and_input_not_mutated(self):
        f={p:3*p-9 for p in range(1,9)};before=dict(f)
        l,t=axes.load(f),axes.tilt(f)
        for i,(p,q) in enumerate(axes.AXES):
            self.assertEqual(l[i]+t[i],2*f[p]);self.assertEqual(l[i]-t[i],2*f[q])
        self.assertEqual(f,before)

    def test_ties_and_invalid_integer_domains_explicit(self):
        valid={p:p%2 for p in range(1,9)}
        self.assertEqual(axes.sign_vector(valid),(0,0,0,0))
        with self.assertRaises(ValueError):axes.parity(valid)
        for invalid in ({}, {p:1.0 for p in range(1,9)}, {p:True for p in range(1,9)}, {p:1 for p in range(1,10)}, [0]*8):
            with self.assertRaises(ValueError):axes.load(invalid)
            with self.assertRaises(ValueError):axes.tilt(invalid)
        with self.assertRaises(ValueError):axes.sign_vector({p:0 for p in range(1,9)})
        with self.assertRaises(ValueError):axes.recover((1,0,0,0),(0,0,0,0))
        with self.assertRaises(ValueError):axes.recover((0,)*3,(0,)*4)
        with self.assertRaises(ValueError):axes.formula_positions('iee','X')
        with self.assertRaises(ValueError):axes.axis_cells('bad')
