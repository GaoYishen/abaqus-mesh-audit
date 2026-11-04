import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import mesh_audit as ma

ROOT=Path(__file__).resolve().parents[1]


class MeshTests(unittest.TestCase):
    def run_text(self,text):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'mesh.inp'; p.write_text(text)
            return ma.audit(p)

    def good(self):
        return (ROOT/'examples/two-triangles.inp').read_text()

    def test_triangles_and_boundaries(self):
        r=ma.audit(ROOT/'examples/two-triangles.inp')
        self.assertTrue(r['audit_pass']); self.assertEqual(r['boundary_edge_count'],4)
        self.assertAlmostEqual(sum(e['signed_area'] for e in r['elements']),1)
        self.assertEqual(r['elset_element_counts'],{'SOLID':2})

    def test_q4_and_concavity(self):
        r=ma.audit(ROOT/'examples/square-q4.inp')
        self.assertTrue(r['audit_pass']); self.assertAlmostEqual(r['elements'][0]['min_sampled_jacobian'],0.25)
        text=(ROOT/'examples/square-q4.inp').read_text().replace('3, 1, 1','3, 0.2, 0.2')
        self.assertIn('nonpositive_or_degenerate_q4_jacobian',[i['kind'] for i in self.run_text(text)['issues']])

    def test_inverted_and_degenerate(self):
        self.assertFalse(ma.audit(ROOT/'examples/inverted-triangle.inp')['audit_pass'])
        text=self.good().replace('3, 1, 1','3, 2, 0')
        r=self.run_text(text)
        self.assertFalse(r['audit_pass']); json.dumps(r,allow_nan=False)

    def test_nonmanifold_and_duplicate_elements(self):
        text=self.good()+'3, 1, 2, 3\n'
        kinds={i['kind'] for i in self.run_text(text)['issues']}
        self.assertIn('nonmanifold_edge',kinds); self.assertIn('duplicate_element_connectivity',kinds)

    def test_coincident_nodes(self):
        text=self.good().replace('*Element','5, 0, 0\n*Element')
        self.assertIn('coincident_nodes',[i['kind'] for i in self.run_text(text)['issues']])

    def test_invalid_inputs_rejected(self):
        bad=[self.good().replace('CPE3','C3D4'), self.good().replace('2, 1, 3, 4','2, 1, 3, 99'),
             '*Include, input=other.inp\n', '*Part, name=part\n'+self.good(),
             self.good().replace('1, 0, 0','1, 0, 0, 1'), self.good().replace('2, 1, 0','2, nan, 0'),
             self.good()+'*Ncopy, change number=10\n', self.good()+'*Node, input=other.inp\n']
        for text in bad:
            with self.subTest(text=text[:25]),self.assertRaises(ValueError): self.run_text(text)

    def test_generate_and_scale(self):
        r=self.run_text(self.good()+'*Elset, elset=ALL, generate\n1,2,1\n')
        self.assertEqual(r['elset_element_counts']['ALL'],2)
        text='*Node\n1,0,0\n2,1e-9,0\n3,0,1e-9\n*Element,type=CPE3\n1,1,2,3\n'
        self.assertTrue(self.run_text(text)['audit_pass'])

    def test_cli_exit_codes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'report.json'
            base=[sys.executable,str(ROOT/'mesh_audit.py')]
            good=base+[str(ROOT/'examples/two-triangles.inp'),'--output',str(output)]
            self.assertEqual(subprocess.run(good,capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(good,capture_output=True).returncode,2)
            self.assertEqual(subprocess.run(base+[str(ROOT/'examples/inverted-triangle.inp')],capture_output=True).returncode,1)


if __name__=='__main__': unittest.main()
