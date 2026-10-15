---
id: PY-M11
title: "Capstone: typed, tested, documented application with CI"
course: COURSE-PY-ENG
level: 3
audience: "Programmers who have finished the earlier Python Engineering modules (at least PY-M02, PY-M03, PY-M04, PY-M05, PY-M07 and PY-M12; PY-M09 and PY-M10 help) and now have to turn a script into something a team can install, trust, operate and hand over: an application with a specification, a test suite that can fail, a package that installs and runs outside the source tree, a command-line contract, a supply chain that is checked, and a pipeline that runs the same checks as the laptop."
prerequisites:
  - "PY-M02 (tests), PY-M03 (types, layout), PY-M04 (packaging), PY-M05 (files and parsing), PY-M07 (secure coding) and PY-M12 (value types); PY-M09 (measuring) and PY-M10 (hostile input) help"
  - "Python 3.11 or newer; the lessons and labs were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "pytest 9.1.1, coverage 7.16.2, mypy 2.4.0, ruff 0.17.0, build 1.6.1, setuptools 84.0.0, wheel 0.48.0, PyYAML 6.0.3 and types-PyYAML 6.0.12.20260906 from labs/requirements.txt; no network, no account, no paid service, no open port"
estimated_time_hours: {lesson: 2.0, guided_lab: 3.5, independent_lab: 8.5, total: 14.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); differences executed in this lesson (R-101)", coverage: "7.16.2", mypy: "2.4.0", ruff: "0.17.0", build: "1.6.1", setuptools: "84.0.0", pyyaml: "6.0.3", pytest: "9.1.1", github_actions: "docs.github.com secure-use guide, actions/checkout v7.0.1, actions/setup-python v7.0.0 (R-101)"}
last_verified: 2026-10-15
---

# PY-M11 - Capstone: typed, tested, documented application with CI

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Turn a prototype into a specification: characterise what it does today, decide row by row what is a feature and what is a defect, and write the contract (inputs, outputs, errors, exit codes, limits) so precisely that two people would build the same program. |
| **LO2** | Structure an application as a package that a stranger can install: `src` layout, a single source of truth for the version, a typed public API, an entry point, a wheel that contains what it should and nothing else, and proof that it runs outside the source tree. |
| **LO3** | Test it so that the tests can fail: black-box tests through the public interface, a direct reading of the specification used as an oracle against random input, branch coverage with its limits understood, and a mutation check of your own suite. |
| **LO4** | Handle untrusted input and a hostile supply chain: bounded reads, safe parsers, no input text in any diagnostic, exact pins checked against advisories, a wheel with no stray files, and a workflow whose permissions, action versions and inputs cannot be abused. |
| **LO5** | Make the command line a contract: exit codes, standard output for the result and standard error for diagnostics, atomic output files, signals, a closed pipe, and logs that name events without quoting data. |
| **LO6** | Release it: one command that runs the same checks locally and in the pipeline, a changelog and a version that agree, a README that states what the tool does and does not protect, and a short note that lets the next owner continue. |

Every objective is taught here, practised in the two parts of the lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

A capstone is the one artefact that other people open. A hiring manager reads its README, a colleague runs its tests, an auditor looks at its pipeline, and an on-call engineer has to understand its exit codes at three in the morning. What they find matters more than what it can do: whether it installs, whether `--help` tells the truth, whether the tests would notice if somebody changed the thing they test, whether the pipeline can be abused, whether a closed pipe makes it print a traceback.

The 2025 handbook ends its first module with a "complete, real-world" project (PDF pages 93 to 98): a log monitor with a folder structure, a few functions and a main loop. It is a good picture of the *shape* of a small application and it is presented as something that "could run in a SOC, a server, a DevOps environment, a cloud system". Section 2 runs it and shows that it would not survive the first week in any of those places. This module keeps the shape and replaces everything else.

The application you build in the labs is `authwatch`: it reads authentication events (JSON Lines) and reports brute force, password spray and a compromise after failures. The domain is security because that is the work this course prepares you for, but the lessons are not about detection. They are about everything around the detection that makes the difference between a script and a product.

The lab has two parts. **Part A (guided, 3.5 hours)** builds a *walking skeleton*: the package, the pipeline and the gate with almost no behaviour, so that the machinery is right before the logic arrives. **Part B (independent, 8.5 hours)** builds the application from a specification. A gate script that you can run offline (`tools/gate.py`) tells you at any time which of thirteen conditions are not met; instructors run a hidden suite and a mutation check of your tests.

## 2. The handbook's project, executed (LO1)

Here is the project of pages 93 to 97 in one file: the functions of `reader.py`, `analyzer.py`, `alert.py` and `main.py` with the constants of `config.py`, as printed except that the arrow in the alert text is ASCII and `main` takes the path of the log as an argument and returns the counts, so that the block can run it. The block runs it on a log of one hundred identical errors, looks at what it does, and then runs the `main` of page 97 as printed.

```python run
import contextlib
import io
import os
import tempfile
from datetime import datetime

ALERT_THRESHOLD = 5
ALERT_KEYWORDS = ["ERROR", "FAILED", "CRITICAL"]


def read_log(path):
    with open(path) as f:
        for line in f:
            yield line.strip()


def analyze(line):
    for key in ALERT_KEYWORDS:
        if key in line:
            return key
    return None


def send_alert(keyword, line):
    print(f"[{datetime.now()}] ALERT: {keyword} detected -> {line}")


def main(path):
    counts = {}
    for line in read_log(path):
        match = analyze(line)
        if match:
            counts[match] = counts.get(match, 0) + 1
            if counts[match] >= ALERT_THRESHOLD:
                send_alert(match, line)
    return counts


with tempfile.TemporaryDirectory() as folder:
    log = os.path.join(folder, "server.log")
    with open(log, "w", encoding="utf-8") as handle:
        handle.write("".join(f"2026-10-14 12:00:{i % 60:02d} ERROR disk full\n" for i in range(100)))
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        counts = main(log)
    alerts = shown.getvalue().count("ALERT")
    print("100 error lines ->", counts, "->", alerts, "alerts")
    assert alerts == 96                                    # every line from the fifth on raises an alert: an alert storm, not an alert

    for line, expected in [("backup finished: 0 ERROR lines", "ERROR"), ("RETRY_FAILED_COUNT=0", "FAILED"), ("CRITICALITY=low", "CRITICAL")]:
        assert analyze(line) == expected                  # a substring is not an event
    for line in ("error: disk full", "Failed password for root from 203.0.113.5"):
        assert analyze(line) is None                      # and the real events are missed: the match is case-sensitive

    assert datetime.now().tzinfo is None                  # the alert time is naive local time: no zone, ambiguous twice a year
    try:
        open(os.path.join(folder, "reports", "summary.txt"), "w")
    except FileNotFoundError:
        print("write_summary writes into a folder it does not create")

    PRINTED_MAIN = """
def main():
    counts = {}
    for line in read_log(LOG_FILE):
        match = analyze(line)
        if match:
           counts[match] = counts.get(match, 0) + 1
           if counts[match] >= ALERT_THRESHOLD:
               send_alert(match, line)
    write_summary(counts)
"""
    page_97 = {"read_log": read_log, "analyze": analyze, "send_alert": send_alert, "LOG_FILE": log, "ALERT_THRESHOLD": ALERT_THRESHOLD}    # exactly the names that page 97 imports
    exec(compile(PRINTED_MAIN, "main.py", "exec"), page_97)                                                                                 # the text of the page, in a namespace that holds what the page imports
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            page_97["main"]()
    except NameError as error:
        print("main.py of page 97 ends with:", error)
        assert "write_summary" in str(error)               # the page calls a function that it never imports
```

Seven problems in about forty lines, all visible only when somebody runs it. None is a typing error. Six are *design* defects: the rule is "every line from the fifth on" (it should be "the line that crosses the threshold, once per episode"); the unit of detection is a substring of free text (it should be a field of a structured event); time has no zone; the summary is written into a folder that the code does not create (the tree on page 94 lists it, so a learner who copies the tree has it and one who copies the code does not); there is no test, no type, no package and no pipeline; and the page says "reads live logs" while the code reads a finished file. The seventh is not a design defect but a plain one that every reader meets on the first run: the `main.py` of page 97 calls `write_summary` and never imports it, so the program as printed finishes its loop and ends with a `NameError`. The finding is F-PYH-016.

The point of the exercise is the order of work. Nobody should open an editor before knowing which of these are *features to keep* and which are *defects to fix*.

## 3. Characterise before you change (LO1)

When you inherit a script (the lab gives you one, `lab-guided/prototype/authwatch_proto.py`), write down what it does *before* you change anything. That table is a characterisation: for a handful of inputs, the output today, and a decision for each row.

```python run
import re

KEYWORDS = ["ERROR", "FAILED", "CRITICAL"]


def prototype(line):
    for key in KEYWORDS:
        if key in line:
            return key
    return None


def revised(line):
    found = re.search(r"\b(ERROR|FAILED|CRITICAL)\b", line, re.IGNORECASE)
    return found.group(1).upper() if found else None


# input, what the prototype does today, what the specification says, the decision
TABLE = [
    ("ERROR disk full", "ERROR", "ERROR", "keep"),
    ("CRITICAL: temperature 91C", "CRITICAL", "CRITICAL", "keep"),
    ("all quiet", None, None, "keep"),
    ("RETRY_FAILED_COUNT=0", "FAILED", None, "fix: a name that contains a keyword is not the keyword"),
    ("CRITICALITY=low", "CRITICAL", None, "fix"),
    ("error: disk full", None, "ERROR", "fix: the real event was missed"),
    ("Failed password for root", None, "FAILED", "fix"),
    ("backup finished: 0 ERROR lines", "ERROR", "ERROR", "open question: free text cannot tell a count from an event"),
]
for line, today, wanted, decision in TABLE:
    assert prototype(line) == today, line               # the characterisation: what the program does now
    assert revised(line) == wanted, line                # the specification the new code is written to
    kept = today == wanted
    assert kept == decision.startswith("keep") or decision.startswith("open"), line
print(sum(1 for *_, d in TABLE if d.startswith("keep")), "rows kept,", sum(1 for *_, d in TABLE if d.startswith("fix")), "rows fixed,", sum(1 for *_, d in TABLE if d.startswith("open")), "open")
```

Two things to notice. First, the table is *data*: the old behaviour and the new behaviour are both asserted, so a change that touches a "keep" row fails loudly, and a "fix" row cannot be fixed by accident. Second, the last row is not fixable by a better pattern: whatever you do, the text `0 ERROR lines` contains the word. That is the real answer to the handbook project's design. The way out is to stop reading prose and read *fields*: a structured event has an outcome, a user and an address, and a rule over fields cannot be fooled by a sentence. `authwatch` reads JSON Lines for that reason.

The specification you write from such a table (the lab gives you `SPEC.md` as the finished example) has the shape every contract needs: the input and what happens to each way it can be wrong, the output down to the bytes, the limits, the order of rules, and the exit status of every failure. A sentence in a specification is either testable or it is a wish.

## 4. A package a stranger can install (LO2)

Two layouts are common. A *flat* layout keeps the package next to `pyproject.toml`; a `src` layout puts it under `src/`. The difference is not style. When you run Python from the project folder, a flat package is importable *whether or not it is installed*, so a test that passes proves nothing about the wheel. With a `src` layout the package can only be found once it is installed (or the path is added on purpose), so "it works from the wheel" can be checked.

```python run
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "flat" / "demo").mkdir(parents=True)
    (root / "flat" / "demo" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (root / "src_layout" / "src" / "demo").mkdir(parents=True)
    (root / "src_layout" / "src" / "demo" / "__init__.py").write_text('__version__ = "1.0.0"\n')

    def importable(project: str) -> bool:
        done = subprocess.run([sys.executable, "-c", "import demo"], cwd=root / project, capture_output=True)
        return done.returncode == 0

    assert importable("flat") is True           # works with nothing installed: a green test run can hide a broken wheel
    assert importable("src_layout") is False    # cannot be found until it is installed
    print("flat layout imports from the source tree; src layout needs an installed package")
```

The second trap is the version. A version that appears in two places will differ in one of them one day. The lab's gate (G05) therefore builds the wheel, installs it into a scratch environment, and compares three things: the version in the wheel's metadata, the version printed by `authwatch --version`, and `authwatch.__version__`. The block below builds two tiny projects with `python -m build --no-isolation` (offline, using the pinned `setuptools` and `wheel` that are already installed): one with a static version in `pyproject.toml` that nobody updated in the code, and one that reads the version from the code.

```python run
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HEAD = '[build-system]\nrequires = ["setuptools >= 77.0.3"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "demo"\nrequires-python = ">= 3.11"\n'
TAIL = '\n[tool.setuptools.packages.find]\nwhere = ["src"]\n'


def build(root: Path, version_lines: str) -> str:
    (root / "src" / "demo").mkdir(parents=True)
    (root / "src" / "demo" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (root / "pyproject.toml").write_text(HEAD + version_lines + TAIL)
    done = subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", str(root / "dist"), str(root)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-600:] + done.stderr[-600:]
    wheel = next((root / "dist").glob("*.whl"))
    with zipfile.ZipFile(wheel) as zf:
        meta = zf.read(next(n for n in zf.namelist() if n.endswith("METADATA"))).decode()
    return next(line.split(": ", 1)[1] for line in meta.splitlines() if line.startswith("Version: "))


with tempfile.TemporaryDirectory() as folder:
    static = build(Path(folder) / "static", 'version = "1.0.1"\n')
    single = build(Path(folder) / "single", 'dynamic = ["version"]\n\n[tool.setuptools.dynamic]\nversion = { attr = "demo.__version__" }\n')
    print("static version in pyproject.toml: wheel says", static, "- the code says 1.0.0")
    print("version read from the package:    wheel says", single, "- the code says 1.0.0")
    assert static == "1.0.1" and single == "1.0.0"        # the first wheel disagrees with the code it contains
```

The rule: **one source of truth** (here `__version__` in the package; the build reads it) and a check that the built artefact agrees with it. The same thinking applies to everything that is stated twice: the list of runtime dependencies in `pyproject.toml` and in a lock file, the list of Python versions in the metadata and in the pipeline, the exit codes in the code and in the README. Either generate one from the other or test that they agree.

What goes *into* the wheel matters as much as what does not. A wheel is a zip file; anything in the package directory ships. Tests, scripts, `.env` files, editor backups and `__pycache__` do not belong in it, and a `py.typed` marker (an empty file) does: without it, type checkers treat your package as untyped for every user. Gate G04 checks the list of names in the wheel and the metadata (`Requires-Dist`, `Requires-Python`, the entry point and the licence).

## 5. Tests that can fail (LO3)

A green test run says that the tests did not find a problem. It says nothing about whether they *could* have. Two instruments measure the difference.

**Coverage** reports which lines and branches ran. It is useful for finding code no test touches, and it is silent about whether any test would notice a change in the code that did run. The block below writes a module, a weak test that touches every line and every branch, and then applies six one-character changes ("mutants") to the module, one at a time, running the tests each time.

```python run
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE = '''
def expired(now, exp):
    return now >= exp


def in_window(now, t, window):
    return now - window < t <= now
'''
WEAK = '''
from clock import expired, in_window


def test_expired():
    assert expired(200, 100) is True
    assert expired(50, 100) is False


def test_in_window():
    assert in_window(100, 95, 10) is True
    assert in_window(100, 50, 10) is False
    assert in_window(100, 101, 10) is False
'''
BOUNDARY = '''

def test_the_edges():
    assert expired(100, 100) is True                      # expired AT exp, not after it
    assert in_window(100, 90, 10) is False                # exactly one window old is outside
    assert in_window(100, 100, 10) is True                # the newest instant is inside
'''
MUTANTS = [("now >= exp", "now > exp"), ("now >= exp", "now == exp"), ("now - window < t", "now - window <= t"), ("<= now", "< now"), ("now - window", "now + window"), ("<= now", ">= now")]


def run_tests(folder: Path) -> bool:
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(folder / "test_clock.py")], cwd=folder, capture_output=True, text=True)
    return done.returncode == 0


def survivors(tests: str) -> list[str]:
    left = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root / "test_clock.py").write_text(tests)
        (root / "clock.py").write_text(MODULE)
        assert run_tests(root)                             # the tests pass on the real code
        for old, new in MUTANTS:
            (root / "clock.py").write_text(MODULE.replace(old, new, 1))
            if run_tests(root):
                left.append(f"{old!r} -> {new!r}")
    return left


weak = survivors(WEAK)
strong = survivors(WEAK + BOUNDARY)
print("weak tests: every line and branch run; survivors:", weak)
print("with the three edge tests; survivors:", strong)
assert len(weak) == 3 and strong == []
```

The weak suite has 100 percent line and branch coverage and lets three of the six defects through: exactly the boundary mistakes that matter in time windows. The lab's gate demands branch coverage of at least 90 percent *and* your tests are graded by a mutation check against defective copies of the reference implementation, because the second number is the one that tells the truth. A suite written against the **public interface** (the package API and the command line) can be run against *any* implementation of the specification, which is exactly how instructors grade it.

**A direct reading of the specification as an oracle.** The strongest test of a clever algorithm is a stupid one: a few lines that follow the specification literally and are obviously right, compared with the clever one on thousands of random inputs. The block counts events in a sliding window with a queue (fast) and with a list scan (slow, obvious), and the random comparison finds a defect that two hand-made examples did not.

```python run
import random
from collections import deque


def naive(events, window):
    """Count, at each event, the events inside (t - window, t]. Written from the sentence, slow on purpose."""
    return [sum(1 for u in events[: i + 1] if u > t - window) for i, t in enumerate(events)]


def fast_buggy(events, window):
    q, out = deque(), []
    for t in events:
        q.append(t)
        while q and q[0] < t - window:                    # defect: an event exactly one window old is kept
            q.popleft()
        out.append(len(q))
    return out


def fast_fixed(events, window):
    q, out = deque(), []
    for t in events:
        q.append(t)
        while q and q[0] <= t - window:
            q.popleft()
        out.append(len(q))
    return out


assert fast_buggy([0, 5, 20], 10) == naive([0, 5, 20], 10)          # the hand-made example does not notice
rng = random.Random(7)
first_difference = None
for _ in range(2000):
    events = sorted(rng.randrange(0, 40) for _ in range(rng.randrange(1, 12)))
    window = rng.choice([1, 5, 10])
    assert fast_fixed(events, window) == naive(events, window)
    if first_difference is None and fast_buggy(events, window) != naive(events, window):
        first_difference = (events, window)
print("random comparison finds the defect with", first_difference)
assert first_difference is not None
```

The lab's hidden suite uses this method on `detect`: 120 random streams against a 40-line reading of the specification.

## 6. Untrusted input (LO4)

Everything `authwatch` reads comes from somewhere you do not control: the event stream, the rules file, the file names on the command line. Two habits cover most of the ground.

**Bounded reads.** `for line in stream` reads a line of any length into memory. A hostile or broken producer can send fifty megabytes without a newline, and the process dies or the machine swaps. `stream.readline(limit)` returns at most `limit` bytes; a line longer than the specification allows is one error and the rest of it is thrown away unread.

**Safe parsers.** YAML's full loaders can construct arbitrary Python objects, which means a configuration file can run code. `yaml.safe_load` builds only plain data. The block shows both, harmlessly (the "payload" creates an empty folder), and then three things that surprise people even with the safe loader, because YAML 1.1 reads some plain words as other types.

```python run
import io
import os
import tempfile
import tracemalloc

import yaml

# 1. a bounded read against an unbounded one (a producer that sends 20 MB without a newline, then one)
class Producer(io.RawIOBase):
    def __init__(self):
        self.remaining = 20_000_001

    def readable(self):
        return True

    def readinto(self, buffer):
        n = min(len(buffer), self.remaining)
        if n == 0:
            return 0
        buffer[:n] = (b"x" * (n - 1) + b"\n") if n == self.remaining else b"x" * n          # the last byte of the stream is the newline
        self.remaining -= n
        return n


tracemalloc.start()
for _ in io.BufferedReader(Producer()):                   # iteration reads the whole line
    pass
unbounded = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
tracemalloc.start()
stream = io.BufferedReader(Producer())
while True:
    chunk = stream.readline(65536)                        # at most 64 KiB at a time, however long the line is
    if not chunk or chunk.endswith(b"\n"):
        break
bounded = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
print(f"peak memory reading one 20 MB line: unbounded {unbounded // 1_000_000} MB, bounded {bounded // 1000} KB")
assert unbounded > 10_000_000 and bounded < 1_000_000

# 2. a document that executes code with the full loader and is refused by the safe one
with tempfile.TemporaryDirectory() as folder:
    marker = os.path.join(folder, "payload-ran")
    payload = f"!!python/object/apply:os.mkdir ['{marker}']"
    try:
        yaml.safe_load(payload)
        raise AssertionError("the safe loader accepted a python tag")
    except yaml.YAMLError:
        assert not os.path.exists(marker)
    yaml.unsafe_load(payload)                            # NEVER do this with a file you did not write: shown once, in a scratch folder
    assert os.path.isdir(marker)

# 3. even the safe loader reads YAML 1.1: plain words become other types
assert yaml.safe_load("on: push") == {True: "push"}                 # the key `on` is the boolean True (a GitHub workflow file has this key)
assert yaml.safe_load("python-version: [3.10, 3.11]") == {"python-version": [3.1, 3.11]}     # 3.10 is the number 3.1
assert yaml.safe_load("country: NO") == {"country": False}                                   # the "Norway problem"
print("safe_load: on ->", yaml.safe_load("on: push"), "| 3.10 ->", yaml.safe_load("[3.10]"), "| NO ->", yaml.safe_load("[NO]"))
```

The consequence for the lab: a workflow's Python versions must be *quoted strings* (`"3.10"`: a quoted version is a string in every parser, so the question of how a particular service reads the unquoted form does not arise), and the gate, which uses PyYAML, looks for the key `on` as `True`. The same habit covers every parser at the boundary: bound the size, use the loader that builds only data, and check the *type* of everything you read from it.

A third habit is about what you *say* back. A diagnostic that quotes the input hands the sender a reflection primitive and puts their text into your logs. `authwatch` reports a **code** and a **line number** and never a character of the line; the same rule was applied to errors in PY-M10.

## 7. The command line is a contract (LO5)

Scripts call your tool; shells chain it; schedulers read its exit status. Those are interfaces, and each has a convention.

| Interface | Convention in `authwatch` |
|---|---|
| standard output | the result, only the result (so `authwatch scan ... > report.json` works) |
| standard error | diagnostics, one warning per run for skipped lines, structured logs with `-v`; never a character of the input |
| exit status | 0 finished; 1 findings (only with `--fail-on-findings`); 2 wrong command line or unusable rules; 3 unreadable or corrupt input, failed output, too many bad lines; 130 interrupted |
| files | written atomically (temporary file in the same folder, then rename) with mode `0600` |

Two behaviours are rarely taught and always met in production. The first is a **closed pipe**: in `authwatch scan huge.jsonl | head -1` the reader leaves after one line and the next write raises `BrokenPipeError`; an unguarded tool prints a traceback into the operator's terminal. The second is **Ctrl-C**: an uncaught `KeyboardInterrupt` ends the process *by the signal*, which the parent sees as a negative status, not as the conventional 130. The block runs both against small child programs.

```python run
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

UNGUARDED = "for i in range(200000):\n    print('line', i)\n"
GUARDED = """import os, sys
try:
    for i in range(200000):
        print('line', i)
    sys.stdout.flush()
except BrokenPipeError:
    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())     # the reader went away: leave quietly
"""
LATER = "print('tail')\n"                                              # one more write to standard output after the guarded block
SWALLOWED = GUARDED.replace("os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())", "pass")


def closed_pipe(code: str):
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child.stdout.close()                                  # the reader leaves at once
    _, err = child.communicate(timeout=60)
    return child.returncode, err


rc, err = closed_pipe(UNGUARDED)
assert rc != 0 and b"BrokenPipeError" in err
print("unguarded: exit", rc, "and a traceback" if b"Traceback" in err else "and a message")
rc, err = closed_pipe(GUARDED)
assert rc == 0 and err == b""
print("guarded:   exit 0, silent")
rc_pass, err_pass = closed_pipe(SWALLOWED + LATER)             # catching the error is not enough if anything writes later
rc_redirect, err_redirect = closed_pipe(GUARDED + LATER)       # pointing the descriptor at the null device is
assert rc_pass != 0 and b"BrokenPipeError" in err_pass
assert rc_redirect == 0 and err_redirect == b""
print("a later write after `except: pass`: exit", rc_pass, "| after the redirect: exit 0, silent")

WAIT = "import sys, time\n{body}"
SLEEP = "    for _ in range(600):\n        time.sleep(0.1)\n"       # short sleeps: a signal that arrives early is noticed at the next one


def interrupted(code: str) -> int:
    child = subprocess.Popen([sys.executable, "-c", WAIT.format(body=code)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert child.stdout.readline().strip() == b"ready"
    child.send_signal(signal.SIGINT)
    child.communicate(timeout=60)
    return child.returncode


if os.name != "nt":
    plain = interrupted("print('ready', flush=True)\nfor _ in range(600):\n    time.sleep(0.1)\n")
    handled = interrupted("try:\n    print('ready', flush=True)\n" + SLEEP + "except KeyboardInterrupt:\n    sys.exit(130)\n")
    print("uncaught Ctrl-C:", plain, "| handled:", handled)
    assert plain == -signal.SIGINT and handled == 130

# an output file: writing in place leaves half a report after a failure, a rename never does
with tempfile.TemporaryDirectory() as folder:
    target = Path(folder) / "report.txt"
    target.write_text("old report\n")
    try:
        with open(target, "w") as handle:
            handle.write("new report, first half\n")
            raise RuntimeError("the run failed half way")
    except RuntimeError:
        pass
    assert target.read_text() == "new report, first half\n"       # the old report is gone and the new one is incomplete
    target.write_text("old report\n")
    tmp = Path(folder) / ".report.tmp"
    try:
        tmp.write_text("new report, first half\n")
        raise RuntimeError("the run failed half way")
    except RuntimeError:
        tmp.unlink()
    assert target.read_text() == "old report\n"                   # a failed run leaves the previous report untouched
    print("in place: report destroyed; temporary file and rename: report intact")
```

## 8. A supply chain you can check, and a pipeline you can trust (LO4, LO6)

A package has three kinds of risk beyond its own code: what it *depends on*, what it *ships*, and what *builds and publishes* it.

**Dependencies.** A lock file pins the exact version of everything the application needs at run time (`PyYAML==6.0.3`). Three checks follow: every runtime requirement of the wheel has an exact pin; no pin is in an advisory's affected range; the pins and the metadata agree. With network access you would run a real scanner (for example `pip-audit` or an OSV-based tool); the lab gate runs the *mechanism* offline against a small file of **synthetic** advisories so that the exercise is deterministic and no network is needed. The block shows the comparison.

```python run
import re

ADVISORIES = [{"id": "SYN-1", "package": "pyyaml", "affected": "<6.0"}, {"id": "SYN-2", "package": "pyyaml", "affected": ">=6.0,<6.0.1"}]


def version_tuple(text):
    return tuple(int(part) for part in re.findall(r"[0-9]+", text)[:4])


def affected(version, spec):
    have = version_tuple(version)
    for clause in spec.split(","):
        op, want = re.fullmatch(r"(<=|>=|<|>|==)([0-9.]+)", clause.strip()).groups()
        want = version_tuple(want)
        if not {"<": have < want, "<=": have <= want, ">": have > want, ">=": have >= want, "==": have == want}[op]:
            return False
    return True


def findings(lock_text):
    pins = dict(line.split("==") for line in lock_text.splitlines() if line.strip() and not line.startswith("#"))
    return [(name, version, a["id"]) for name, version in pins.items() for a in ADVISORIES if a["package"] == name.lower() and affected(version, a["affected"])]


assert findings("PyYAML==6.0.3\n") == []
assert findings("PyYAML==5.4.1\n") == [("PyYAML", "5.4.1", "SYN-1")]
assert findings("PyYAML==6.0\n") == [("PyYAML", "6.0", "SYN-2")]
assert version_tuple("6.0.12") > version_tuple("6.0.9")                  # compare numbers, not strings: "6.0.9" > "6.0.12" as text
print("lock file checked against", len(ADVISORIES), "advisories")
```

**The pipeline.** A workflow file is code that runs with credentials. Four rules follow from GitHub's own guidance (the *Secure use reference*, fetched 2026-10-15; R-101) and each is checked by gate G09:

| Rule | Why | What the page says |
|---|---|---|
| a token with the least permission (`permissions: {contents: read}` at the top) | a compromised step can do only what the token can | "make sure that the `GITHUB_TOKEN` is granted the minimum required permissions" |
| every `uses:` pinned to a full commit SHA | a tag can be moved to different code; a SHA cannot | "Pin references to actions to a commit SHA in your workflow files" (and check the SHA comes from the action's own repository, not a fork) |
| no untrusted text expanded inside `run:` | `${{ github.event.pull_request.title }}` becomes part of the script | "set the value of the expression to an intermediate environment variable" |
| no `pull_request_target` for a check workflow | it runs with secrets in the context of the base branch | "Avoid using the `pull_request_target` workflow trigger if it's not necessary" |

A fifth rule comes from the action itself: `actions/checkout` stores the token in the local git configuration by default (`persist-credentials` defaults to true; its README says the token is removed in post-job cleanup and tells you to set `false` to opt out), so a check workflow that never pushes should opt out. The reference workflow of the lab pins `actions/checkout` to `3d3c42e5aac5ba805825da76410c181273ba90b1` (tag v7.0.1) and `actions/setup-python` to `5fda3b95a4ea91299a34e894583c3862153e4b97` (tag v7.0.0); both were resolved from the actions' own repositories on 2026-10-15 and must be looked up again when you write a workflow, because they are facts about a day.

The block applies the structural rules to a workflow as data, which is what the gate does. It also shows why they must be checked on the *parsed* file: the key `on` is read as `True` and a version written without quotes is a float.

```python run
import re

import yaml

GOOD = """
name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - run: python scripts/check.py
"""
BAD = GOOD.replace("pull_request:", "pull_request_target:").replace("contents: read", "contents: write").replace('["3.11", "3.12", "3.13", "3.14"]', "[3.10, 3.11]").replace(
    "3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1", "v4").replace("- run: python scripts/check.py", '- run: echo "${{ github.event.pull_request.title }}"')
SHA = re.compile(r"[0-9a-f]{40}")


def problems(text):
    data = yaml.safe_load(text)
    out = []
    triggers = data.get("on", data.get(True))                         # YAML 1.1 reads `on` as True
    if "pull_request_target" in triggers:
        out.append("pull_request_target")
    if data.get("permissions") != {"contents": "read"}:
        out.append("permissions")
    for job in data["jobs"].values():
        for version in job["strategy"]["matrix"]["python-version"]:
            if not isinstance(version, str):
                out.append(f"unquoted version {version!r}")
        for step in job["steps"]:
            ref = str(step.get("uses", "@")).split("@", 1)[1]
            if "uses" in step and not SHA.fullmatch(ref):
                out.append(f"unpinned action {ref}")
            if re.search(r"\$\{\{\s*github\.event\.", str(step.get("run", ""))):
                out.append("injection")
    return out


assert yaml.safe_load(GOOD)[True] == {"pull_request": None} and "on" not in yaml.safe_load(GOOD)
assert problems(GOOD) == []
print(problems(BAD))
assert set(problems(BAD)) == {"pull_request_target", "permissions", "unquoted version 3.1", "unquoted version 3.11", "unpinned action v4", "injection"}
```

## 9. Operating notes (LO5, LO6)

- **Time is UTC and explicit.** The handbook's alert uses `datetime.now()`: naive local time. `authwatch` accepts and writes only UTC with a trailing `Z`; `datetime.UTC` (3.11+) is the constant.
- **Logs name events, not data.** `scan.file`, `scan.bad_line` (a line *number* and a code), `scan.done` (counts). Nothing a sender typed.
- **Resources are bounded.** A line, a rules file, the state kept per source: each has a number in the specification and a test.
- **The README is part of the interface.** It documents every option and exit code, what the tool does *not* protect (a stolen valid key, transport security, a flood in front of it) and the one command a contributor runs. The gate checks the headings and that every option is mentioned.
- **One command.** `python scripts/check.py` runs lint, types, tests with coverage and a build; the pipeline runs exactly that. A green run on a laptop and a red one in the pipeline means the pipeline is doing something the laptop is not, and that is a defect in the setup.

## 10. What differs between Python versions (executed)

The lesson ran on five interpreters. Most of what `authwatch` uses is the same everywhere: `tomllib` (3.11+), `datetime.UTC` (3.11+), `json`, `gzip`, `argparse`. One difference was found while writing the specification, and it is the reason the specification says that the text form of an IPv4-mapped address is **not specified**.

```python run
import ipaddress
import sys

import tomllib  # noqa: F401 - present from 3.11
from datetime import UTC, datetime

mapped = ipaddress.ip_address("::ffff:1.2.3.4").compressed
print(sys.version.split()[0], "text form of ::ffff:1.2.3.4 ->", mapped)
assert mapped in {"::ffff:1.2.3.4", "::ffff:102:304"}                  # CPython releases differ: one form on 3.11.17, 3.13, 3.14 and 3.15, the other on 3.12.3
assert ipaddress.ip_address("2001:DB8:0:0:0:0:0:1").compressed == "2001:db8::1"      # an ordinary address is stable everywhere
assert datetime(2026, 10, 14, tzinfo=UTC).isoformat() == "2026-10-14T00:00:00+00:00"
```

The specification therefore fixes what every interpreter agrees on (lower case, zeros compressed) and says nothing about the rest. The general rule: a contract may only promise behaviour that you have *executed* on every version you support.

## 11. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 93 to 98 | "Real-time Python project": a log monitor (`reader`, `analyzer`, `alert`, `config`, `main`), a folder structure and a main loop; the claim that it "could run in a SOC, a server, a DevOps environment, a cloud system" (98) | section 2 runs it and finds seven defects (F-PYH-016); the whole lab rebuilds the idea as `authwatch` with a specification, structured input, a package, tests and a pipeline |
| 98 to 101 | Builder, Adapter and Facade patterns with mutable instance state | not carried as patterns; the value types and composition are PY-M12 |
| 101 to 102 | "Robust code" and "security best practices" as bullet lists (`bandit`, `pip-audit`) | sections 6 and 8: every bullet that can be tested is a gate (ruff's `S` rules are the `bandit` family; the dependency check is a mechanism, with `pip-audit` named for network use) |
| 102 to 103 | Interview preparation: questions and one-line answers | not carried; the quiz and rubric of this module replace them |
| 103 to 104 | Module summary and a list of "everything you learned" | not carried: a list of topics is not evidence of a skill |
| 104 to 106 | Assignments: "build your own log analyzer", a calculator, a class, a decorator, a download with threads; a list of "bonus resources" | replaced by one assignment with a specification, acceptance criteria and checks |
| 646 to 650 | Module 8 interview questions, 50 questions across the book | not carried; the other modules teach the skills the questions ask about |
| 651 to 654 | Back matter: a global ecosystem message and a founder's message | not carried: not instruction |

## 12. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| coding before the contract is written | two people disagree about what "done" means in week three | specification first, with a decision for every row of the characterisation |
| a flat layout and a green test run | the wheel is broken and nobody notices | `src` layout; install the wheel in a scratch environment and run it from elsewhere |
| the version in two places | the wheel says 1.0.1, the program says 1.0.0 | one source of truth and a check |
| coverage as the goal | 100 percent and the boundary mistakes still pass | measure with mutants; test the edges named in the specification |
| tests that import private modules | the suite cannot be run against another implementation and breaks at every refactoring | test the public interface |
| `for line in stream` on untrusted input | one long line exhausts memory | bounded reads |
| `yaml.load` or `unsafe_load` | a configuration file runs code | `safe_load`, and check the types of what comes out |
| `python-version: [3.10]` | a YAML 1.1 parser such as PyYAML hands over the number 3.1, not the text `3.10` (how GitHub's own parser reads it was not verified) | quote versions: a quoted version is a string in every parser |
| an action by tag, a token with write access | a moved tag or a compromised step controls the repository | pin to a SHA; `permissions: {contents: read}` |
| `${{ github.event... }}` inside `run:` | script injection | pass it through `env:` |
| a diagnostic that quotes the input | reflected text and secrets in logs | codes and line numbers |
| a traceback on a closed pipe or on Ctrl-C | noise in the operator's terminal, a status nobody can interpret | handle both, exit 0 and 130 |
| an output file written in place | half a report after a crash | temporary file and rename, mode `0600` |
| a promise the interpreter does not keep | an assertion that passes on one patch release only | promise only what you executed everywhere |

## 13. Check yourself

1. The handbook's monitor raises 96 alerts for 100 identical error lines. State the rule it implements and the rule it should implement, in one sentence each.
2. Your tests reach 100 percent branch coverage and a colleague changes `>=` to `>` in the expiry check without any test failing. What do you add, and why does coverage not show the gap?
3. Why can a flat project pass its tests and still produce a wheel that cannot be imported?
4. The gate parses a workflow with PyYAML and finds `python-version: [3.10, 3.11, 3.12]`. What does the parser hand over for the first entry, and what is the repair?
5. Name three reasons the diagnostic for a rejected input line contains a number and a code but not the line.
6. `authwatch scan big.jsonl | head -1` prints a traceback. Which exception, why, and how does the tool leave quietly?

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 14. Sources and verification trail

- Every code block of this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 (R-101; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). The handbook's log monitor (pages 93 to 97) was executed as printed (section 2); the 96-alert count, the substring matches, the missed events, the naive time and the missing folder are results of that run.
- GitHub Actions: <https://docs.github.com/en/actions/reference/security/secure-use> (pinning actions to a commit SHA, least-privilege `GITHUB_TOKEN`, script injection and the intermediate environment variable, `pull_request_target`), fetched 2026-10-15. The `persist-credentials` default and its behaviour are from the `action.yml` and README of `actions/checkout` at tag v7.0.1 (commit 3d3c42e5aac5ba805825da76410c181273ba90b1); `actions/setup-python` tag v7.0.0 resolves to commit 5fda3b95a4ea91299a34e894583c3862153e4b97 (read from the actions' public repositories on 2026-10-15).
- Tool versions: coverage 7.16.2 and types-PyYAML 6.0.12.20260906 were the newest releases on PyPI on 2026-10-15; the other pins are those of earlier modules (R-100 and the baseline in `docs/research/TECHNOLOGY_BASELINES_2026.md`). PyYAML's YAML 1.1 behaviour (section 6) is executed, not cited.
- Handbook corrections: finding F-PYH-016 (a project presented as production-grade that alerts on every line after the threshold, matches substrings of prose, uses naive time, writes to a folder nobody creates and has no tests, types, package or pipeline).
- Not verified here and therefore not claimed: how GitHub's own workflow parser reads an unquoted `3.10` or the key `on` (the lesson and the gate use PyYAML, which reads YAML 1.1), Windows and macOS behaviour (signals, file modes and `os.replace` differ; the gate skips the POSIX signal check on Windows), the behaviour of a real GitHub-hosted runner (the labs never run a pipeline; the gate checks the workflow file's structure only, and cannot check that a pinned SHA exists), the real-vulnerability status of any dependency (the advisories of the lab are synthetic), reproducible builds, signing and provenance of artefacts, and any property of a deployment.
