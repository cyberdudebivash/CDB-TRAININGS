"""FND-M03 targeted content-contract checks; these are not Academy release criteria."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT/'courses/digital-foundations/modules/FND-M03'


def load(path):return yaml.safe_load(path.read_text(encoding='utf-8'))


def test_provenance_and_substantive_lesson():
    source=load(MOD/'source-map.yaml')
    assert source['source'] is None and source['mappings']==[]
    assert source['origin']=='NEW_ORIGINAL_FOUNDATIONS_CURRICULUM'
    lesson=(MOD/'lesson.md').read_text(encoding='utf-8')
    assert len(lesson.split())>=1800
    assert 'no DNS lookup' in lesson and 'no TLS handshake' in lesson


def test_runnable_lesson_code_blocks():
    text=(MOD/'lesson.md').read_text(encoding='utf-8')
    blocks=re.findall(r'```python run\n(.*?)\n```',text,re.S)
    assert len(blocks)>=4
    for block in blocks:
        exec(compile(block,'<FND-M03-example>','exec'),{'__name__':'__main__'})


def test_public_outcome_links_and_quiz_contract():
    outcomes=load(MOD/'outcomes.yaml')['outcomes']
    quiz=load(MOD/'assessment/quiz.yaml')['items']
    criteria=load(MOD/'assessment/rubric.yaml')['criteria']
    assert len(outcomes)==4 and len(quiz)==8 and len(criteria)==4
    assert {x['id'] for x in outcomes}=={x['outcome'] for x in quiz}
    assert {c['id'] for c in criteria}=={'C1','C2','C3','C4'}
    for outcome in outcomes:
        for ref in outcome['instruction']+outcome['practice']:
            filename,sep,anchor=ref.partition('#')
            assert sep
            headings=re.findall(r'^#{1,6}\s+(.+)$',(MOD/filename).read_text(encoding='utf-8'),re.M)
            normalized=[re.sub(r'[^\w\- ]','',h.strip().lower()).replace(' ','-') for h in headings]
            assert anchor in normalized, ref


def test_guided_loopback_contracts():
    folder=MOD/'lab-guided/checks'
    res=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_http_trace.py'],cwd=folder,text=True,capture_output=True,timeout=45)
    assert res.returncode==0, res.stdout+res.stderr
    assert 'Ran 12 tests' in res.stderr


def test_independent_starter_fails_with_actionable_messages():
    folder=MOD/'lab-independent/checks'
    res=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_trace_model.py'],cwd=folder,text=True,capture_output=True,timeout=15)
    assert res.returncode!=0
    assert 'Ran 12 tests' in res.stderr
    assert 'FND-M03 STARTER INCOMPLETE' in res.stderr
    assert 'ModuleNotFoundError' not in res.stderr


def test_preview_excludes_protected_assets():
    data=load(ROOT/'courses/digital-foundations/student/FND-M03-student-edition.yaml')
    assert data['edition']=='student-preview' and data['module']=='FND-M03'
    assert len(data['include'])==4
    assert all('/instructor/' not in x and '/solution/' not in x and 'answer-key' not in x for x in data['include'])
