"""FND-M04 content contracts; not a human review or complete course release."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
M = ROOT/'courses/digital-foundations/modules/FND-M04'


def load(path):return yaml.safe_load(path.read_text(encoding='utf-8'))


def test_new_original_source_provenance():
    data=load(M/'source-map.yaml')
    assert data['source'] is None and data['mappings']==[]
    assert data['origin']=='NEW_ORIGINAL_FOUNDATIONS_CURRICULUM'


def test_lesson_has_depth_and_executable_examples():
    text=(M/'lesson.md').read_text(encoding='utf-8')
    assert len(text.split())>=1800
    blocks=re.findall(r'```python run\n(.*?)\n```',text,re.S)
    assert len(blocks)>=4
    for block in blocks:
        exec(compile(block,'<FND-M04-example>','exec'),{'__name__':'__main__'})


def test_outcomes_assessments_and_anchors_resolve():
    outcomes=load(M/'outcomes.yaml')['outcomes']
    quiz=load(M/'assessment/quiz.yaml')['items']
    rub=load(M/'assessment/rubric.yaml')['criteria']
    assert len(outcomes)==4 and len(quiz)==8 and len(rub)==4
    assert {x['id'] for x in outcomes}=={q['outcome'] for q in quiz}
    assert {x['id'] for x in rub}=={'C1','C2','C3','C4'}
    for outcome in outcomes:
        for ref in outcome['instruction']+outcome['practice']:
            relative,separator,anchor=ref.partition('#')
            assert separator
            headings=re.findall(r'^#{1,6}\s+(.+)$',(M/relative).read_text(encoding='utf-8'),re.M)
            normalized=[re.sub(r'[^\w\- ]','',h.strip().lower()).replace(' ','-') for h in headings]
            assert anchor in normalized,ref


def test_guided_git_repositories_and_cleanup():
    folder=M/'lab-guided/checks'
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_git_workflow.py'],cwd=folder,capture_output=True,text=True,timeout=90)
    assert proc.returncode==0,proc.stdout+proc.stderr
    assert 'Ran 13 tests' in proc.stderr


def test_student_starter_fails_with_clear_directions():
    folder=M/'lab-independent/checks'
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_review_gate.py'],cwd=folder,capture_output=True,text=True,timeout=30)
    assert proc.returncode!=0
    assert 'Ran 12 tests' in proc.stderr
    assert 'FND-M04 STARTER INCOMPLETE' in proc.stderr
    assert 'ModuleNotFoundError' not in proc.stderr


def test_preview_is_student_only():
    config=load(ROOT/'courses/digital-foundations/student/FND-M04-student-edition.yaml')
    assert config['edition']=='student-preview' and config['module']=='FND-M04'
    assert len(config['include'])==4
    assert all('/instructor/' not in s and '/solution/' not in s for s in config['include'])
