import itertools,json,unittest
from pathlib import Path
from hle import model_a
from hle_unified import model_g as g

ROOT=Path(__file__).resolve().parents[1]
TABLE=json.loads((ROOT/'contracts/sources/Model_G_Table_v1.json').read_text())

class ModelGTests(unittest.TestCase):
    def test_all_128_elements_and_signs_against_transcribed_source(self):
        for tim,row in TABLE['types'].items():
            for k,expected in enumerate(row['signed_stack'],1):
                x=g.describe(tim,k)
                self.assertEqual(x['sign']+x['element'],expected.lower())
                self.assertEqual(x['label'],row['label'])

    def test_all_source_position_attributes(self):
        for tim in model_a.TYPES:
            for row in TABLE['positions']:
                actual=g.describe(tim,row['g_position'])
                for field,value in row.items():self.assertEqual(actual[field],value)
                self.assertEqual(actual['grade_name'],('pessimum','minimum','optimum','maximum')[row['grade']])

    def test_unique_reindexing_of_all_40320_permutations(self):
        stacks={t:model_a.stack(t) for t in model_a.TYPES}
        target={t:tuple(x[1:].lower() for x in row['signed_stack']) for t,row in TABLE['types'].items()}
        fits=[];count=0
        for pi in itertools.permutations(range(1,9)):
            count+=1
            if all(tuple(stacks[t][a-1] for a in pi)==target[t] for t in model_a.TYPES):fits.append(pi)
        self.assertEqual(count,40320)
        self.assertEqual(fits,[(1,8,3,6,2,5,4,7)])
        self.assertEqual(tuple(g.g_to_a(k) for k in range(1,9)),fits[0])
        for k in range(1,9):self.assertEqual(g.a_to_g(g.g_to_a(k)),k)

    def test_grade_bits_and_two_independent_field_formulas(self):
        for p in range(1,9):
            a,v,r=model_a.position(p);f=model_a.fields(p)
            self.assertEqual(g.grade(p),2*int(f['valued'] if f['accepting'] else f['strong'])+int(f['ring']=='mental'))
            self.assertEqual(g.grade(p),2*int(f['valued'] if r==0 else f['contact'])+(1-r))
            self.assertEqual(g.grade(p)&1,1-r)
            self.assertEqual(g.grade(p)>>1,1 ^ v ^ (a & r))

    def test_partners_match_source_blocks_and_grades(self):
        for row in TABLE['positions']:
            p=g.g_to_a(row['g_position']);bp=g.block_partner(p);gp=g.grade_partner(p)
            self.assertNotEqual(bp,p);self.assertNotEqual(gp,p)
            self.assertEqual(g.block_partner(bp),p);self.assertEqual(g.grade_partner(gp),p)
            self.assertEqual(TABLE['positions'][g.a_to_g(bp)-1]['block'],row['block'])
            self.assertEqual(TABLE['positions'][g.a_to_g(gp)-1]['grade'],row['grade'])

    def test_labels_equal_kernel_character_on_all_types(self):
        for tim,row in TABLE['types'].items():
            self.assertEqual(row['label']=='positivist',model_a.character((1,1,1,0),tim)==1)

    def test_source_spine_and_crossed_names_only(self):
        for tim in model_a.TYPES:
            self.assertEqual(g.spine(tim),tuple((p,model_a.element_at(tim,p)) for p in (6,1,8)))
        self.assertEqual(g.describe('iee',2)['name'],'Creative')
        self.assertEqual(g.describe('iee',2)['a_position'],8)
        self.assertEqual(g.describe('iee',5)['name'],'Demonstrative')
        self.assertEqual(g.describe('iee',5)['a_position'],2)

    def test_invalid_inputs_rejected_and_results_not_shared(self):
        for invalid in (0,9,True,1.0,'1'):
            for fn in (g.g_to_a,g.a_to_g,g.grade,g.block_partner,g.grade_partner):
                with self.assertRaises(ValueError):fn(invalid)
            with self.assertRaises(ValueError):g.sign('iee',invalid)
        for invalid in ('IEE','unknown',None,1):
            with self.assertRaises(ValueError):g.describe(invalid,1)
            with self.assertRaises(ValueError):g.spine(invalid)
        a=g.describe('iee',1);a['grade']=-99
        self.assertEqual(g.describe('iee',1)['grade'],3)
        self.assertTrue(TABLE['transcribed_not_reread'])
