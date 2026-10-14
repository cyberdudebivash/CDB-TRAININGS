#!/usr/bin/env python3
"""Executed API-compatibility probes: does a pattern taught in a legacy source still work on the current release?

Each probe installs the *snapshot* version of a package (docs/research/data/registry_snapshot_<cutoff>.json) into an
isolated virtual environment outside the repository, runs a tiny program and records what actually happened
(imports, missing attributes, raised exceptions, warnings).  The results are EXECUTED evidence for the page-level
audit: a statement such as "find_element_by_id no longer exists" is only made when this script observed it.

Nothing here contacts any service other than the package registries used by pip/npm, uses no credentials and writes
only under --work-dir and the results file.

Usage:
  python scripts/research/api_probes.py --cutoff 2026-10-14 --work-dir /tmp/probe-work
  python scripts/research/api_probes.py --only selenium,openai
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "research" / "data"

# --------------------------------------------------------------------------------------------- probe definitions
PY = "python"
NODE = "node"
PROBES: list[dict] = [
    {"id": "selenium-python-legacy-locators", "runtime": PY, "pkgs": ["selenium"], "taught_pattern": "driver.find_element_by_id(...) / webdriver.Chrome(executable_path=...)",
     "code": """
        import inspect, json
        from selenium import webdriver
        out = {"has_find_element_by_id": hasattr(webdriver.Chrome, "find_element_by_id"),
               "has_find_elements_by_xpath": hasattr(webdriver.Chrome, "find_elements_by_xpath"),
               "chrome_init_params": list(inspect.signature(webdriver.Chrome.__init__).parameters)}
        print(json.dumps(out))
     """},
    {"id": "openai-legacy-module-api", "runtime": PY, "pkgs": ["openai"], "taught_pattern": "openai.ChatCompletion.create(...) / openai.api_key = ...",
     "code": """
        import json, openai
        out = {"version": openai.__version__}
        for name, call in (("ChatCompletion.create", lambda: openai.ChatCompletion.create(model="m", messages=[])),
                           ("Completion.create", lambda: openai.Completion.create(model="m", prompt="x")),
                           ("Embedding.create", lambda: openai.Embedding.create(model="m", input="x"))):
            try:
                call()
                out[name] = "call returned"
            except Exception as e:
                out[name] = f"{type(e).__name__}: {str(e)[:110]}"
        out["has_client_class"] = hasattr(openai, "OpenAI")
        print(json.dumps(out))
     """},
    {"id": "langchain-legacy-imports", "runtime": PY, "pkgs": ["langchain"], "taught_pattern": "from langchain.llms / chains / chat_models / vectorstores / embeddings imports",
     "code": """
        import importlib, json
        targets = ["langchain.chains:LLMChain", "langchain.chains:ConversationalRetrievalChain", "langchain.chains:RetrievalQA", "langchain.llms:OpenAI",
                   "langchain.chat_models:ChatOpenAI", "langchain.embeddings:OpenAIEmbeddings", "langchain.vectorstores:FAISS",
                   "langchain.text_splitter:RecursiveCharacterTextSplitter", "langchain.agents:AgentExecutor", "langchain.agents:initialize_agent",
                   "langchain.memory:ConversationBufferMemory", "langchain.prompts:PromptTemplate", "langchain.agents:create_agent"]
        res = {}
        for t in targets:
            mod, attr = t.split(":")
            try:
                m = importlib.import_module(mod)
                getattr(m, attr)
                res[t] = "ok"
            except Exception as e:
                res[t] = f"{type(e).__name__}: {str(e)[:90]}"
        print(json.dumps(res))
     """},
    {"id": "pytest-removed-apis", "runtime": PY, "pkgs": ["pytest"], "taught_pattern": "@pytest.yield_fixture, pytest.warns(None), nose-style setup",
     "code": """
        import json, pytest
        out = {"version": pytest.__version__, "has_yield_fixture": hasattr(pytest, "yield_fixture"), "has_fixture": hasattr(pytest, "fixture"), "has_importorskip": hasattr(pytest, "importorskip")}
        try:
            with pytest.warns(None):
                pass
            out["warns_none"] = "accepted"
        except Exception as e:
            out["warns_none"] = f"{type(e).__name__}: {str(e)[:100]}"
        print(json.dumps(out))
     """},
    {"id": "cpython-removed-stdlib", "runtime": PY, "pkgs": [], "taught_pattern": "import distutils/imp/asyncore/cgi/telnetlib; datetime.utcnow(); asyncio.get_event_loop()",
     "code": """
        import importlib, json, sys, warnings, datetime, asyncio
        res = {"python": sys.version.split()[0]}
        for name in ("distutils", "imp", "asyncore", "asynchat", "smtpd", "cgi", "cgitb", "telnetlib", "pipes", "crypt", "nntplib", "lib2to3", "pkg_resources"):
            try:
                importlib.import_module(name); res[name] = "importable"
            except Exception as e:
                res[name] = type(e).__name__
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            datetime.datetime.utcnow()
            res["utcnow_warning"] = [x.category.__name__ for x in w]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                asyncio.get_event_loop(); res["get_event_loop"] = "returned a loop"
            except Exception as e:
                res["get_event_loop"] = f"{type(e).__name__}: {str(e)[:80]}"
            res["get_event_loop_warning"] = [x.category.__name__ for x in w]
        import unittest
        res["unittest_makeSuite"] = hasattr(unittest, "makeSuite")
        print(json.dumps(res))
     """},
    {"id": "pydantic-v1-style-api", "runtime": PY, "pkgs": ["pydantic"], "taught_pattern": "@validator, class Config, .dict(), .json(), parse_obj",
     "code": """
        import json, warnings
        import pydantic
        from pydantic import BaseModel
        res = {"version": pydantic.VERSION}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            class M(BaseModel):
                x: int
                class Config:
                    anystr_strip_whitespace = True
            m = M(x=1)
            m.dict(); m.json(); M.parse_obj({"x": 2})
            res["warnings"] = sorted({x.category.__name__ for x in w})
        try:
            from pydantic import validator
            res["validator_import"] = "present (deprecated)"
        except Exception as e:
            res["validator_import"] = type(e).__name__
        print(json.dumps(res))
     """},
    {"id": "fastapi-on-event", "runtime": PY, "pkgs": ["fastapi"], "taught_pattern": "@app.on_event('startup') / @app.on_event('shutdown')",
     "code": """
        import json, warnings
        from fastapi import FastAPI
        res = {}
        app = FastAPI()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                @app.on_event("startup")
                async def start():
                    pass
                res["on_event"] = "accepted"
            except Exception as e:
                res["on_event"] = f"{type(e).__name__}: {str(e)[:100]}"
            res["warnings"] = sorted({x.category.__name__ for x in w})
        res["has_lifespan_param"] = "lifespan" in FastAPI.__init__.__code__.co_varnames
        print(json.dumps(res))
     """},
    {"id": "sqlalchemy-legacy-execute", "runtime": PY, "pkgs": ["sqlalchemy"], "taught_pattern": "engine.execute(...); from sqlalchemy.ext.declarative import declarative_base",
     "code": """
        import json, warnings
        import sqlalchemy
        from sqlalchemy import create_engine, text
        res = {"version": sqlalchemy.__version__}
        e = create_engine("sqlite://")
        res["engine_execute"] = hasattr(e, "execute")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                from sqlalchemy.ext.declarative import declarative_base
                declarative_base()
                res["ext_declarative_base"] = "works"
            except Exception as ex:
                res["ext_declarative_base"] = f"{type(ex).__name__}: {str(ex)[:100]}"
            res["warnings"] = sorted({x.category.__name__ for x in w})
        with e.connect() as c:
            res["text_query"] = list(c.execute(text("select 1")))[0][0]
        try:
            with e.connect() as c:
                c.execute("select 1")
            res["raw_string_execute"] = "accepted"
        except Exception as ex:
            res["raw_string_execute"] = f"{type(ex).__name__}"
        print(json.dumps(res))
     """},
    {"id": "pandas-removed-apis", "runtime": PY, "pkgs": ["pandas", "numpy"], "taught_pattern": "df.append, Series.iteritems, chained assignment, np.float_/np.bool8/np.product",
     "code": """
        import json, warnings
        import pandas as pd, numpy as np
        res = {"pandas": pd.__version__, "numpy": np.__version__}
        df = pd.DataFrame({"a": [1, 2]})
        res["DataFrame.append"] = hasattr(df, "append")
        res["Series.iteritems"] = hasattr(df["a"], "iteritems")
        res["DataFrame.applymap"] = hasattr(df, "applymap")
        before = df["a"].tolist()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            df["a"][0] = 99
            res["warnings_on_chained_assignment"] = sorted({x.category.__name__ for x in w})
        res["chained_assignment_changed_frame"] = df["a"].tolist() != before
        for n in ("float_", "bool8", "product", "cumproduct", "in1d", "row_stack", "unicode_", "string_", "Inf", "NaN"):
            res["np." + n] = hasattr(np, n)
        print(json.dumps(res))
     """},
    {"id": "pyyaml-unsafe-load", "runtime": PY, "pkgs": ["pyyaml"], "taught_pattern": "yaml.load(f) without Loader",
     "code": """
        import io, json, yaml
        res = {"version": yaml.__version__}
        try:
            yaml.load(io.StringIO("a: 1"))
            res["yaml.load_no_loader"] = "accepted"
        except Exception as e:
            res["yaml.load_no_loader"] = f"{type(e).__name__}: {str(e)[:100]}"
        print(json.dumps(res))
     """},
    {"id": "pyjwt-decode-algorithms", "runtime": PY, "pkgs": ["pyjwt"], "taught_pattern": "jwt.decode(token, key) without algorithms; HS256 shared secret in source",
     "code": """
        import json, jwt
        res = {"version": jwt.__version__}
        tok = jwt.encode({"sub": "u"}, "k" * 32, algorithm="HS256")
        res["encode_returns"] = type(tok).__name__
        try:
            jwt.decode(tok, "k" * 32)
            res["decode_without_algorithms"] = "accepted"
        except Exception as e:
            res["decode_without_algorithms"] = f"{type(e).__name__}: {str(e)[:100]}"
        print(json.dumps(res))
     """},
    {"id": "flask-removed-apis", "runtime": PY, "pkgs": ["flask"], "taught_pattern": "@app.before_first_request, flask.json.JSONEncoder, from flask import escape",
     "code": """
        import json
        import flask
        from flask import Flask
        res = {"version": flask.__version__ if hasattr(flask, "__version__") else "n/a"}
        res["before_first_request"] = hasattr(Flask, "before_first_request")
        res["flask.json.JSONEncoder"] = hasattr(flask.json, "JSONEncoder")
        res["flask.escape"] = hasattr(flask, "escape")
        res["flask.Markup"] = hasattr(flask, "Markup")
        print(json.dumps(res))
     """},
    {"id": "django-removed-apis", "runtime": PY, "pkgs": ["django"], "taught_pattern": "from django.conf.urls import url; force_text",
     "code": """
        import importlib, json, django
        res = {"version": django.get_version()}
        for t in ("django.conf.urls:url", "django.utils.encoding:force_text", "django.utils.translation:ugettext", "django.urls:path"):
            mod, attr = t.split(":")
            try:
                getattr(importlib.import_module(mod), attr); res[t] = "ok"
            except Exception as e:
                res[t] = type(e).__name__
        print(json.dumps(res))
     """},
    {"id": "paramiko-host-key-policy", "runtime": PY, "pkgs": ["paramiko"], "taught_pattern": "set_missing_host_key_policy(AutoAddPolicy()); DSSKey",
     "code": """
        import json, paramiko
        res = {"version": paramiko.__version__, "AutoAddPolicy": hasattr(paramiko, "AutoAddPolicy"), "RejectPolicy": hasattr(paramiko, "RejectPolicy"), "DSSKey": hasattr(paramiko, "DSSKey")}
        print(json.dumps(res))
     """},
    {"id": "bs4-camelcase-methods", "runtime": PY, "pkgs": ["beautifulsoup4"], "taught_pattern": "soup.findAll(...) / find_all",
     "code": """
        import json, warnings
        import bs4
        from bs4 import BeautifulSoup
        res = {"version": bs4.__version__}
        s = BeautifulSoup("<a>1</a>", "html.parser")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res["findAll_exists"] = hasattr(s, "findAll")
            if res["findAll_exists"]:
                s.findAll("a")
            res["warnings"] = sorted({x.category.__name__ for x in w})
        print(json.dumps(res))
     """},
    {"id": "react-dom-legacy-render", "runtime": NODE, "pkgs": ["react", "react-dom"], "taught_pattern": "ReactDOM.render(<App/>, root); componentWillMount",
     "code": """
        const rd = require('react-dom'); const rdc = require('react-dom/client'); const React = require('react');
        const out = {react: React.version, 'ReactDOM.render': typeof rd.render, 'ReactDOM.hydrate': typeof rd.hydrate, 'ReactDOM.unmountComponentAtNode': typeof rd.unmountComponentAtNode,
                     'react-dom/client createRoot': typeof rdc.createRoot, 'React.createClass': typeof React.createClass, 'PropTypes_in_react': typeof React.PropTypes};
        console.log(JSON.stringify(out));
     """},
    {"id": "npm-deprecation-flags", "runtime": "npm-view", "pkgs": ["create-react-app", "react-scripts", "node-sass", "enzyme", "request", "moment", "tslint", "protractor"], "taught_pattern": "tooling the legacy playbook may recommend",
     "code": ""},
    {"id": "eslint-eslintrc-removed", "runtime": "eslint", "pkgs": ["eslint"], "taught_pattern": ".eslintrc.json / .eslintrc.js configuration",
     "code": ""},
    {"id": "setuptools-setup-py-commands", "runtime": "setuptools", "pkgs": ["setuptools"], "taught_pattern": "python setup.py install / sdist / bdist_wheel / test",
     "code": ""},
    {"id": "typescript-native-compiler", "runtime": "tsc", "pkgs": ["typescript"], "taught_pattern": "tsc version and flags",
     "code": ""},
]


# --------------------------------------------------------------------------------------------- helpers
def run(cmd, cwd=None, timeout=900, env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def snapshot_versions(cutoff: str) -> dict[str, str]:
    snap = json.loads((OUT_DIR / f"registry_snapshot_{cutoff}.json").read_text(encoding="utf-8"))
    out = {}
    for r in snap["records"]:
        if r.get("status") == "OK" and r["kind"] in ("pypi", "npm") and r.get("current"):
            out.setdefault(r["package"].lower(), r["current"]["version"])
    return out


def pin(pkg: str, versions: dict[str, str], npm: bool = False) -> str:
    v = versions.get(pkg.lower())
    if not v:
        return pkg
    return f"{pkg}@{v}" if npm else f"{pkg}=={v}"


def run_python_probe(p: dict, work: Path, versions: dict[str, str]) -> dict:
    venv = work / f"venv-{p['id']}"
    if venv.exists():
        shutil.rmtree(venv)
    rc, _, err = run([sys.executable, "-m", "venv", str(venv)])
    if rc:
        return {"status": "ERROR", "error": err[-300:]}
    py = venv / "bin" / "python"
    pins = [pin(x, versions) for x in p["pkgs"]]
    if pins:
        rc, out, err = run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pins], timeout=1500)
        if rc:
            return {"status": "INSTALL_FAILED", "pins": pins, "error": err[-400:]}
    code = textwrap.dedent(p["code"])
    rc, out, err = run([str(py), "-W", "default", "-c", code], timeout=300)
    installed = {}
    if pins:
        _, freeze, _ = run([str(py), "-m", "pip", "freeze"])
        installed = {ln.split("==")[0].lower(): ln.split("==")[1] for ln in freeze.splitlines() if "==" in ln and ln.split("==")[0].lower() in {x.lower() for x in p["pkgs"]}}
    result = {"status": "OK" if rc == 0 else "NONZERO_EXIT", "pins": pins, "installed": installed, "python": run([str(py), "--version"])[1].strip() or run([str(py), "--version"])[2].strip()}
    try:
        result["observed"] = json.loads(out.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        result["stdout"] = out[-600:]
    if rc != 0:
        result["stderr"] = err[-600:]
    shutil.rmtree(venv, ignore_errors=True)
    return result


def run_node_probe(p: dict, work: Path, versions: dict[str, str]) -> dict:
    d = work / f"node-{p['id']}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "package.json").write_text('{"name":"probe","version":"0.0.0","private":true}', encoding="utf-8")
    pins = [pin(x, versions, npm=True) for x in p["pkgs"]]
    rc, _, err = run(["npm", "install", "--no-audit", "--no-fund", "--silent", "--legacy-peer-deps", *pins], cwd=d, timeout=900)
    if rc:
        return {"status": "INSTALL_FAILED", "pins": pins, "error": err[-400:]}
    (d / "probe.js").write_text(textwrap.dedent(p["code"]), encoding="utf-8")
    rc, out, err = run(["node", "probe.js"], cwd=d, timeout=120)
    res = {"status": "OK" if rc == 0 else "NONZERO_EXIT", "pins": pins, "node": run(["node", "--version"])[1].strip()}
    try:
        res["observed"] = json.loads(out.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        res["stdout"] = out[-500:]
    if rc:
        res["stderr"] = err[-500:]
    shutil.rmtree(d, ignore_errors=True)
    return res


def run_npm_view(p: dict, work: Path, versions: dict[str, str]) -> dict:
    res = {}
    for pkg in p["pkgs"]:
        rc, out, err = run(["npm", "view", f"{pkg}@latest", "version", "deprecated", "--json"], timeout=120)
        try:
            data = json.loads(out) if out.strip() else {}
        except Exception:  # noqa: BLE001
            data = {"raw": out[-200:]}
        if isinstance(data, str):  # npm prints a bare string when only one requested field exists
            data = {"version": data}
        ver = data.get("version") if isinstance(data, dict) else None
        dep = data.get("deprecated") if isinstance(data, dict) else None
        if rc and not ver:
            ver = "NOT_FOUND_OR_ERROR"
        res[pkg] = {"latest_version": ver, "deprecated": (dep[:240] if isinstance(dep, str) else dep)}
    return {"status": "OK", "observed": res, "node": run(["node", "--version"])[1].strip()}


def run_eslint(p: dict, work: Path, versions: dict[str, str]) -> dict:
    d = work / "node-eslint"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "package.json").write_text('{"name":"probe","private":true}', encoding="utf-8")
    pins = [pin("eslint", versions, npm=True)]
    rc, _, err = run(["npm", "install", "--no-audit", "--no-fund", "--silent", *pins], cwd=d, timeout=900)
    if rc:
        return {"status": "INSTALL_FAILED", "error": err[-300:]}
    (d / ".eslintrc.json").write_text('{"rules": {"no-unused-vars": "error"}}', encoding="utf-8")
    (d / "a.js").write_text("const x = 1;\n", encoding="utf-8")
    rc1, out1, err1 = run(["npx", "--no-install", "eslint", "a.js"], cwd=d, timeout=120)
    (d / ".eslintrc.json").unlink()
    (d / "eslint.config.js").write_text("module.exports = [{rules: {'no-unused-vars': 'error'}}];\n", encoding="utf-8")
    rc2, out2, err2 = run(["npx", "--no-install", "eslint", "a.js"], cwd=d, timeout=120)
    res = {"status": "OK", "pins": pins,
           "with_only_eslintrc": {"exit": rc1, "output": (out1 + err1).strip()[:300]},
           "with_flat_config": {"exit": rc2, "output": (out2 + err2).strip()[:300]}}
    shutil.rmtree(d, ignore_errors=True)
    return res


def run_tsc(p: dict, work: Path, versions: dict[str, str]) -> dict:
    d = work / "node-tsc"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "package.json").write_text('{"name":"probe","private":true}', encoding="utf-8")
    pins = [pin("typescript", versions, npm=True)]
    rc, _, err = run(["npm", "install", "--no-audit", "--no-fund", "--silent", *pins], cwd=d, timeout=900)
    if rc:
        return {"status": "INSTALL_FAILED", "error": err[-300:]}
    rc, out, err = run(["npx", "--no-install", "tsc", "--version"], cwd=d)
    (d / "a.ts").write_text("const x: number = 'a';\n", encoding="utf-8")
    rc2, out2, err2 = run(["npx", "--no-install", "tsc", "--noEmit", "a.ts"], cwd=d)
    res = {"status": "OK", "pins": pins, "tsc_version": out.strip(), "type_error_detected": rc2 != 0, "message": (out2 + err2).strip()[:200]}
    shutil.rmtree(d, ignore_errors=True)
    return res


def run_setuptools(p: dict, work: Path, versions: dict[str, str]) -> dict:
    d = work / "setuptools-probe"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    rc, _, err = run([sys.executable, "-m", "venv", str(d / "venv")])
    py = d / "venv" / "bin" / "python"
    pins = [pin("setuptools", versions)]
    rc, _, err = run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pins], timeout=600)
    if rc:
        return {"status": "INSTALL_FAILED", "error": err[-300:]}
    proj = d / "proj"
    proj.mkdir()
    (proj / "setup.py").write_text("from setuptools import setup\nsetup(name='demo', version='0.1', py_modules=['demo'])\n", encoding="utf-8")
    (proj / "demo.py").write_text("x = 1\n", encoding="utf-8")
    obs = {}
    for cmd in ("sdist", "bdist_wheel", "install", "test"):
        rc, out, err = run([str(py), "setup.py", cmd], cwd=proj, timeout=300)
        obs[cmd] = {"exit": rc, "last_lines": (out + err).strip().splitlines()[-3:]}
    obs["setuptools_version"] = run([str(py), "-c", "import setuptools; print(setuptools.__version__)"])[1].strip()
    shutil.rmtree(d, ignore_errors=True)
    return {"status": "OK", "pins": pins, "observed": obs, "python": sys.version.split()[0]}


RUNNERS = {"setuptools": run_setuptools, PY: run_python_probe, NODE: run_node_probe, "npm-view": run_npm_view, "eslint": run_eslint, "tsc": run_tsc}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cutoff", default="2026-10-14")
    ap.add_argument("--work-dir", required=True, help="scratch directory OUTSIDE the repository for virtual environments")
    ap.add_argument("--only", help="comma-separated probe ids")
    ap.add_argument("--merge", action="store_true", help="with --only: update just those probes in the existing results file")
    a = ap.parse_args()
    work = Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    if ROOT in work.resolve().parents or work.resolve() == ROOT:
        raise SystemExit("--work-dir must be outside the repository")
    versions = snapshot_versions(a.cutoff)
    only = set(a.only.split(",")) if a.only else None
    out_path = OUT_DIR / f"api_probes_{a.cutoff}.json"
    results = []
    for p in PROBES:
        if only and p["id"] not in only:
            continue
        started = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            r = RUNNERS[p["runtime"]](p, work, versions)
        except Exception as e:  # noqa: BLE001
            r = {"status": "ERROR", "error": f"{type(e).__name__}: {str(e)[:300]}"}
        r.update({"id": p["id"], "taught_pattern": p["taught_pattern"], "runtime": p["runtime"], "executed_utc": started})
        results.append(r)
        print(f"{r['status']:15} {p['id']}")
    if a.merge and out_path.exists() and only:
        old = json.loads(out_path.read_text(encoding="utf-8"))
        keep = [x for x in old["probes"] if x["id"] not in only]
        results = keep + results
    doc = {"cutoff_date": a.cutoff, "host": {"platform": platform.platform(), "python": sys.version.split()[0]}, "script": "scripts/research/api_probes.py",
           "note": "Observations are facts about the installed releases on the execution date, not about historical behaviour.", "probes": sorted(results, key=lambda x: x["id"])}
    out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
