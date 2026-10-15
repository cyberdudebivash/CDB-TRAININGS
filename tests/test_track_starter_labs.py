"""Executable narrow regression checks; no claim of completed course validation."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
COURSES = [
 ('digital-foundations','file-integrity'),('python-automation','reconciliation'),
 ('ai-engineering','tool-approval'),('osint-investigations','source-provenance'),
 ('gcp-data-engineering','batch-quality'),('cybersecurity-tracks','auth-triage'),
 ('frontend-engineering','form-contract'),('java-test-automation','order-contract')
]

@pytest.mark.parametrize('slug,lab',COURSES)
def test_course_directory_has_substantive_lab(slug:str,lab:str):
    course=ROOT/'courses'/slug
    course_doc=(course/'README.md').read_text(encoding='utf-8')
    lab_doc=(course/'labs'/lab/'README.md').read_text(encoding='utf-8')
    assert len(course_doc.split())>=130,slug
    assert len(lab_doc.split())>=180,lab
    assert 'NOT' in course_doc and 'Customer-operations scenario' in lab_doc

@pytest.mark.parametrize('slug,lab',COURSES[:6])
def test_python_starter_lab_contract_passes(slug:str,lab:str):
    folder=ROOT/'courses'/slug/'labs'/lab
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_lab.py'],
                     cwd=folder,capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stdout+p.stderr
    assert 'Ran ' in p.stderr

def test_java_and_node_are_optional_for_general_pytest_runner():
    script=ROOT/'scripts/validation/run_starter_labs.py'
    assert script.is_file()
    assert 'NOT_EXECUTED' in script.read_text(encoding='utf-8')
