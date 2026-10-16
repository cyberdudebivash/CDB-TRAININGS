"""FND-M05 targeted curriculum contracts. Not full QA or human approval."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'courses/digital-foundations/modules/FND-M05'

def data(p):return yaml.safe_load(p.read_text(encoding='utf8'))

def test_source_free_integrity():
    source=data(MODULE/'source-map.yaml')
    assert source['source'] is None and source['mappings']==[]
    assert source['origin']=='NEW_ORIGINAL_FOUNDATIONS_CURRICULUM'

def test_lesson_depth_and_runnable_examples():
    content=(MODULE/'lesson.md').read_text(encoding='utf8')
    assert len(content.split())>=1800
    blocks=re.findall(r'```python run\n(.*?)\n```',content,re.S)
    assert len(blocks)>=4
    for block in blocks:exec(compile(block,'<fnd-m05-example>','exec'),{'__name__':'__main__'})

def test_guided_reference_suite():
    folder=MODULE/'lab-guided/checks'
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_support_metrics.py'],
                     cwd=folder,capture_output=True,text=True,timeout=45)
    assert p.returncode==0,p.stdout+p.stderr
    assert 'Ran 16 tests' in p.stderr

def test_independent_starter_intentionally_fails():
    folder=MODULE/'lab-independent/checks'
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_queue_report.py'],
                     cwd=folder,capture_output=True,text=True,timeout=30)
    assert p.returncode!=0
    assert 'Ran 10 tests' in p.stderr
    assert 'FND-M05 STARTER INCOMPLETE' in p.stderr
    assert 'ModuleNotFoundError' not in p.stderr and 'ImportError' not in p.stderr

def test_outcome_references_and_assessments():
    outcomes=data(MODULE/'outcomes.yaml')['outcomes']
    quiz=data(MODULE/'assessment/quiz.yaml')['items']
    rubric=data(MODULE/'assessment/rubric.yaml')['criteria']
    assert len(outcomes)==4 and len(quiz)==8 and len(rubric)==4
    assert {x['id'] for x in outcomes}=={x['outcome'] for x in quiz}
    assert {c['id'] for c in rubric}=={'C1','C2','C3','C4'}
    for outcome in outcomes:
        for ref in outcome['instruction']+outcome['practice']:
            filename,sep,anchor=ref.partition('#')
            assert sep
            text=(MODULE/filename).read_text(encoding='utf8')
            headings=re.findall(r'^#{1,6}\s+(.+)$',text,re.M)
            normalized=[re.sub(r'[^\w\- ]','',h.strip().lower()).replace(' ','-') for h in headings]
            assert anchor in normalized,ref

def test_student_preview_does_not_disclose_instructor_assets():
    cfg=data(ROOT/'courses/digital-foundations/student/FND-M05-student-edition.yaml')
    assert cfg['edition']=='student-preview' and cfg['module']=='FND-M05'
    assert len(cfg['include'])==4
    assert all('/solution/' not in p and '/instructor/' not in p and 'answer-key' not in p for p in cfg['include'])
    assert {Path(p).name for p in cfg['include']}=={'lesson.md','README.md','quiz.md'}
