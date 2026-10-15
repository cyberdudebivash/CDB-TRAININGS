#!/usr/bin/env python3
"""The release gate of the PY-M11 capstone: does the project in --project meet the definition of done? Run it from the folder lab-guided/.

    python tools/gate.py --part A             # part A (the walking skeleton): gates G01-G07 and G09-G12 on ../lab-independent/project
    python tools/gate.py                      # part B (the finished application): all thirteen gates
    python tools/gate.py --project ../mine --only G03,G05
    python tools/gate.py --json result.json

It builds the project in a scratch copy, installs the wheel into a scratch virtual environment and runs your tools with its own settings (strict types, the lint rules of the specification, branch
coverage), so a weaker setting in your pyproject.toml cannot hide a problem. Everything is offline. Exit status 0 only when every gate passes. Passing the gate is necessary for the capstone, not
sufficient: the instructors' suite tests the behaviour of your application much harder than these gates do.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, IO, cast
from pathlib import Path

import yaml

LAB = Path(__file__).resolve().parent.parent                          # the folder lab-guided/
PROJECT = LAB.parent / "lab-independent" / "project"                    # your project: created in part A, finished in part B
PY = sys.executable
TOOLS = Path(__file__).resolve().parent
SHA = re.compile(r"[0-9a-f]{40}")
IGNORED = shutil.ignore_patterns("build", "dist", "*.egg-info", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".coverage*", ".venv", ".git", "*.pyc")


@dataclass
class Result:
    gate: str
    title: str
    ok: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class Context:
    project: Path
    scratch: Path
    part: str = "B"
    work: Path = field(init=False)
    wheel: Path | None = None
    sdist: Path | None = None
    venv_python: Path | None = None

    def __post_init__(self) -> None:
        self.work = self.scratch / "project"
        shutil.copytree(self.project, self.work, ignore=IGNORED)


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 600, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    full = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env or {}))
    return subprocess.run(args, cwd=cwd, env=full, capture_output=True, timeout=timeout, input=stdin, check=False)  # noqa: S603 - arguments are built from fixed lists and paths


def tail(done: subprocess.CompletedProcess[bytes], lines: int = 6) -> list[str]:
    text = (done.stdout + b"\n" + done.stderr).decode("utf-8", "replace").strip().splitlines()
    return text[-lines:]


def pyproject(ctx: Context) -> dict[str, object]:
    return tomllib.loads((ctx.work / "pyproject.toml").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------------------------------------------------------ the gates
def g01_layout(ctx: Context, r: Result) -> None:
    need = ["pyproject.toml", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore", "requirements.lock", "scripts/check.py", "src/authwatch/__init__.py", "src/authwatch/__main__.py",
            "src/authwatch/py.typed"]
    missing = [n for n in need if not (ctx.work / n).is_file()]
    tests = sorted((ctx.work / "tests").glob("test_*.py")) if (ctx.work / "tests").is_dir() else []
    workflows = sorted((ctx.work / ".github" / "workflows").glob("*.y*ml")) if (ctx.work / ".github" / "workflows").is_dir() else []
    r.notes += [f"missing: {n}" for n in missing]
    if not tests:
        r.notes.append("no tests/test_*.py")
    if not workflows:
        r.notes.append("no .github/workflows/*.yml")
    r.ok = not (missing or not tests or not workflows)


def g02_metadata(ctx: Context, r: Result) -> None:
    try:
        data = pyproject(ctx)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        r.notes.append(f"pyproject.toml unusable: {type(exc).__name__}")
        return
    project = data.get("project")
    problems: list[str] = []
    if not isinstance(project, dict):
        r.notes.append("no [project] table")
        return
    if project.get("name") != "authwatch":
        problems.append("project.name must be authwatch")
    if not str(project.get("requires-python", "")).replace(" ", "").startswith(">=3.11"):
        problems.append("requires-python must start with '>=3.11'")
    scripts = project.get("scripts")
    if not isinstance(scripts, dict) or "authwatch" not in scripts:
        problems.append("[project.scripts] must define the authwatch command")
    deps = [str(d).lower().replace(" ", "") for d in project.get("dependencies", [])]
    if not any(d.startswith("pyyaml") for d in deps):
        problems.append("dependencies must name PyYAML (rules files)")
    if not project.get("readme"):
        problems.append("project.readme is missing")
    if not (project.get("license") or project.get("license-files")):
        problems.append("a license expression or license-files is required")
    if "dynamic" in project and "version" in project["dynamic"]:
        tool = data.get("tool", {})
        if not isinstance(tool, dict) or "setuptools" not in tool and "hatch" not in tool:
            problems.append("a dynamic version needs a tool section that says where it comes from")
    elif "version" not in project:
        problems.append("the version must be static or dynamic, not absent")
    r.notes += problems
    r.ok = not problems


def g03_build(ctx: Context, r: Result) -> None:
    out = ctx.scratch / "dist"
    done = run([PY, "-m", "build", "--no-isolation", "--outdir", str(out), str(ctx.work)], ctx.scratch)
    wheels, sdists = sorted(out.glob("*.whl")), sorted(out.glob("*.tar.gz"))
    if done.returncode != 0 or len(wheels) != 1 or len(sdists) != 1:
        r.notes += ["build failed or did not produce exactly one wheel and one sdist", *tail(done)]
        return
    ctx.wheel, ctx.sdist = wheels[0], sdists[0]
    r.notes.append(f"built {wheels[0].name} and {sdists[0].name}")
    r.ok = True


def g04_wheel(ctx: Context, r: Result) -> None:
    if ctx.wheel is None:
        r.notes.append("needs G03")
        return
    with zipfile.ZipFile(ctx.wheel) as zf:
        names = zf.namelist()
        meta_name = next((n for n in names if n.endswith(".dist-info/METADATA")), None)
        metadata = zf.read(meta_name).decode("utf-8") if meta_name else ""
        entry = next((zf.read(n).decode("utf-8") for n in names if n.endswith("entry_points.txt")), "")
    problems = [f"missing from the wheel: {need}" for need in ("authwatch/__init__.py", "authwatch/__main__.py", "authwatch/py.typed") if need not in names]
    problems += [f"must not be in the wheel: {n}" for n in names if re.search(r"(^|/)(tests?|scripts|\.github)/|__pycache__|\.pyc$|(^|/)\.env|\.coverage", n)]
    if not re.search(r"^Requires-Dist:\s*pyyaml", metadata, re.I | re.M):
        problems.append("the wheel metadata has no Requires-Dist for PyYAML")
    if not re.search(r"^Requires-Python:\s*>=\s*3\.11", metadata, re.M):
        problems.append("the wheel metadata has no Requires-Python >=3.11")
    if not re.search(r"^authwatch\s*=\s*authwatch\.", entry, re.M):
        problems.append("no console_scripts entry for authwatch")
    if not re.search(r"^(License-Expression|License-File|License):", metadata, re.M):
        problems.append("no licence information in the metadata")
    r.notes += problems
    r.ok = not problems


def _share_pyyaml(venv: Path, scratch: Path) -> None:
    """The scratch environment has no network, so it gets a copy of the PyYAML that the lab toolchain already installed (and nothing else from this environment)."""
    deps = scratch / "deps"
    deps.mkdir()
    shutil.copytree(Path(yaml.__file__).resolve().parent, deps / "yaml", ignore=shutil.ignore_patterns("__pycache__"))
    for extra in Path(yaml.__file__).resolve().parent.parent.glob("_yaml*"):
        if extra.is_dir():
            shutil.copytree(extra, deps / extra.name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(extra, deps / extra.name)
    site = next((venv / "lib").glob("python*/site-packages"), None) or venv / "Lib" / "site-packages"
    (site / "authwatch_gate_deps.pth").write_text(str(deps) + "\n", encoding="utf-8")


def g05_install(ctx: Context, r: Result) -> None:
    if ctx.wheel is None:
        r.notes.append("needs G03")
        return
    venv = ctx.scratch / "venv"
    made = run([PY, "-m", "venv", str(venv)], ctx.scratch)
    py = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if made.returncode != 0 or not py.exists():
        r.notes += ["could not create a scratch virtual environment", *tail(made)]
        return
    ctx.venv_python = py
    _share_pyyaml(venv, ctx.scratch)
    installed = run([str(py), "-m", "pip", "install", "--no-index", "--no-deps", "--quiet", str(ctx.wheel)], ctx.scratch)
    if installed.returncode != 0:
        r.notes += ["pip could not install the wheel offline", *tail(installed)]
        return
    elsewhere = ctx.scratch / "elsewhere"
    elsewhere.mkdir()
    where = run([str(py), "-c", "import authwatch, sys; print(authwatch.__file__); print(authwatch.__version__)"], elsewhere)
    lines = where.stdout.decode().strip().splitlines()
    if where.returncode != 0 or len(lines) != 2:
        r.notes += ["the installed package cannot be imported", *tail(where)]
        return
    problems = []
    if str(ctx.project.resolve()) in lines[0] or str(ctx.work) in lines[0]:
        problems.append("the import found the source tree, not the installed wheel")
    version = lines[1]
    script = py.parent / ("authwatch.exe" if os.name == "nt" else "authwatch")
    shown = run([str(script), "--version"], elsewhere) if script.exists() else None
    if shown is None:
        problems.append("the wheel installed no `authwatch` command")
    elif shown.stdout.decode().strip() != f"authwatch {version}":
        problems.append(f"`authwatch --version` printed {shown.stdout.decode().strip()!r}, expected 'authwatch {version}'")
    meta = run([str(py), "-c", "import importlib.metadata as m; print(m.version('authwatch'))"], elsewhere).stdout.decode().strip()
    if meta != version:
        problems.append(f"package metadata says {meta}, authwatch.__version__ says {version}: two sources of truth")
    sample = LAB / "sample-data" / "events-small.jsonl"
    scan = run([str(py), "-m", "authwatch", "scan", "--format", "json", str(sample)], elsewhere)
    try:
        events = json.loads(scan.stdout)["summary"]["events"]
    except (ValueError, KeyError, TypeError):
        events = None
    if scan.returncode != 0 or not isinstance(events, int) or events < 1:
        problems.append("`authwatch scan --format json` on the sample file did not print a JSON object with summary.events (part A needs only that much; part B needs the whole specification)")
    r.notes += problems
    r.ok = not problems


def g06_types(ctx: Context, r: Result) -> None:
    empty = ctx.scratch / "empty-mypy.ini"
    empty.write_text("[mypy]\n", encoding="utf-8")
    done = run([PY, "-m", "mypy", "--strict", "--config-file", str(empty), "--cache-dir", str(ctx.scratch / ".mypy"), "-p", "authwatch"], ctx.work, env={"MYPYPATH": str(ctx.work / "src")})
    r.ok = done.returncode == 0
    if not r.ok:
        r.notes += ["mypy --strict reports errors (your settings are ignored by the gate):", *tail(done, 8)]


NOQA_BLANKET = re.compile(r"#\s*noqa(?!\s*:\s*[A-Z]+[0-9]+)", re.I)
IGNORE_BLANKET = re.compile(r"#\s*type:\s*ignore(?!\[)")
FILE_NOQA = re.compile(r"#\s*ruff:\s*noqa", re.I)


def g07_lint(ctx: Context, r: Result) -> None:
    common = ["--isolated", "--line-length", "200", "--no-cache", "--output-format", "concise"]
    src = run([PY, "-m", "ruff", "check", *common, "--select", "F,E,W,B,S,UP,SIM,D1", "--ignore", "D105,D107", "src", "scripts"], ctx.work)
    tests = run([PY, "-m", "ruff", "check", *common, "--select", "F,E,W,B,S,UP,SIM", "--ignore", "S101", "tests"], ctx.work)
    problems: list[str] = []
    for done, label in ((src, "src and scripts"), (tests, "tests")):
        if done.returncode != 0:
            problems += [f"ruff finds problems in {label}:", *tail(done, 6)]
    for path in [*sorted((ctx.work / "src").rglob("*.py")), *sorted((ctx.work / "scripts").rglob("*.py")), *sorted((ctx.work / "tests").rglob("*.py"))]:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ctx.work)
        for n, ln in enumerate(text.splitlines(), 1):
            if NOQA_BLANKET.search(ln) or IGNORE_BLANKET.search(ln) or FILE_NOQA.search(ln):
                problems.append(f"{rel}:{n}: a suppression must name its rule or error code (and say why)")
    r.notes += problems
    r.ok = not problems


def g08_tests(ctx: Context, r: Result) -> None:
    rc = ctx.scratch / "coveragerc"
    rc.write_text("[run]\nbranch = True\nsource = authwatch\nparallel = True\npatch = subprocess\n", encoding="utf-8")
    env = {"PYTHONPATH": str(ctx.work / "src"), "COVERAGE_RCFILE": str(rc)}
    xml = ctx.scratch / "junit.xml"
    for old in ctx.work.glob(".coverage*"):
        old.unlink()
    done = run([PY, "-m", "coverage", "run", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"], ctx.work, env=env, timeout=900)
    problems: list[str] = []
    count = failed = 0
    if xml.exists():
        import xml.etree.ElementTree as ET

        root = ET.parse(xml).getroot()  # noqa: S314 - the file was written by the pytest run above, not by anyone else
        cases = list(root.iter("testcase"))
        count = len(cases)
        failed = sum(1 for c in cases if c.find("failure") is not None or c.find("error") is not None)
        skipped = sum(1 for c in cases if c.find("skipped") is not None)
        if skipped:
            problems.append(f"{skipped} test(s) are skipped; a skipped test proves nothing")
    if done.returncode != 0 or failed:
        problems += [f"your tests do not pass ({failed} failed or errored of {count})", *tail(done, 8)]
    if count < 30:
        problems.append(f"{count} tests; the capstone needs at least 30 (parsing, detection, rules, output and the command line each have many cases)")
    run([PY, "-m", "coverage", "combine", "--quiet"], ctx.work, env=env)
    report = run([PY, "-m", "coverage", "report", "--fail-under=90"], ctx.work, env=env)
    total = re.findall(r"TOTAL.*?(\d+)%", report.stdout.decode())
    if report.returncode != 0:
        problems.append(f"branch coverage of the package is {total[0] + '%' if total else 'unknown'}, the limit is 90%")
    else:
        r.notes.append(f"{count} tests pass, branch coverage {total[0] if total else '?'}%")
    r.notes += problems
    r.ok = not problems


def _workflow(ctx: Context) -> tuple[dict[object, object] | None, str]:
    files = sorted((ctx.work / ".github" / "workflows").glob("*.y*ml"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and "jobs" in data:
            return data, text
    return None, ""


def g09_ci(ctx: Context, r: Result) -> None:
    data, text = _workflow(ctx)
    if data is None:
        r.notes.append("no parsable workflow with jobs under .github/workflows")
        return
    problems: list[str] = []
    on = data.get("on", data.get(True))                       # YAML 1.1 reads the bare key `on` as the boolean True
    triggers = set(on) if isinstance(on, (dict, list)) else {on}
    if "pull_request_target" in triggers:
        problems.append("pull_request_target runs with secrets on code from forks: do not use it for a check workflow")
    if not triggers & {"push", "pull_request"}:
        problems.append("the workflow must run on push or pull_request")
    if data.get("permissions") != {"contents": "read"}:
        problems.append("set top-level `permissions: {contents: read}` (least privilege for the token)")
    jobs = cast(dict[str, Any], data["jobs"])
    versions: set[str] = set()
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "timeout-minutes" not in job:
            problems.append(f"job {name}: set timeout-minutes")
        if isinstance(job.get("permissions"), dict) and "write" in job["permissions"].values():
            problems.append(f"job {name}: a check job needs no write permission")
        matrix = (job.get("strategy") or {}).get("matrix", {}) if isinstance(job.get("strategy"), dict) else {}
        for v in matrix.get("python-version", []) if isinstance(matrix, dict) else []:
            if not isinstance(v, str):
                problems.append(f"job {name}: python-version {v!r} must be a quoted string (YAML reads 3.10 as the number 3.1)")
            versions.add(str(v))
        steps = [s for s in job.get("steps", []) if isinstance(s, dict)]
        checkout = False
        for step in steps:
            uses = str(step.get("uses", ""))
            if uses and not uses.startswith("./"):
                ref = uses.split("@", 1)[1] if "@" in uses else ""
                if not SHA.fullmatch(ref):
                    problems.append(f"job {name}: `{uses}` must be pinned to a full 40-character commit SHA (the gate cannot check that the SHA exists: you must)")
            if uses.startswith("actions/checkout"):
                checkout = True
                if (step.get("with") or {}).get("persist-credentials") is not False:
                    problems.append(f"job {name}: actions/checkout needs `persist-credentials: false`")
            run_text = str(step.get("run", ""))
            if re.search(r"\$\{\{\s*(github\.event\.|github\.head_ref|inputs\.)", run_text):
                problems.append(f"job {name}: untrusted `${{{{ ... }}}}` text inside `run:` (script injection); pass it through env: instead")
        if not checkout:
            problems.append(f"job {name}: no actions/checkout step")
        if not any("scripts/check.py" in str(s.get("run", "")) for s in steps):
            problems.append(f"job {name}: it must run `python scripts/check.py`, the same command as on your laptop")
    missing = {"3.11", "3.12", "3.13", "3.14"} - versions
    if missing:
        problems.append(f"the matrix must cover Python 3.11 to 3.14; missing {sorted(missing)}")
    if "secrets." in text:
        problems.append("a check workflow needs no secrets")
    r.notes += problems
    r.ok = not problems


def _pins(lock: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in lock.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][A-Za-z0-9.+!_-]*)(?:\s+--hash=sha256:[0-9a-f]{64})*", line)
        if not m:
            raise ValueError(f"not an exact pin: {line.split()[0] if line.split() else line}")
        pins[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = m.group(2)
    return pins


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"[0-9]+", text.split("+")[0])[:4])


def _affected(version: str, spec: str) -> bool:
    have = _version_tuple(version)
    for clause in spec.split(","):
        m = re.fullmatch(r"\s*(<=|>=|<|>|==)\s*([0-9][0-9.]*)\s*", clause)
        if not m:
            raise ValueError(f"unreadable range {clause!r}")
        want = _version_tuple(m.group(2))
        ok = {"<": have < want, "<=": have <= want, ">": have > want, ">=": have >= want, "==": have == want}[m.group(1)]
        if not ok:
            return False
    return True


def g10_dependencies(ctx: Context, r: Result) -> None:
    advisories = json.loads((TOOLS / "advisories.json").read_text(encoding="utf-8"))["advisories"]
    try:
        pins = _pins(ctx.work / "requirements.lock")
    except (OSError, ValueError) as exc:
        r.notes.append(f"requirements.lock: {exc}")
        return
    problems: list[str] = []
    if ctx.wheel is not None:
        with zipfile.ZipFile(ctx.wheel) as zf:
            meta = zf.read(next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))).decode("utf-8")
        requirements = [m.group(1).strip() for m in re.finditer(r"^Requires-Dist:\s*(.+)$", meta, re.M) if "extra ==" not in m.group(1)]
        required = [re.sub(r"[-_.]+", "-", re.split(r"[ ;<>=!~(\[]", item, maxsplit=1)[0]).lower() for item in requirements]
        for name in required:
            if name not in pins:
                problems.append(f"the wheel requires {name}, requirements.lock has no exact pin for it")
    else:
        problems.append("needs G03 (the wheel metadata names the run-time dependencies)")
    for name, version in pins.items():
        for adv in advisories:
            if adv["package"] == name and _affected(version, adv["affected"]):
                problems.append(f"{name}=={version} is affected by {adv['id']} ({adv['summary']})")
    r.notes += problems
    if not problems:
        r.notes.append(f"{len(pins)} pinned package(s) checked against {len(advisories)} synthetic advisories (offline; against real advisories use `pip-audit` or an OSV scanner with network access)")
    r.ok = not problems


SECRET = re.compile(r"""(?ix)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*(["'])[^"']{4,}\2|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}""")


def g11_hygiene(ctx: Context, r: Result) -> None:
    problems: list[str] = []
    for path in sorted(ctx.work.rglob("*")):
        if not path.is_file() or any(part in {".git", ".venv"} for part in path.parts):
            continue
        rel = path.relative_to(ctx.work)
        if path.name == ".env" or path.suffix in {".pem", ".key", ".p12"} or path.name in {"id_rsa", "id_ed25519"}:
            problems.append(f"{rel}: a file of this kind must not be in the project")
        if path.stat().st_size > 1_000_000:
            problems.append(f"{rel}: larger than 1 MB")
        if path.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".lock", ".cfg", ".ini", ".json"} and path.stat().st_size < 1_000_000:
            for n, ln in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if SECRET.search(ln):
                    problems.append(f"{rel}:{n}: looks like a credential")
    for path in sorted((ctx.work / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else (f"{fn.value.id}.{fn.attr}" if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) else "")
                if name in {"eval", "exec", "os.system", "pickle.loads", "pickle.load", "yaml.load", "yaml.full_load", "yaml.unsafe_load"}:
                    problems.append(f"{path.relative_to(ctx.work)}:{node.lineno}: {name}() on this path is not allowed")
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        problems.append(f"{path.relative_to(ctx.work)}:{node.lineno}: shell=True")
    ignore = (ctx.work / ".gitignore").read_text(encoding="utf-8") if (ctx.work / ".gitignore").is_file() else ""
    for need in (".env", "__pycache__", "dist", "build"):
        if not re.search(rf"^/?{re.escape(need)}/?(\*)?\s*$", ignore, re.M):
            problems.append(f".gitignore does not mention {need}")
    r.notes += problems
    r.ok = not problems


def g12_docs(ctx: Context, r: Result) -> None:
    problems: list[str] = []
    readme = (ctx.work / "README.md").read_text(encoding="utf-8") if (ctx.work / "README.md").is_file() else ""
    headings = {m.group(1).strip().lower() for m in re.finditer(r"^##\s+(.+)$", readme, re.M)}
    for need in ("install", "usage", "configuration", "exit codes", "security considerations", "development"):
        if need not in headings:
            problems.append(f"README.md has no '## {need.title()}' section")
    log = (ctx.work / "CHANGELOG.md").read_text(encoding="utf-8") if (ctx.work / "CHANGELOG.md").is_file() else ""
    version = None
    if ctx.wheel is not None:
        m = re.match(r"authwatch-([^-]+)-", ctx.wheel.name)
        version = m.group(1) if m else None
    first = re.search(r"^##\s+\[?v?([0-9][^\]\s]*)", log, re.M)
    if version is None:
        problems.append("needs G03 (to know the version)")
    elif not first or first.group(1) != version:
        problems.append(f"the newest CHANGELOG.md heading must be the released version {version}")
    if ctx.part == "B":                                       # part A has no options yet; part B documents every option of the specification
        for name in ("--rules", "--fail-on-findings", "--output", "--max-bad"):
            if name not in readme:
                problems.append(f"README.md does not document {name}")
    r.notes += problems
    r.ok = not problems


def _need(stream: IO[bytes] | None) -> IO[bytes]:
    """A pipe that Popen was asked to create (it is None only when it was not asked for)."""
    if stream is None:
        raise RuntimeError("the pipe was not created")
    return stream


def _generator(*extra: str) -> list[str]:
    return [PY, str(TOOLS / "make_events.py"), *extra]


def g13_scenario(ctx: Context, r: Result) -> None:
    py = ctx.venv_python
    if py is None:
        r.notes.append("needs G05 (the installed application)")
        return
    problems: list[str] = []
    truth_path = ctx.scratch / "truth.json"
    damage = ("--junk", "0.002", "--skew", "30", "--bom", "--crlf", "--pace", "0.02")             # unusable lines, events out of order, a byte-order mark, Windows line endings, a slow producer
    gen = subprocess.Popen(_generator("--seed", "7", "--minutes", "120", *damage, "--truth", str(truth_path)), stdout=subprocess.PIPE)  # noqa: S603
    stream = _need(gen.stdout)
    scan = subprocess.run([str(py), "-m", "authwatch", "scan", "--format", "json", "--max-bad", "50", "-"], stdin=stream, capture_output=True, timeout=300, check=False)  # noqa: S603
    stream.close()
    gen.wait(timeout=60)
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    if scan.returncode != 0:
        problems.append(f"the live stream made the scan fail (exit {scan.returncode}): {scan.stderr.decode()[-200:]}")
    else:
        report = json.loads(scan.stdout)
        got = [(f["kind"], f["subject"], f["first_ts"], f["last_ts"], f["count"]) for f in report["findings"]]
        want = [(f["kind"], f["subject"], f["first_ts"], f["last_ts"], f["count"]) for f in truth["findings"]]
        for item in want:
            if item not in got:
                problems.append(f"missed a planted attack: {item[0]} {item[1]}")
        for item in got:
            if item not in want:
                problems.append(f"reported something that was not planted: {item[0]} {item[1]}")
        s = report["summary"]
        if (s["events"], s["out_of_order"]) != (truth["events"], truth["out_of_order"]):
            problems.append(f"counted {s['events']} events and {s['out_of_order']} out of order, the stream had {truth['events']} and {truth['out_of_order']}")
        if f"{truth['bad_lines']} unusable".encode() not in scan.stderr:
            problems.append(f"the warning on stderr should say {truth['bad_lines']} unusable lines")
    # failure injection: every one must end with the documented exit status, a readable message and no traceback
    cases: list[tuple[str, list[str], bytes | None, int]] = []
    broken = ctx.scratch / "broken.jsonl.gz"
    import gzip

    data = subprocess.run(_generator("--seed", "2", "--minutes", "30"), capture_output=True, check=True).stdout  # noqa: S603
    broken.write_bytes(gzip.compress(data)[:-40] + b"corrupt-tail-bytes")
    cases += [("a corrupt archive", ["scan", str(broken)], None, 3), ("a missing file", ["scan", str(ctx.scratch / "nothing")], None, 3),
              ("too many unusable lines", ["scan", "--max-bad", "3", "-"], b"junk\n" * 10, 3), ("no unusable line is tolerated with --max-bad 0", ["scan", "--max-bad", "0", "-"], b"junk\n", 3),
              ("a wrong format", ["scan", "--format", "xml"], b"", 2), ("unknown rules key", ["scan", "--rules", str(ctx.scratch / "r.yaml"), "-"], b"", 2)]
    (ctx.scratch / "r.yaml").write_text("nonsense: 1\n", encoding="utf-8")
    for label, args, stdin, want_code in cases:
        done = run([str(py), "-m", "authwatch", *args], ctx.scratch, stdin=stdin)
        if done.returncode != want_code or b"Traceback" in done.stderr:
            problems.append(f"{label}: exit {done.returncode} (expected {want_code}){' with a traceback' if b'Traceback' in done.stderr else ''}")
    pipe = subprocess.Popen([str(py), "-m", "authwatch", "scan", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
    _need(pipe.stdin)
    _need(pipe.stdout).close()                                       # nobody reads the report: `authwatch scan ... | head -0`
    _, err = pipe.communicate(data[:200_000])
    if pipe.returncode not in (0, 141) or b"Traceback" in err or b"BrokenPipe" in err:
        problems.append(f"a closed output pipe: exit {pipe.returncode}, expected a quiet end (0)")
    child = subprocess.Popen([str(py), "-m", "authwatch", "scan", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
    _need(child.stdin).write(b'{"ts": "2026-10-14T00:00:00Z", "user": "a", "ip": "10.0.0.1", "outcome": "failure"}\n')
    _need(child.stdin).flush()
    time.sleep(1.5)
    if os.name != "nt":
        child.send_signal(signal.SIGINT)
        child.communicate(timeout=30)
        if child.returncode != 130:
            problems.append(f"Ctrl-C: exit {child.returncode} (expected 130)")
    else:
        child.kill()
        child.communicate()
    r.notes += problems
    if not problems:
        r.notes.append(f"{len(truth['findings'])} planted attacks found, {len(truth['must_not_report'])} near-misses not reported, damaged stream survived, "
                       f"{len(cases) + 2} failures ended as specified")
    r.ok = not problems


PART_B_ONLY = {"G08", "G13"}
GATES: list[tuple[str, str, Callable[[Context, Result], None]]] = [
    ("G01", "Project layout (src layout, entry files, tests, CI file)", g01_layout),
    ("G02", "Package metadata in pyproject.toml", g02_metadata),
    ("G03", "Offline build of a wheel and a source distribution", g03_build),
    ("G04", "Wheel contents and metadata", g04_wheel),
    ("G05", "Clean install, import from elsewhere, one source of truth for the version", g05_install),
    ("G06", "mypy --strict (your settings ignored)", g06_types),
    ("G07", "ruff rules of the specification; no blanket suppressions", g07_lint),
    ("G08", "Your tests pass, at least 30, branch coverage of at least 90%", g08_tests),
    ("G09", "CI workflow: least privilege, pinned actions, matrix 3.11-3.14, one command", g09_ci),
    ("G10", "Dependencies: exact pins that match the wheel, no known-bad version (offline, synthetic advisories)", g10_dependencies),
    ("G11", "Hygiene: no secrets, no dangerous calls, .gitignore", g11_hygiene),
    ("G12", "README sections and a CHANGELOG for the released version", g12_docs),
    ("G13", "Operational scenario: a live damaged stream, the planted attacks, eight failures", g13_scenario),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=Path, default=PROJECT)
    ap.add_argument("--part", choices=("A", "B"), default="B", help="A: the walking skeleton (all gates except G08 and G13, which need the finished application); B: every gate")
    ap.add_argument("--only", help="comma-separated gate ids, e.g. G03,G05 (G04, G05, G10, G12 and G13 need G03/G05 and run them first)")
    ap.add_argument("--json", type=Path, help="write the result as JSON")
    args = ap.parse_args()
    wanted = set(args.only.split(",")) if args.only else {g for g, _, _ in GATES if args.part == "B" or g not in PART_B_ONLY}
    if args.only:
        if wanted & {"G04", "G10", "G12"}:
            wanted.add("G03")
        if "G13" in wanted:
            wanted |= {"G03", "G05"}
        if "G05" in wanted:
            wanted.add("G03")
    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="authwatch-gate-") as td:
        if not args.project.is_dir():
            print(f"no project at {args.project}", file=sys.stderr)
            return 2
        ctx = Context(args.project, Path(td), part=args.part)
        for gate, title, fn in GATES:
            if gate not in wanted:
                continue
            res = Result(gate, title)
            try:
                fn(ctx, res)
            except Exception as exc:  # noqa: BLE001 - a gate must report its own failure, never crash the run
                res.ok = False
                res.notes.append(f"the gate itself failed: {type(exc).__name__}: {exc}")
            results.append(res)
            print(f"[{'PASS' if res.ok else 'FAIL'}] {gate} {title}")
            for note in res.notes:
                print(f"        {note}")
    passed = sum(r.ok for r in results)
    print(f"\n{passed} of {len(results)} gates passed")
    if args.json:
        args.json.write_text(json.dumps([{"gate": r.gate, "title": r.title, "ok": r.ok, "notes": r.notes} for r in results], indent=2) + "\n", encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
