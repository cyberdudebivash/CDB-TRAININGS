#!/usr/bin/env python3
"""Validate standalone training-starter labs. Not a Gate A course validator.

Runs synthetic fixture tests only. Missing Node or JDK reports NOT_EXECUTED (never PASS).
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = (
    ('digital-foundations', 'file-integrity'),
    ('python-automation', 'reconciliation'),
    ('ai-engineering', 'tool-approval'),
    ('osint-investigations', 'source-provenance'),
    ('gcp-data-engineering', 'batch-quality'),
    ('cybersecurity-tracks', 'auth-triage'),
)

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--strict', action='store_true', help='Fail when Node or JDK is missing instead of recording NOT_EXECUTED')
    ap.add_argument('--output', type=Path, help='Optional local JSON evidence path; do not commit reports as release approval')
    args = ap.parse_args()
    records = []
    for course, lab in PYTHON:
        path = ROOT / 'courses' / course / 'labs' / lab
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', str(path), '-p', 'test_lab.py', '-v']
        run = subprocess.run(cmd, cwd=path, capture_output=True, text=True, timeout=30)
        found = re.search(r'Ran (\d+) tests?', run.stdout + run.stderr)
        records.append({'course':course,'lab':lab,'runtime':'Python','status':'PASS' if run.returncode == 0 and found else 'FAIL',
                        'checks':int(found.group(1)) if found else 0,'exit':run.returncode,'tail':(run.stdout+run.stderr)[-400:]})
    js = ROOT / 'courses/frontend-engineering/labs/form-contract'
    node = shutil.which('node')
    if node:
        run = subprocess.run([node,'--test','test_lab.mjs'],cwd=js,capture_output=True,text=True,timeout=30)
        found = re.search(r'^# tests (\d+)$',run.stdout,re.M)
        records.append({'course':'frontend-engineering','lab':'form-contract','runtime':'Node.js',
                        'status':'PASS' if run.returncode == 0 and found else 'FAIL','checks':int(found.group(1)) if found else 0,
                        'exit':run.returncode,'tail':(run.stdout+run.stderr)[-400:]})
    else:
        records.append({'course':'frontend-engineering','lab':'form-contract','runtime':'Node.js','status':'NOT_EXECUTED','checks':0,'reason':'node not on PATH'})
    jpath = ROOT / 'courses/java-test-automation/labs/order-contract'
    java = shutil.which('java');javac = shutil.which('javac')
    if java and javac:
        with tempfile.TemporaryDirectory(prefix='cdb-java-check-') as out:
            compile = subprocess.run([javac,'-d',out,'OrderCalculator.java','OrderCalculatorTest.java'],cwd=jpath,capture_output=True,text=True,timeout=60)
            run = subprocess.run([java,'-cp',out,'OrderCalculatorTest'],cwd=jpath,capture_output=True,text=True,timeout=30) if compile.returncode==0 else compile
            m = re.search(r'PASS: (\d+) Java contract checks',run.stdout)
            records.append({'course':'java-test-automation','lab':'order-contract','runtime':'JDK',
                            'status':'PASS' if compile.returncode==0 and run.returncode==0 and m else 'FAIL',
                            'checks':int(m.group(1)) if m else 0,'exit':run.returncode,'tail':(run.stdout+run.stderr)[-400:]})
    else:
        records.append({'course':'java-test-automation','lab':'order-contract','runtime':'JDK','status':'NOT_EXECUTED','checks':0,'reason':'java/javac not on PATH'})
    statuses = {s:sum(x['status']==s for x in records) for s in ('PASS','FAIL','NOT_EXECUTED')}
    result = {'type':'STARTER_LAB_EVIDENCE_ONLY','portfolio_gate_a':'NOT_ASSESSED',
              'status_counts':statuses,'checks_executed':sum(x['checks'] for x in records if x['status']=='PASS'),
              'results':records}
    print(json.dumps(result,indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 1 if statuses['FAIL'] or (args.strict and statuses['NOT_EXECUTED']) else 0

if __name__=='__main__':
    raise SystemExit(main())
