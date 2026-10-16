"""All snapshots remain blocked; malformed evidence must never create release GO."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from enterprise.release_preflight import inspect_course, to_markdown, GATE_A
from enterprise.demo_pilot import run


class ReleaseSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        base = self.root / 'docs/production/data'
        base.mkdir(parents=True)
        self.base = base
        criteria = {a:'MET' for a in GATE_A}
        criteria['A11']='NOT_MET'
        criteria['A14']='NOT_MET'
        (base/'truth_matrix.json').write_text(json.dumps({'COURSE-PY-ENG': {
            'state':'TECHNICALLY_VERIFIED','score':89.7,'criteria':criteria,
            'modules':{'PY-M01':{'state':'TECHNICALLY_VERIFIED'}},
            'labs':{'planned':25,'verified_executable':25}}}),encoding='utf8')
        (base/'pdf_manifest.json').write_text(json.dumps({'course_editions':[{ 'course':'COURSE-PY-ENG',
             'kind':'PREVIEW','passed':True,'pdf_pages':397,'problems':{}}]}),encoding='utf8')
        (base/'defects.yaml').write_text(yaml.safe_dump({'defects':[{'id':'DEF-004','severity':'P1','status':'OPEN',
                  'applies_to':['*']}]}),encoding='utf8')
        (base/'human_reviews.yaml').write_text(yaml.safe_dump({'reviews':[]}),encoding='utf8')

    def tearDown(self):
        self.temp.cleanup()

    def test_python_flagship_is_not_approved(self):
        result=inspect_course(self.root,'COURSE-PY-ENG')
        self.assertFalse(result['training_content_go'])
        self.assertEqual(result['course_pdf_preview_pages'],397)
        self.assertEqual(result['decision'],'BLOCKED_PENDING_LIVE_RECOMPUTATION_AND_HUMAN_SIGNOFF')
        self.assertEqual(result['unmet_gate_a_criteria'],['A11','A14'])
        self.assertEqual(result['open_blocking_p0_p1_defects'],['DEF-004'])

    def test_snapshot_reports_tenor_of_reviews_without_fake_approval(self):
        result=inspect_course(self.root,'COURSE-PY-ENG')
        self.assertEqual(set(result['missing_human_review_types']),{'SME','EDITORIAL','LEARNER_PILOT','OWNER_ACCEPTANCE'})
        self.assertFalse(result['commercial_go'])
        self.assertFalse(result['academy_live_go'])

    def test_malicious_100_score_cannot_override_gate(self):
        f=self.base/'truth_matrix.json'; x=json.loads(f.read_text());x['COURSE-PY-ENG']['score']=100
        x['COURSE-PY-ENG']['state']='TRAINING_CONTENT_GO'; x['COURSE-PY-ENG']['criteria']={a:'MET' for a in GATE_A}
        f.write_text(json.dumps(x))
        result=inspect_course(self.root,'COURSE-PY-ENG')
        self.assertFalse(result['training_content_go'])
        self.assertEqual(result['decision'],'BLOCKED_PENDING_LIVE_RECOMPUTATION_AND_HUMAN_SIGNOFF')

    def test_unrecognized_criteria_fail_closed(self):
        f=self.base/'truth_matrix.json';x=json.loads(f.read_text());del x['COURSE-PY-ENG']['criteria']['A19'];f.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'mandatory'):inspect_course(self.root,'COURSE-PY-ENG')

    def test_multiple_final_pdf_records_fail_closed(self):
        f=self.base/'pdf_manifest.json';x=json.loads(f.read_text());x['course_editions'].append(x['course_editions'][0]);f.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'multiple course'):inspect_course(self.root,'COURSE-PY-ENG')

    def test_typoed_course_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown course'):inspect_course(self.root,'COURSE-UNKNOWN')

    def test_public_report_is_honest(self):
        text=to_markdown(inspect_course(self.root,'COURSE-PY-ENG'))
        self.assertIn('BLOCKED',text)
        self.assertIn('397',text)
        self.assertNotIn('Approved by OpenAI',text)

    def test_cli_exit_code_blocks_release(self):
        cli=ROOT/'scripts/enterprise/release_preflight.py'
        proc=subprocess.run([sys.executable,str(cli),'--root',str(self.root),'--course','COURSE-PY-ENG'],capture_output=True,text=True)
        self.assertEqual(proc.returncode,3)
        self.assertIn('BLOCKED',proc.stdout)

    def test_report_only_explicit_not_approval(self):
        cli=ROOT/'scripts/enterprise/release_preflight.py'
        proc=subprocess.run([sys.executable,str(cli),'--root',str(self.root),'--format','json','--report-only'],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0)
        data=json.loads(proc.stdout)
        self.assertFalse(data['training_content_go'])
        self.assertEqual(data['decision'],'BLOCKED_PENDING_LIVE_RECOMPUTATION_AND_HUMAN_SIGNOFF')

    def test_demo_pilot_has_real_submissions_and_no_certificate(self):
        path=self.root/'demo.db'
        output=run(path)
        self.assertEqual(output['before_grading']['graded'],0)
        self.assertEqual(output['after_grading']['graded'],3)
        self.assertTrue(output['after_grading']['meets_pilot_threshold'])
        self.assertEqual(output['after_grading']['credential'],'NOT_A_CERTIFICATE')
        self.assertFalse(output['after_grading']['course_completed'])
        self.assertGreater(output['audit']['events'],10)


if __name__ == '__main__':unittest.main()
