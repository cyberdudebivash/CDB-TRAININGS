#!/usr/bin/env python3
"""Execute the Python Engineering lab and module-pack tests on every available CPython version and record the evidence.

For each requested minor version this script
  1. finds an interpreter (python3.X on PATH, /usr/bin/python3.X, or `uv python find X`),
  2. creates a fresh virtual environment under .work/lab-venvs/ (git-ignored) and installs courses/python-engineering/labs/requirements.txt,
  3. runs tests/test_python_engineering_labs.py and tests/test_module_packs.py with that environment's interpreter,
  4. writes docs/qa/data/lab_execution_<cutoff>.json (versions, commands, exit codes, per-test outcomes).

A version for which no interpreter can be found is recorded as NOT_EXECUTED with the reason; it is never reported as passing.
Requires network access to install the pinned packages from PyPI (no paid service, no credentials).

Run:  .venv/bin/python scripts/validation/run_lab_matrix.py [--versions 3.11,3.12,3.13,3.14,3.15] [--cutoff 2026-10-14]
Render the Markdown report afterwards with scripts/validation/render_lab_evidence.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_fingerprint as EF  # noqa: E402

REQS = ROOT / "courses" / "python-engineering" / "labs" / "requirements.txt"
SUITES = ["tests/test_python_engineering_labs.py", "tests/test_module_packs.py", *sorted(f"tests/{p.name}" for p in (ROOT / "tests").glob("test_fnd_m[0-9][0-9].py"))]      # one file per foundations module


LABS = "tests/test_python_engineering_labs.py"
MODULE_GROUPS = [("m01-m04", ("m01", "m02", "m03", "m04")), ("m05-m06", ("m05", "m06")), ("m07-m08", ("m07", "m08")), ("m09", ("m09",)), ("m10", ("m10",)), ("m11", ("m11",)), ("m12-m13", ("m12", "m13"))]


def chunks() -> list[tuple[str, list[str], str | None]]:
    """The suites cut into pieces of at most about half an hour, so that an interrupted run loses one piece and not an interpreter: (name, files, a `-k` expression or None).
    Every test of SUITES belongs to exactly one piece (tests/test_gate_a.py checks it)."""
    out: list[tuple[str, list[str], str | None]] = [("module-packs", ["tests/test_module_packs.py"], None)]
    for name, mods in MODULE_GROUPS:
        out.append((f"labs-{name}", [LABS], " or ".join(f"test_{m}_" for m in mods)))
    every = " or ".join(f"test_m{n:02d}_" for n in range(1, 14))
    out.append(("labs-other", [LABS], f"not ({every})"))
    foundations = [f for f in SUITES if "test_fnd_m" in f]
    if foundations:
        out.append(("foundations", foundations, None))
    return out


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def find_interpreter(version: str) -> tuple[str | None, str]:
    for cand in (shutil.which(f"python{version}"), f"/usr/bin/python{version}"):
        if cand and Path(cand).exists():
            managed = "/uv/python/" in str(Path(cand).resolve())
            return cand, "uv-managed python-build-standalone build" if managed else "distribution or PATH interpreter"
    uv = shutil.which("uv") or str(Path(sys.executable).with_name("uv"))
    if Path(uv).exists():
        found = sh([uv, "python", "find", version])
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.strip().splitlines()[0], "uv-managed python-build-standalone build"
    return None, "no interpreter found (python3.X on PATH, /usr/bin, or `uv python install X`)"


def run_chunk(py: str, name: str, files: list[str], expr: str | None, xml: Path, env: dict) -> dict:
    cmd = [py, "-m", "pytest", *files, *(["-k", expr] if expr else []), f"--junitxml={xml}", "-q", "-p", "no:cacheprovider", "--tb=short", "-rs"]
    started = time.time()
    proc = sh(cmd, cwd=ROOT, env=env, timeout=7200)
    tests, skipped = [], []
    if xml.exists():
        for tc in ET.parse(xml).getroot().iter("testcase"):
            outcome = "failed" if tc.find("failure") is not None else "error" if tc.find("error") is not None else "skipped" if tc.find("skipped") is not None else "passed"
            test_id = f"{(tc.get('classname') or '').replace('.', '/')}::{tc.get('name')}"
            tests.append({"id": test_id, "outcome": outcome})
            if outcome == "skipped":
                skipped.append({"id": test_id, "reason": (tc.find("skipped").get("message") or "")[:160]})
    result = {"name": name, "command": "python -m pytest " + " ".join(files) + (f" -k '{expr}'" if expr else "") + " -q -p no:cacheprovider", "exit": proc.returncode,
              "duration_s": round(time.time() - started, 1), "tests": tests, "skipped": skipped}
    if proc.returncode != 0:
        result["failure_tail"] = (proc.stdout + proc.stderr)[-1500:]
    return result


def chunk_passed(result: dict) -> bool:
    return result.get("exit") == 0 and bool(result.get("tests")) and all(t["outcome"] == "passed" for t in result["tests"])


def run_one(version: str, work: Path, cutoff: str, saved: dict[str, dict] | None = None, save=None) -> dict:
    record: dict = {"requested": version}
    exe, source = find_interpreter(version)
    record["interpreter_source"] = source
    if not exe:
        record.update(status="NOT_EXECUTED", reason=source)
        return record
    info = sh([exe, "-c", "import platform,sys;print(platform.python_implementation(),platform.python_version(),sys.version.split()[0])"]).stdout.split()
    record.update(executable=exe, implementation=info[0], python=info[1])
    venv_dir = work / f"py{version.replace('.', '')}"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    made = sh([exe, "-m", "venv", str(venv_dir)])
    if made.returncode != 0:
        record.update(status="NOT_EXECUTED", reason="venv creation failed: " + made.stderr[-300:])
        return record
    py = str(venv_dir / "bin" / "python")
    inst = sh([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(REQS)], timeout=1800)
    record["install_exit"] = inst.returncode
    if inst.returncode != 0:
        record.update(status="NOT_EXECUTED", reason="package installation failed: " + (inst.stderr or inst.stdout)[-400:])
        return record
    freeze = sh([py, "-m", "pip", "list", "--format=json", "--disable-pip-version-check"])
    packages = {p["name"].lower(): p["version"] for p in json.loads(freeze.stdout)}
    record["packages"] = {k: packages.get(k, "") for k in ("pytest", "pyyaml", "pyjwt", "ruff", "mypy", "build", "setuptools", "wheel", "pip", "requests", "httpx", "httpx2", "pydantic", "fastapi", "starlette")}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("VIRTUAL_ENV", None)
    done: list[dict] = []
    for name, files, expr in chunks():
        result = (saved or {}).get(name)
        if result is not None and chunk_passed(result):
            print(f"   {name}: reused from the interrupted run ({len(result['tests'])} tests)", flush=True)
        else:
            result = run_chunk(py, name, files, expr, work / f"junit-py{version.replace('.', '')}-{name}.xml", env)
            print(f"   {name}: exit {result['exit']}, {len(result['tests'])} tests, {result['duration_s']} s", flush=True)
            if save is not None and chunk_passed(result):
                save(version, name, result)
        done.append(result)
    tests = [t for r in done for t in r["tests"]]
    ids = [t["id"] for t in tests]
    assert len(ids) == len(set(ids)), "a test was selected by two pieces"
    record["command"] = "python -m pytest " + " ".join(SUITES) + " -q -p no:cacheprovider (run in pieces: " + ", ".join(r["name"] for r in done) + ")"
    record["pytest_exit"] = max(r["exit"] for r in done)
    record["duration_s"] = round(sum(r["duration_s"] for r in done), 1)
    record["pieces"] = [{"name": r["name"], "exit": r["exit"], "duration_s": r["duration_s"], "tests": len(r["tests"])} for r in done]
    record["tests"] = tests
    record["skipped"] = [x for r in done for x in r["skipped"]]
    record["counts"] = {o: sum(1 for t in tests if t["outcome"] == o) for o in ("passed", "failed", "error", "skipped")}
    record["status"] = "PASS" if record["pytest_exit"] == 0 and not record["counts"]["failed"] and not record["counts"]["error"] and tests else "FAIL"
    if record["status"] == "FAIL":
        record["failure_tail"] = "\n".join(r.get("failure_tail", "") for r in done if r["exit"] != 0)[-1500:]
    return record


def write_partial(partial: Path, identity: str, results: list[dict], pieces: dict[str, dict[str, dict]]) -> None:
    tmp = partial.with_suffix(".tmp")
    tmp.write_text(json.dumps({"tree_id": identity, "results": results, "pieces": pieces}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(partial)                                       # a restart in the middle of the write must not destroy the record


def tree_id(fingerprints: dict[str, str], private_fingerprints: dict[str, str]) -> str:
    """Identity of the content that a run executes: the fingerprints of every module and of every private pack, whatever the commit."""
    return hashlib.sha256(json.dumps([fingerprints, private_fingerprints, EF.FORMULA, SUITES], sort_keys=True).encode()).hexdigest()


def resumable(partial: Path, identity: str) -> dict[str, dict]:
    """The interpreters that already PASSED in an interrupted run of exactly this content (`--resume`); nothing else is ever reused."""
    try:
        saved = json.loads(partial.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if saved.get("tree_id") != identity:
        return {}
    return {r["requested"]: r for r in saved.get("results", []) if r.get("status") == "PASS" and r.get("requested")}


def saved_pieces(partial: Path, identity: str) -> dict[str, dict[str, dict]]:
    """The pieces of an interpreter that passed before an interruption, per interpreter, for exactly this content."""
    try:
        saved = json.loads(partial.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return saved.get("pieces", {}) if saved.get("tree_id") == identity else {}


def restore_default_sigint() -> bool:
    """A process started in the background of a non-interactive shell (`( cmd & )`, a scheduler, some CI runners) inherits an IGNORED SIGINT, and so does every process below it:
    Python then installs no KeyboardInterrupt handler, and every test that sends Ctrl-C to a program under test (PY-M11's interrupt checks and lesson block) hangs or fails.
    That would make the evidence depend on how the run was started, so the runner restores the default first. Returns True when it had to."""
    if signal.getsignal(signal.SIGINT) is signal.SIG_IGN:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        return True
    return False


def main() -> int:
    if restore_default_sigint():
        print("SIGINT was ignored in this process (background launch); restored the default so that the Ctrl-C tests can run", flush=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="3.11,3.12,3.13,3.14,3.15")
    ap.add_argument("--cutoff", default="2026-10-14")
    ap.add_argument("--resume", action="store_true", help="reuse the interpreters that passed in an interrupted run of the same content (a long run survives a restart)")
    a = ap.parse_args()
    work = ROOT / ".work" / "lab-venvs"
    work.mkdir(parents=True, exist_ok=True)
    head = sh(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT).stdout.strip()
    dirty = bool(sh(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT).stdout.strip())
    fingerprints, private_fingerprints = {}, {}
    for lesson in sorted((ROOT / "courses").glob("*/modules/*/lesson.md")):
        slug, module_id = lesson.parts[-4], lesson.parts[-2]
        fingerprints[module_id] = EF.fingerprint(EF.execution_inputs(slug, module_id))
        private_fp = EF.private_fingerprint(slug, module_id)
        if private_fp:
            private_fingerprints[module_id] = private_fp
    identity = tree_id(fingerprints, private_fingerprints)
    partial = work / f"partial_{a.cutoff}.json"
    reused = resumable(partial, identity) if a.resume else {}
    pieces: dict[str, dict[str, dict]] = saved_pieces(partial, identity) if a.resume else {}
    results = []

    def save(version: str, name: str, result: dict) -> None:
        pieces.setdefault(version, {})[name] = result
        write_partial(partial, identity, results, pieces)

    for v in a.versions.split(","):
        v = v.strip()
        print(f"== CPython {v}", flush=True)
        if v in reused:
            r = reused[v]
            print(f"   reused from the interrupted run: {r['status']}  {r.get('python', '')}  {r.get('counts', '')}", flush=True)
        else:
            r = run_one(v, work, a.cutoff, pieces.get(v), save)
            print(f"   {r['status']}  {r.get('python', '')}  {r.get('counts', r.get('reason', ''))}", flush=True)
        results.append(r)
        write_partial(partial, identity, results, pieces)
    private = (ROOT / "courses" / "python-engineering" / "instructor" / "PY-M02" / "independent-reference").exists()
    out = {"schema_version": 1, "cutoff": a.cutoff, "run_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "commit": head, "working_tree_dirty": dirty,
           "host": f"{platform.system()} {platform.release()} {platform.machine()}", "private_instructor_pack_present": private,
           "fingerprint_formula": EF.FORMULA, "fingerprints": fingerprints, "private_fingerprints": private_fingerprints,
           "requirements_file": "courses/python-engineering/labs/requirements.txt", "suites": SUITES, "interpreters": results}
    path = ROOT / "docs" / "qa" / "data" / f"lab_execution_{a.cutoff}.json"
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT))
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
