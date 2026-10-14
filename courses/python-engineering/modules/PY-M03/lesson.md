---
id: PY-M03
title: "Types, modules and project layout"
course: COURSE-PY-ENG
level: 2
audience: "Developers and analysts turning working scripts into packages that other people can read, check and reuse"
prerequisites:
  - "PY-M02 (tests with pytest) and PY-M01, or equivalent"
  - "Python 3.11 or newer; the packages in labs/requirements.txt (pytest, mypy)"
  - "No account, network access after installation, or cost is needed"
estimated_time_hours: {lesson: 2.0, guided_lab: 2.0, independent_lab: 2.0, total: 6.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "supported 3.11-3.15 (R-005); annotations are evaluated lazily from 3.14 (R-046, executed here)", mypy: "2.4.0 (PyPI, released 2026-10-01; executed)", pytest: "9.1.1 (PyPI, 2026-06-19)"}
last_verified: 2026-10-14
---

# PY-M03 - Types, modules and project layout

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Annotate functions and data with current type syntax and explain what annotations do and do not do at run time. |
| **LO2** | Run a static type checker in strict mode, read its errors and fix the cause instead of silencing it. |
| **LO3** | Split a script into modules with a small public interface and no circular imports. |
| **LO4** | Choose between a `src` layout and a flat layout and explain how each changes what your tests import. |
| **LO5** | Run the type check and the tests together as one command and keep both green. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

A script that works on today's sample file is the start of a program, not the end. Two things make it safe to change: a **type checker** that finds a whole class of mistakes before the code runs, and a **package structure** that keeps
each idea in one place. The 2025 handbook shows type hints in four lines (page 85) and says they give "bug detection"; it never shows a checker, and on the previous page it says dataclasses provide "type validation" - which they do not, as the next section shows.
Its tooling pages name no type checker, linter or formatter workflow at all (change record MC-PYH-15).

## 2. Annotations are metadata, not enforcement (LO1)

Python records annotations and ignores them when the program runs. A function annotated to return a string can return a number; a dataclass field annotated `int` accepts text. Only a separate tool (a type checker) reads annotations and complains.

```python run
from dataclasses import dataclass


def double(x: int) -> str:                 # the annotation is a claim, not a check
    return x * 2                          # returns an int although `-> str` says otherwise


@dataclass
class User:
    name: str
    age: int


assert double(3) == 6 and double.__annotations__ == {"x": int, "return": str}
user = User("ada", "thirty-six")          # no error: dataclasses do not validate types
assert user.age == "thirty-six"
```

The handbook's list of what `@dataclass` provides ("init, repr, eq, type validation") is therefore wrong on the last item: the decorator generates `__init__`, `__repr__` and `__eq__` (among others) and validates nothing.
If you need validation at run time, you need code that does it (for example a library such as pydantic, which later modules use) or you convert at the boundary.

One run-time detail changed recently. Until Python 3.13, an annotation that names a class **before it is defined** (such as `def link(nxt: Node | None)` inside `class Node`) raises `NameError` when the function is defined, unless the module starts with `from __future__ import annotations` or the name is quoted.
From 3.14 annotations are evaluated lazily (PEP 649, R-046), and the same code works. The next block checks this on whichever interpreter runs the lesson:

```python run
import sys

SOURCE = '''
class Node:
    def __init__(self, nxt: Node | None = None) -> None:
        self.nxt = nxt
'''
try:
    exec(SOURCE, {})
    accepted = True
except NameError:
    accepted = False
assert accepted == (sys.version_info >= (3, 14)), (sys.version_info, accepted)    # lazy evaluation starts with 3.14
exec("from __future__ import annotations\n" + SOURCE, {})                       # still accepted on every supported version tested here
```

If your code must run on 3.11 to 3.13 as well, keep the `from __future__ import annotations` line at the top of modules that use forward references.

## 3. Types that say something (LO1)

Current syntax (all available from Python 3.10 unless noted) reads like the data it describes:

| You mean | Write |
|---|---|
| a list of integers | `list[int]` |
| a mapping from names to numbers | `dict[str, float]` |
| a value that may be missing | `str \| None` |
| one of a few fixed texts | `Literal["asc", "desc"]` |
| a fixed record with named fields | a frozen `@dataclass` (or `TypedDict` for a JSON-shaped dictionary) |
| "anything that behaves like a sequence" | `collections.abc.Sequence[str]` (accept the general type, return the specific one) |
| a function that never returns normally | `NoReturn` |

Choose the most precise type that is still true. `dict[str, str]` for a CSV row says "everything is text", which is true of what the file contains and **hides** that a quantity should be a number (section 5). Modelling the row as a typed record forces the conversion to happen once, at the boundary.

```python run
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    sku: str
    qty: int
    price: Decimal

    @property
    def value(self) -> Decimal:
        return self.qty * self.price


row = {"sku": "A-100", "qty": "12", "price": "2.50"}                 # what a CSV reader gives you: all text
product = Product(row["sku"], int(row["qty"]), Decimal(row["price"]))    # convert once, at the boundary
assert product.value == Decimal("30.00")
try:
    product.qty = 5                                                  # frozen: cannot be changed afterwards
except AttributeError:
    pass
else:
    raise AssertionError("a frozen dataclass must reject assignment")
```

## 4. Reading what the checker says (LO2)

mypy checks the code against the annotations. Two behaviours surprise newcomers:

1. **By default mypy skips every function that has no annotations.** A completely untyped script passes with "no issues found" - which proves nothing. `--strict` turns on the checks that make types mandatory and flags untyped definitions and calls.
2. **Fix the cause.** An error is a claim about your program. Silencing it with `# type: ignore` or `cast(...)` removes the claim without removing the bug.

The block below runs mypy 2.4.0 on a small program with three real mistakes and checks the error codes it reports (messages can change between releases, error codes are stable):

```python run
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SOURCE = textwrap.dedent('''
    from dataclasses import dataclass

    @dataclass
    class User:
        name: str
        age: int

    def find(users: list[User], name: str) -> User | None:
        for u in users:
            if u.name == name:
                return u
        return None

    def shout(users: list[User]) -> str:
        return find(users, "ada").name.upper()          # the user may be missing

    def average_age(users: list[User]) -> int:
        return sum(u.age for u in users) / len(users)   # true division returns a float

    shout([User("ada", "36")])                          # the age is text
''')
UNTYPED = "def add(a, b):\n    return a + b\n\nadd(1, 'x')\n"

with tempfile.TemporaryDirectory() as tmp:
    typed = Path(tmp) / "typed.py"
    typed.write_text(SOURCE, encoding="utf-8")
    untyped = Path(tmp) / "untyped.py"
    untyped.write_text(UNTYPED, encoding="utf-8")
    run = lambda *args: subprocess.run([sys.executable, "-m", "mypy", "--no-color-output", "--show-error-codes", *args], capture_output=True, text=True, cwd=tmp)
    strict = run("--strict", str(typed))
    codes = sorted(line.rsplit("[", 1)[1].rstrip("]") for line in strict.stdout.splitlines() if "error:" in line)
    assert codes == ["arg-type", "return-value", "union-attr"], strict.stdout
    assert run(str(untyped)).returncode == 0                       # default mode: untyped functions are skipped, nothing reported
    assert run("--strict", str(untyped)).returncode == 1           # strict mode: untyped definitions are errors
```

| Code | Meaning | Usual fix |
|---|---|---|
| `union-attr` | You used a value that may be `None` (or another type) as if it were certain | Handle the missing case: test it, raise a clear error, or return early |
| `arg-type` | An argument has the wrong type | Convert at the boundary, or correct the call |
| `return-value` | The function returns something other than what it promises | Fix the computation (here `//` or `int(...)`) or the annotation |
| `no-untyped-def` | A function has no annotations (strict mode) | Annotate parameters and the return type |

## 5. Model the data accurately (LO2)

The lab's starter script keeps CSV rows as dictionaries of text and compares `p["qty"] < p["reorder_level"]`. For two strings that comparison is valid, mypy accepts it, and at run time it compares **characters**: `"9" < "10"` is false because `"9"` sorts after `"1"`.
The bug survives type checking because the type said "text". Once a typed record holds `int` fields, the conversion has to be written and the comparison becomes numeric. Types find the bugs you give them the information to find.

```python run
assert not ("9" < "10")          # text comparison: 9 is not "less than" 10
assert 9 < 10                    # numeric comparison
```

## 6. From script to package (LO3)

A package turns "one long file" into modules with one job each, plus a **public interface** - the few names users should import:

- `models.py` holds the data types; `loader.py` reads files; `stock.py` computes; `report.py` formats; `cli.py` parses arguments and prints.
- `__init__.py` imports the public names and lists them in `__all__`. `__all__` documents the interface and controls `from package import *`; it does not hide anything (Python has no enforced privacy).
- Dependencies point one way: `cli` -> `report` -> `stock` -> `models`. A **circular import** (two modules importing each other at the top) fails because one of them is only partly initialised when the other runs.

```python run
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    pkg = Path(tmp) / "cyc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from cyc.b import B\nclass A:\n    pass\n", encoding="utf-8")
    (pkg / "b.py").write_text("from cyc.a import A\nclass B:\n    pass\n", encoding="utf-8")
    broken = subprocess.run([sys.executable, "-c", "import cyc.a"], cwd=tmp, capture_output=True, text=True)
    assert broken.returncode != 0 and "circular import" in broken.stderr, broken.stderr   # ImportError: partially initialized module
    # Fix: the shared class moves to a module both can import; dependencies now point one way.
    (pkg / "base.py").write_text("class A:\n    pass\n", encoding="utf-8")
    (pkg / "a.py").write_text("from cyc.base import A\n", encoding="utf-8")
    (pkg / "b.py").write_text("from cyc.base import A\nclass B(A):\n    pass\n", encoding="utf-8")
    fixed = subprocess.run([sys.executable, "-c", "import cyc.a, cyc.b"], cwd=tmp, capture_output=True, text=True)
    assert fixed.returncode == 0, fixed.stderr
```

## 7. Layout: `src` or flat (LO4)

| Layout | Where the package lives | What happens if you run Python in the project root |
|---|---|---|
| Flat | `project/invkit/` | `import invkit` works immediately - from the *working directory copy*, installed or not |
| `src` | `project/src/invkit/` | `import invkit` fails until the package is installed (or the path is configured), so tests can only pass if the package is importable the way users will import it |

The `src` layout is a safety device: it makes "works only from my checkout" fail early. The price is one line of configuration (`pythonpath = ["src"]` for pytest, `mypy_path = "src"` for mypy, or an editable install). Tests belong **outside** the package (`tests/`), so they are not shipped in the wheel (PY-M04).

```python run
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for base in ("flat", "src"):
        pkg = root / base / ("pkg" if base == "flat" else "src/pkg")
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    flat = subprocess.run([sys.executable, "-c", "import pkg"], cwd=root / "flat", capture_output=True, text=True)
    src = subprocess.run([sys.executable, "-c", "import pkg"], cwd=root / "src", capture_output=True, text=True)
    assert flat.returncode == 0           # the working directory is on the import path
    assert src.returncode != 0 and "No module named 'pkg'" in src.stderr
```

## 8. One command for both checks (LO5)

Put the type-checker settings in `pyproject.toml` (`[tool.mypy] strict = true`, `files = ["src", "tests"]`, `mypy_path = "src"`) so every developer and the build run the same checks, and run both tools from one line:

```bash
python -m mypy && python -m pytest
```

Type-check the tests too: a test with a wrong argument type is a test that does not test what you think. Keep both green before every commit; a check nobody runs protects nothing.

## 9. What changed since the 2025 handbook

Verified on 2026-10-14 (executed in this lesson or recorded in the register):

| 2025 handbook | Now |
|---|---|
| Dataclasses provide "type validation" (p. 85) | They do not: `User("ada", "thirty-six")` succeeds (executed). Validate at run time with code or a library, and check statically with a type checker. |
| Type hints: "bug detection" with no checker named (p. 85) | Bug detection needs a checker. mypy 2.4.0 skips untyped functions by default and flags them under `--strict` (executed). Registry versions on 2026-10-14: mypy 2.4.0, pyright 1.1.414, ruff 0.17.0 (R-045). |
| `from __future__ import annotations` or quotes for forward references | Unquoted forward references work from Python 3.14 (PEP 649, R-046; executed on 3.11-3.15 here); the future import is still accepted on 3.15.0. |
| "Python 3.7+" for dataclasses | Supported CPython versions are 3.11 to 3.15; 3.10 reached end of life on 2026-10-01 (R-005). |

## 10. Common misconceptions

| Misconception | Reality |
|---|---|
| "Type hints make Python check types." | They are ignored when the program runs; only a checker reads them. |
| "mypy found nothing, so the code is typed." | Default mypy skips untyped functions. Use `--strict` and read the summary line. |
| "`# type: ignore` fixes the error." | It hides the message and keeps the bug. |
| "`__all__` makes names private." | It documents the public interface; any module can still import anything. |
| "Splitting into files fixes design." | Modules help only if each has one job and dependencies point one way. |

## 11. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Turn the untyped `inventory.py` script, whose tests fail, into a strictly typed `invkit` package | `lab-guided/README.md` |
| Independent lab (LO2-LO5) | Type and restructure a package that has circular imports and `Any`-typed code, to a specification | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 12. Summary

- Annotations are claims; a strict checker verifies them. Use `--strict`, fix causes, and never rely on a pass for untyped code.
- Model data with the most precise true type; convert once at the boundary.
- A package has one job per module, a small public interface and dependencies that point one way.
- Prefer `src` layout, keep tests outside the package, configure the checker in `pyproject.toml`, and run `mypy` and `pytest` together.

## References

- Python Developer's Guide, *Status of Python versions* (R-005); *What's New In Python 3.14* (R-046); registry snapshot of tool versions as of 2026-10-14 (R-045).
- Findings and change records addressed: F-PYH-004, F-PYH-008 (dataclasses described as validating types), MC-PYH-15 (typing and static-analysis tooling), F-PYH-007.
