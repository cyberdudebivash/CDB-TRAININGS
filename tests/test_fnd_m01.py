"""FND-M01 implementation regression; not a release gate or learner pilot."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "courses/digital-foundations/modules/FND-M01"

def test_original_source_declaration_is_honest():
    s=yaml.safe_load((M/"source-map.yaml").read_text(encoding="utf8"))
    assert s["source"] is None
    assert s["mappings"]==[]
    assert s["origin"]=="NEW_ORIGINAL_FOUNDATIONS_CURRICULUM"

def test_lesson_has_substantive_content_and_executable_examples():
    text=(M/"lesson.md").read_text(encoding="utf8")
    assert len(re.findall(r"\w+",text))>=1500
    blocks=re.findall(r"```python run\n(.*?)```",text,re.S)
    assert len(blocks)>=3
    for block in blocks:exec(compile(block,"example","exec"),{"__name__":"__main__"})

def test_guided_regressions():
    folder=ROOT/"courses/digital-foundations/labs/file-integrity"
    p=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(folder),"-p","test_lab.py"],
                     capture_output=True,text=True,cwd=folder,timeout=30)
    assert p.returncode==0,p.stderr+p.stdout
    assert "Ran 5 tests" in p.stderr

def test_independent_starter_fails_as_intended():
    folder=M/"lab-independent/checks"
    p=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(folder),"-p","test_lab.py"],
                     capture_output=True,text=True,cwd=folder,timeout=30)
    assert p.returncode!=0 and "Ran 7 tests" in p.stderr,p.stderr
    assert "NotImplementedError" in p.stderr
    assert "ModuleNotFoundError" not in p.stderr and "ImportError" not in p.stderr

def test_quiz_outcomes_and_private_material_exclusion():
    outs=yaml.safe_load((M/"outcomes.yaml").read_text(encoding="utf8"))["outcomes"]
    quiz=yaml.safe_load((M/"assessment/quiz.yaml").read_text(encoding="utf8"))["items"]
    assert len(outs)==4 and len(quiz)==8
    assert {q["outcome"] for q in quiz}=={o["id"] for o in outs}
    assert all(set(q)=={"id","outcome","stem","options"} for q in quiz)
