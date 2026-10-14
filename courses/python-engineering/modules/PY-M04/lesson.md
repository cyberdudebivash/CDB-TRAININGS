---
id: PY-M04
title: "Environments, dependencies and packaging (pyproject, build)"
course: COURSE-PY-ENG
level: 2
audience: "Developers and operations staff who need to ship Python code that installs the same way on every machine"
prerequisites:
  - "PY-M01 and PY-M02, or equivalent: you can write modules and functions and run tests with pytest"
  - "Python 3.11 or newer with `venv` and `pip` (labs executed on 3.11, 3.12 and 3.13; see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "Packages `build` and `setuptools` installed (labs/requirements.txt); the labs install and build offline"
estimated_time_hours: {lesson: 2.0, guided_lab: 2.0, independent_lab: 2.0, total: 6.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "supported 3.11-3.15 (R-005)", pip: "26.2.1 (PyPI, 2026-08-04)", setuptools: "84.0.0 in the executed probe; guide example requires >= 77.0.3 (R-079)", specifications: "PyPA pages read 2026-10-14 (R-047, R-077, R-078, R-079)"}
last_verified: 2026-10-14
---

# PY-M04 - Environments, dependencies and packaging

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Create and use an isolated virtual environment and explain which interpreter and packages it uses. |
| **LO2** | Declare a project's metadata, dependencies and console command in `pyproject.toml` without a `setup.py`. |
| **LO3** | Build a source distribution and a wheel with `python -m build` and inspect what each contains. |
| **LO4** | Install the wheel into a clean environment, run its command and verify the result with `pip check`. |
| **LO5** | Separate runtime dependencies, optional extras and development dependency groups, and say which tool installs each. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

"It works on my machine" is almost always a packaging statement: the code ran against whatever happened to be installed. A package that builds
from one declarative file, installs into an empty environment and runs from there has *proved* it does not depend on anything undeclared.

The 2025 handbook this module replaces teaches packaging as four steps ending in `python setup.py sdist` and a three-command virtual-environment
routine (F-PYH-003). That advice is out of date, and it is worth being exact about how:

- The Python Packaging User Guide states that using `setup.py` as a command-line tool is deprecated and that commands such as `install`, `sdist` and `bdist_wheel`
  must not be run any more; builds go through `python -m build` and a `pyproject.toml` `[build-system]` table (R-006).
- On setuptools 84.0.0 the old commands **still run**: `setup.py sdist`, `bdist_wheel` and `install` exit 0 (the last two print deprecation notices), while `setup.py test`
  is an invalid command (executed probe `setuptools-setup-py-commands`, 2026-10-14). So legacy tutorials do not fail loudly; they fail by teaching a build you cannot rely on.

## 2. Isolated environments (LO1)

A virtual environment is a directory containing (or pointing to) an interpreter plus its own `site-packages`. Installing into it cannot change another project or the system Python.
Always call pip through the interpreter you mean: `python -m pip install ...` guarantees the package lands in *that* interpreter's environment.

```python run
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    env_dir = Path(tmp) / "env"
    venv.create(env_dir, with_pip=False)
    python = env_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    probe = "import sys; print(sys.prefix != sys.base_prefix)"
    answer = subprocess.run([str(python), "-c", probe], capture_output=True, text=True, check=True).stdout.strip()
    assert answer == "True"                                 # inside a venv the prefix differs from the base interpreter's
    outside = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True).stdout.strip()
    print("venv:", answer, "| the interpreter running this lesson is itself a venv:", outside)
```

You do not have to *activate* an environment to use it: running `env/bin/python -m pip ...` (Windows: `env\Scripts\python`) is enough. Activation only changes your shell's `PATH`.

## 3. Describe the project in pyproject.toml (LO2)

`pyproject.toml` has three jobs, each in its own table: `[build-system]` says how to build, `[project]` is the metadata every tool reads, and `[tool.*]` holds settings for one tool.

```toml
[build-system]
requires = ["setuptools >= 77.0.3"]          # the packaging guide's example for setuptools (R-079)
build-backend = "setuptools.build_meta"

[project]
name = "tinycsv"
dynamic = ["version"]                          # filled in by the backend, see [tool.setuptools.dynamic]
description = "Summarise a CSV file"
readme = "README.md"
requires-python = ">= 3.11"
license = "LicenseRef-Training-Example"        # an SPDX expression string; the old {file=..} table form is deprecated (R-079)
license-files = ["LICENSE"]
dependencies = []

[project.scripts]                              # becomes the command `tinycsv-summary`
tinycsv-summary = "tinycsv.cli:main"

[tool.setuptools.dynamic]
version = { attr = "tinycsv.__version__" }     # one place defines the version

[tool.setuptools.packages.find]
include = ["tinycsv*"]                         # ship the package, not tests/
```

Three details cause most packaging bugs:

1. **Which packages go into the wheel.** Automatic discovery that includes everything will ship your `tests/` package too (the labs' legacy project does exactly this). Say what to include.
2. **Where the version lives.** Duplicating it in `setup.py` and `__init__.py` guarantees a mismatch one day. Read it from one place.
3. **What `requires-python` promises.** It is a statement about the *oldest* interpreter you test on. Supported CPython versions are 3.11 to 3.15 on 2026-10-14 and 3.10 ended on 2026-10-01 (R-005).

```python run
import tomllib

TEXT = '''
[build-system]
requires = ["setuptools >= 77.0.3"]
build-backend = "setuptools.build_meta"

[project]
name = "tinycsv"
dynamic = ["version"]
requires-python = ">= 3.11"
license = "LicenseRef-Training-Example"

[project.scripts]
tinycsv-summary = "tinycsv.cli:main"
'''
data = tomllib.loads(TEXT)                       # tomllib is in the standard library from Python 3.11
assert data["build-system"]["build-backend"] == "setuptools.build_meta"
assert data["project"]["scripts"]["tinycsv-summary"] == "tinycsv.cli:main"
assert isinstance(data["project"]["license"], str)   # SPDX expression, not the deprecated table
```

## 4. Build an sdist and a wheel (LO3)

`python -m build` reads `[build-system]`, creates an isolated environment with the declared requirements, and produces two files in `dist/`:
a **source distribution** (`.tar.gz`: your sources plus metadata, so anyone can rebuild) and a **wheel** (`.whl`: a zip file that installers unpack directly).
The labs use `--no-isolation` so they run offline with the tools you already installed; in normal use leave isolation on.

```python run
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PYPROJECT = '''[build-system]
requires = ["setuptools >= 77.0.3"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-pkg"
version = "0.1.0"
requires-python = ">= 3.11"

[tool.setuptools.packages.find]
include = ["demo_pkg*"]
'''

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "demo_pkg").mkdir()
    (root / "demo_pkg" / "__init__.py").write_text('"""demo"""\n', encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", str(root / "dist"), str(root)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    wheel = next((root / "dist").glob("*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    assert "demo_pkg/__init__.py" in names
    assert not any(n.startswith("tests/") for n in names)       # include = [...] kept the tests out
    print(wheel.name, "->", len(names), "files")
```

A wheel is just a zip file: `python -m zipfile -l dist/*.whl` lists it. Reading the listing is a habit worth building - it is how you find a missing data file or an accidentally shipped test directory.

## 5. Install in a clean environment and verify (LO4)

A build is proven only when something *outside the source tree* uses it. The check has four parts: create an empty environment, install the wheel (the lab uses `--no-index --no-deps` so nothing is fetched),
run the installed command from a different directory, and run `python -m pip check`, which reports installed packages whose declared requirements are missing or conflicting.

Run the command from a directory that is **not** your project. If the import works only from the project root, you were importing the source tree, not the installed package.
Print `package.__file__` once: it should point into the environment's `site-packages`.

## 6. Three kinds of dependencies (LO5)

| Kind | Declared in | Installed by | Use it for |
|---|---|---|---|
| Runtime | `[project] dependencies` | Always installed with the package | What the code imports to do its job |
| Optional extra | `[project.optional-dependencies]` | `pip install "pkg[extra]"` by the *user* | Features some users want (a prettier output library) |
| Development group | `[dependency-groups]` | `pip install --group NAME` by *developers* | Tests, linters, docs - never installed by users of the package |

Dependency groups are an interoperability specification (PEP 735; R-078): a table named `dependency-groups` whose keys are group names and whose values are lists of requirement strings,
and a group can include another with `{include-group = "name"}`. pip 26.2.1 lists `--group` among its install options (executed `pip install --help`, 2026-10-14).

```python run
import tomllib

GROUPS = tomllib.loads('''
[dependency-groups]
test = ["pytest >= 8"]
lint = ["ruff"]
dev = [{ include-group = "test" }, { include-group = "lint" }]
''')["dependency-groups"]


def flatten(name, seen=()):
    assert name not in seen, "dependency groups must not form a cycle"
    out = set()
    for item in GROUPS[name]:
        out |= flatten(item["include-group"], seen + (name,)) if isinstance(item, dict) else {item}
    return out


assert flatten("dev") == {"pytest >= 8", "ruff"}
```

Why not `requirements.txt`? It is a *file format for one installer*, it cannot say how a package is built, and it mixes "what the code needs" with "what a developer uses". A lock file (an exact, reproducible set of
versions) answers a different question: PyPA lists an interoperable lock-file specification, `pylock.toml`, and pip 26.2.1 has a `pip lock` command (executed `pip lock --help`); tool support differs, so check yours before relying on it. This module does not teach a lock workflow.

## 7. Single-file scripts: inline metadata

A script that needs a library can carry its own requirements in a comment block, so a tool can create the right environment before running it (PEP 723; R-077). The block starts with `# /// script`,
ends with `# ///`, and contains TOML (`requires-python`, `dependencies`). The specification publishes the regular expression readers use:

```python run
import re
import tomllib

REGEX = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"   # from the PyPA specification (R-077)

SCRIPT = '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "rich>=13",
# ]
# ///

print("hello")
'''
blocks = [m for m in re.finditer(REGEX, SCRIPT) if m.group("type") == "script"]
assert len(blocks) == 1
content = "".join(line[2:] if line.startswith("# ") else line[1:] for line in blocks[0].group("content").splitlines(keepends=True))
meta = tomllib.loads(content)
assert meta["requires-python"] == ">=3.11" and meta["dependencies"] == ["rich>=13"]
```

pip 26.2.1 offers a `--requirements-from-script` option (listed in `pip install --help`); it is not the only consumer of the format.

## 8. What changed since the 2025 handbook

Verified on 2026-10-14 (register: `docs/research/research_register.yaml`; probes: `docs/research/data/api_probes_2026-10-14.json`):

| 2025 handbook | Now |
|---|---|
| `python setup.py sdist` is the packaging command (p. 64) | Deprecated as a CLI (R-006). On setuptools 84.0.0 `sdist`, `bdist_wheel` and `install` still run (the last two with deprecation notices) and `setup.py test` is invalid (executed). Use `python -m build`. |
| Four steps ending in "Add setup.py" (p. 63-64) | A `pyproject.toml` with `[build-system]` and `[project]` (R-079); the build backend fills in dynamic fields. |
| `python -m venv env; pip install -r requirements.txt` | Still valid for applications, but call `python -m pip`, and keep development tools in `[dependency-groups]` (R-078). |
| "Python 3.10+" as the baseline (p. 220) | 3.10 reached end of life on 2026-10-01; supported versions are 3.11 to 3.15 (R-005). |
| License as a free-text field or a table | An SPDX expression string plus `license-files` (R-079). The table form is deprecated. |
| No lock files, no script metadata | Interoperable specifications exist for dependency groups, lock files and inline script metadata (R-047, R-077, R-078). |

## 9. Common misconceptions

| Misconception | Reality |
|---|---|
| "A virtual environment is a copy of Python." | It is a small directory that points at a base interpreter and has its own `site-packages`. |
| "If the tests pass in the repo, the package works." | Tests that import from the source tree prove nothing about the installed wheel. Test the install in an empty environment. |
| "`find_packages()` ships exactly my code." | It ships every directory that has an `__init__.py`, including `tests/`. Declare what to include. |
| "`requirements.txt` defines my project." | It lists what one installer should fetch; project metadata belongs in `pyproject.toml`. |
| "I need `pip install -e .` to import my package." | Editable installs are a development convenience; the proof of packaging is the non-editable install of the built wheel. |

## 10. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO4) | Modernise the legacy `tinycsv` project: add `pyproject.toml`, remove `setup.py`, build, install into a clean environment, run | `lab-guided/README.md` |
| Independent lab (LO2, LO5) | Package `logslice` from a specification: src layout, extra, dependency groups, inline script metadata | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 11. Summary

- A project is described by `pyproject.toml`; `python -m build` turns it into an sdist and a wheel.
- Prove a build by installing the wheel into an empty environment and running the command from somewhere else.
- Keep runtime dependencies, optional extras and development groups apart; pip installs each in a different way.
- Declare what goes into the wheel, read the version from one place, and test on the oldest Python you claim to support.

## References

- Python Packaging User Guide: *Is setup.py deprecated?* (R-006) and *Writing your pyproject.toml* (R-079).
- PyPA specifications: index (R-047), *Dependency Groups* (R-078), *Inline script metadata* (R-077).
- Python Developer's Guide, *Status of Python versions* (R-005); registry snapshot of 2026-10-14 (R-045).
- Executed probe: `setuptools-setup-py-commands`. Findings addressed: F-PYH-003 (packaging taught as `python setup.py sdist`), F-PYH-007.
