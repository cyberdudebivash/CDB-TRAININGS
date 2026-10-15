---
id: PY-M01
title: "Language core and data structures"
course: COURSE-PY-ENG
level: 1
audience: "Beginners and career-changers who will write Python that processes text, files and records, and who need to know which Python they are running"
prerequisites:
  - "None beyond a computer and a text editor. Learners from COURSE-FND-DIGITAL arrive with a command line habit; others should be able to open a terminal"
  - "Python 3.11 or newer (the labs were executed on 3.11, 3.12, 3.13, 3.14 and 3.15; see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "No account, network access after installation, or cost is needed"
estimated_time_hours: {lesson: 4.0, guided_lab: 4.0, independent_lab: 4.0, total: 12.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "supported 3.11-3.15, 3.10 ended 2026-10-01 (R-005); feature availability by version executed in this lesson (R-024, R-046)", pytest: "9.1.1 (PyPI, 2026-06-19)"}
last_verified: 2026-10-14
---

# PY-M01 - Language core and data structures

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Run Python from the interpreter and from a file, read a traceback, and say which Python version and interpreter you are using. |
| **LO2** | Choose between `str`, `list`, `tuple`, `dict` and `set` for a task and use their core operations (indexing, slicing, unpacking, membership, comprehensions, sorting). |
| **LO3** | Use conditions, loops, `match` and early returns to write small functions that always return the same output for the same input. |
| **LO4** | Read and write text files safely with an explicit encoding, `pathlib` and the `json` and `csv` modules. |
| **LO5** | Implement a function from a written specification so that provided unit tests pass, working one failing test at a time. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Almost every later module in this course assumes you can read a short piece of Python and predict what it does. The 2025 handbook covers this ground in its first fifty pages with friendly explanations and many examples; this module keeps that scope and fixes three things:
the examples are **executed**, not just printed (F-PYH-004); the "which Python?" question is answered with 2026 facts (3.10 ended on 2026-10-01 and 3.15 appeared on 2026-10-09); and a few simplifications that would later mislead are corrected (for example "variables live on the stack", p. 25).
The labs ask you to make provided tests pass, which is how professional work usually arrives: a specification, some examples and a test suite.

## 2. Running Python and reading what it tells you (LO1)

You can run Python three ways: interactively (type `python` and enter lines at the `>>>` prompt), as a script (`python file.py`) and as a module (`python -m package`). The script form is the one you will use most. When something goes wrong Python prints a **traceback**: read it from the bottom.
The last line names the error type and message; the lines above it are the chain of calls that led there, the most recent call last.

```python run
import sys
import traceback

assert sys.version_info >= (3, 11)                       # the labs need 3.11 or newer
print("running", sys.version.split()[0], "from", sys.executable)


def average(values):
    return sum(values) / len(values)


try:
    average([])                                          # dividing by zero
except ZeroDivisionError:
    report = traceback.format_exc().strip().splitlines()
    assert report[-1] == "ZeroDivisionError: division by zero"       # the last line says what happened
    assert any(line.strip() == "return sum(values) / len(values)" for line in report)   # an earlier line shows where
```

Three habits save hours. Run `python --version` (or `python3 --version`) and write the number down when you ask for help. Know **which** interpreter runs your code: `sys.executable` tells you, and inside a virtual environment (PY-M04) it is the environment's copy.
And read the error message before you change anything: the common errors below each mean one specific thing.

| Error | What it means | Typical cause |
|---|---|---|
| `NameError` | A name was used before it was given a value | A typo, or a variable defined in another function |
| `TypeError` | An operation got a value of the wrong kind | Adding a number to text; calling with the wrong number of arguments |
| `ValueError` | The kind is right, the value is not | `int("abc")` |
| `KeyError` / `IndexError` | A dictionary key or list position does not exist | A misspelt key; an off-by-one |
| `AttributeError` | The object has no such attribute or method | Using a method of another type; a value that is `None` |
| `SyntaxError` | The text is not valid Python | A missing colon or bracket |

## 3. Values, types and the traps in numbers (LO2)

Every value has a type: `int`, `float`, `str`, `bool`, `None` (the "no value" value), and the collections of the next section. Two traps catch nearly everyone.

**Floats are approximations.** Computers store `float` numbers in binary, so most decimals are stored inexactly. For money and for any total you will compare with `==`, use `decimal.Decimal` (built from text, not from a float) or whole cents.

**`==` asks "equal?", `is` asks "the same object?".** Two lists with the same contents are equal and are not the same object. Use `is` only for `None` (`if x is None`).

```python run
from decimal import Decimal

assert 0.1 + 0.2 != 0.3                                   # binary floats cannot represent 0.1 exactly
assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")   # exact decimal arithmetic
assert round(2.675, 2) == 2.67                             # the stored float is just below 2.675
assert Decimal("2.675").quantize(Decimal("0.01")) == Decimal("2.68")

a = [1, 2, 3]
b = [1, 2, 3]
c = a
assert a == b and a is not b                               # equal contents, different objects
assert c is a                                              # a second name for the same list
c.append(4)
assert a == [1, 2, 3, 4]                                   # change it through one name and the other sees it

assert not [] and not "" and not 0 and not None            # empty values and zero are "false"
assert [0] and "0" and -1                                   # anything else is "true", even the text "0"
```

Names are labels, not boxes. `x = 10` binds the name `x` to an object; names live in a *namespace*, which for a module is just a dictionary you can look at:

```python run
x = 10
assert globals()["x"] == 10                                # the name x is a key in the module namespace
y = x
assert y is x                                              # two names, one object
x = 11                                                     # rebinding x does not change y
assert y == 10
```

The handbook (p. 25) says a variable is "a name on the stack" and the value "an object on the heap". That describes one implementation detail and is not part of the language: what the language guarantees is names bound to objects in namespaces.

## 4. Collections: choose the right one (LO2)

| Type | Ordered | Changeable | Duplicates | Use it for |
|---|---|---|---|---|
| `str` | yes | no (new strings are created) | yes | text |
| `list` | yes | yes | yes | a sequence you add to, sort or loop over |
| `tuple` | yes | no | yes | a fixed record such as `(x, y)`; dictionary keys |
| `dict` | insertion order | yes | keys are unique | lookup by name or id |
| `set` | no | yes | no | membership tests, removing duplicates, set arithmetic |

Core operations worth knowing by heart: indexing from 0 and from the end (`items[-1]`), slicing (`items[1:3]` excludes the end), unpacking (`first, *rest = items`), membership (`x in container`; fast for sets and dicts, a scan for lists),
comprehensions (`[f(x) for x in items if keep(x)]`) and sorting with a `key` function. `sorted` is stable: items that compare equal keep their original order, which is why you can sort by one field and then by another.

```python run
words = ["pear", "fig", "apple", "kiwi", "fig"]

assert words[1:3] == ["fig", "apple"] and words[-1] == "fig"
first, *rest = words
assert first == "pear" and rest == ["fig", "apple", "kiwi", "fig"]

assert sorted(set(words)) == ["apple", "fig", "kiwi", "pear"]                  # remove duplicates, then sort
assert sorted(words, key=len) == ["fig", "fig", "pear", "kiwi", "apple"]      # stable: 'pear' stays before 'kiwi'
assert {w: len(w) for w in words} == {"pear": 4, "fig": 3, "apple": 5, "kiwi": 4}   # later duplicates overwrite earlier keys

counts: dict[str, int] = {}
for w in words:
    counts[w] = counts.get(w, 0) + 1                                          # .get avoids a KeyError for a new word
assert counts == {"pear": 1, "fig": 2, "apple": 1, "kiwi": 1}
assert list(counts) == ["pear", "fig", "apple", "kiwi"]                       # dictionaries remember insertion order

a, b = {1, 2, 3}, {3, 4}
assert a & b == {3} and a | b == {1, 2, 3, 4} and a - b == {1, 2}
```

Two cautions. Never change a list while looping over it (build a new list instead). And a copy is not automatic: `b = a` is a second name; `b = a.copy()` or `list(a)` is a new (shallow) copy.

## 5. Control flow and small functions (LO3)

Conditions (`if`/`elif`/`else`), loops (`for`, `while`, with `break`, `continue` and the rarely used `else`), and `match` (structural pattern matching, available since Python 3.10) are enough to express most logic.
Prefer **early returns** that handle the unusual cases first so the main path stays flat, and prefer **pure functions**: the same inputs always give the same output and nothing outside the function changes. Pure functions are the easiest to test (PY-M02).

```python run
def describe(command: str) -> str:
    match command.split():
        case []:
            return "empty"
        case ["go", ("north" | "south") as direction]:
            return f"walk {direction}"
        case ["take", item, *more] if not more:
            return f"pick up {item}"
        case ["take", *_]:
            return "take one thing at a time"
        case _:
            return "unknown"


assert describe("") == "empty"
assert describe("go north") == "walk north"
assert describe("take lamp") == "pick up lamp"
assert describe("take lamp key") == "take one thing at a time"
assert describe("dance") == "unknown"


def first_even(numbers: list[int]) -> int | None:
    for n in numbers:
        if n % 2 == 0:
            return n                                   # return as soon as the answer is known
    return None                                        # say explicitly that there is none


assert first_even([3, 5, 8, 10]) == 8 and first_even([1, 3]) is None
```

## 6. Text and files (LO4)

### Text tools you will use in the labs

Most real data arrives as text, so a few string tools do a great deal of work: `strip()` removes spaces at both ends, `split(sep, maxsplit)` cuts into pieces, `partition(sep)` cuts at the **first** separator only and always returns three parts,
`startswith()` and `lower()` ask and normalise, and `"-".join(parts)` glues pieces together. For counting, `collections.Counter` is a dictionary specialised for it; ask for a fixed order yourself with `sorted(..., key=...)`, because tied counts otherwise keep first-seen order.
To check that a date is a real date, let `datetime.strptime` try to read it: it raises `ValueError` for `2026-02-30`.
When the shape of the text matters, a **regular expression** (module `re`) describes it: `[0-9]` is a digit, `+` means "one or more", `(...)` captures a piece, and `fullmatch` requires the whole text to fit. You may solve every lab without `re` by using the string tools above.

One trap deserves its own example. In Python 3 `str` patterns, `str.isdigit()`, `int()` and `datetime.strptime` accept digits from other writing systems (for example the Arabic-Indic digit three), and `\d` in a pattern matches them too. If a format means the ASCII digits 0-9, say so with `[0-9]` or the `re.ASCII` flag.

```python run
import re
from collections import Counter
from datetime import datetime

line = "  2026-10-14 12:00:01 ERROR payment failed  "
date, clock, rest = line.strip().split(" ", 2)                     # at most two cuts: three pieces
level, _, message = rest.partition(" ")                            # cut at the first space only
assert (date, clock, level, message) == ("2026-10-14", "12:00:01", "ERROR", "payment failed")
assert "a=b=c".partition("=") == ("a", "=", "b=c") and "x".partition("=") == ("x", "", "")

counts = Counter("b a b c a d".split())
assert counts["b"] == 2 and counts["zzz"] == 0                     # a missing key counts as zero
assert counts.most_common() == [("b", 2), ("a", 2), ("c", 1), ("d", 1)]    # ties keep first-seen order
assert sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) == [("a", 2), ("b", 2), ("c", 1), ("d", 1)]   # you choose the tie-break

datetime.strptime("2024-02-29", "%Y-%m-%d")                        # a leap day exists
try:
    datetime.strptime("2026-02-30", "%Y-%m-%d")
except ValueError:
    pass
else:
    raise AssertionError("2026-02-30 must be rejected")

assert re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "2026-10-14")
assert re.findall(r"[^\W\d_]+", "Don't stop: caf\u00e9 2026") == ["Don", "t", "stop", "caf\u00e9"]   # letters only, accents included
assert re.sub(r"[0-9]+$", "x", "host 10.0.0.25") == "host 10.0.0.x"

arabic_three = "\u0663"
assert arabic_three.isdigit() and int(arabic_three) == 3           # looks foreign, converts happily
assert re.fullmatch(r"\d+", arabic_three) and not re.fullmatch(r"[0-9]+", arabic_three)
assert datetime.strptime("\u0662\u0660\u0662\u0666-10-14", "%Y-%m-%d").year == 2026      # even a date can be written this way
```

### Files and encodings

A `str` is a sequence of Unicode characters; `bytes` is a sequence of numbers. A file contains bytes, so reading text means **decoding** with an encoding and writing means encoding. If you do not say which encoding, Python picks a platform default.
That default depends on the locale before Python 3.15, and from 3.15 text I/O defaults to UTF-8 (PEP 686; research register R-024). Code that must behave the same everywhere says `encoding="utf-8"` every time.

Use `pathlib.Path` for paths (it joins with `/`, knows about the platform and has `read_text`/`write_text`), a `with` block so files are closed even when an error occurs, and the `csv` and `json` modules instead of splitting text by hand.

```python run
import csv
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    note = folder / "note.txt"
    note.write_text("café\n", encoding="utf-8")                        # explicit encoding, always
    assert note.read_text(encoding="utf-8") == "café\n"
    assert note.read_bytes() == b"caf\xc3\xa9\n"                           # the same data as bytes: the accented letter takes two bytes
    assert len("café") == 4 and len("café".encode("utf-8")) == 5     # characters versus bytes

    table = folder / "people.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:           # newline="" is what the csv module expects
        writer = csv.DictWriter(handle, fieldnames=["name", "age"])
        writer.writeheader()
        writer.writerow({"name": "Ada", "age": 36})
        writer.writerow({"name": "Grace, H.", "age": 45})                   # a comma inside a value is quoted automatically
    with table.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"name": "Ada", "age": "36"}, {"name": "Grace, H.", "age": "45"}]       # everything read from a CSV is text

    payload = {"user": "ada", "tags": ["a", "b"], "active": True, "nickname": None}
    (folder / "data.json").write_text(json.dumps(payload), encoding="utf-8")
    assert json.loads((folder / "data.json").read_text(encoding="utf-8")) == payload        # None, True and lists round-trip
    assert json.loads(json.dumps({"a": (1, 2)})) == {"a": [1, 2]}            # a tuple comes back as a list: JSON has no tuples
```

Two reminders: data from files and networks is **text until you convert it** (`int(row["age"])`), and a conversion can fail, so decide what should happen with bad rows (raise a clear error, as the labs do, rather than skipping silently).

## 7. Python in 2026: which version, and what you will see in code (LO1)

Supported CPython versions on 2026-10-14 are **3.11 to 3.15**; 3.10 reached end of life on 2026-10-01 and 3.9 on 2025-10-31 (R-005). Python 3.15.0 was released on 2026-10-09 (R-024). Library support for a brand-new release lags, so pin and test on the versions you claim.
New language features appear in real code before they reach every installation, so it helps to know what is where. The block below checks which features exist on the interpreter running this lesson; the assertions encode the version table, and the lesson test suite runs them on every interpreter from 3.11 to 3.15:

```python run
import builtins
import sys

v = sys.version_info[:2]


def compiles(source: str) -> bool:
    try:
        compile(source, "<feature>", "exec")
    except SyntaxError:
        return False
    return True


assert compiles("match 1:\n    case 1:\n        pass")                      # structural pattern matching: 3.10 and later
assert hasattr(str, "removeprefix")                                          # 3.9 and later
assert compiles("t = t'hello {1}'") == (v >= (3, 14))                       # template strings (PEP 750): 3.14 and later
assert compiles("lazy import json") == (v >= (3, 15))                       # explicit lazy imports (PEP 810): 3.15 and later
assert hasattr(builtins, "frozendict") == (v >= (3, 15))                    # immutable dictionary type (PEP 814): 3.15 and later
print("features on", v, "checked")
```

You do not need the last three features for this course; you only need to recognise that code using them will not run on older interpreters, which is one reason a project states the oldest Python it supports (PY-M04).

## 8. From specification to passing tests (LO5)

Professional tasks often arrive as a specification and a failing test suite. A method that works:

1. **Read the specification twice**, then read the tests: the tests are the specification written as examples, including the edge cases (empty input, repeated items, wrong values).
2. **Pick one failing test**, run only it (`python -m pytest -k name`), read the failure, and write the smallest code that makes it pass.
3. **Run all tests** after each step so you notice breaking something that worked.
4. **Refactor last**: when everything is green, improve names and remove repetition while the tests stay green.

The lab functions are small on purpose: each needs a loop or a comprehension, one data structure and one or two edge cases.

## 9. What changed since the 2025 handbook

Verified on 2026-10-14 (executed in this lesson or recorded in the register):

| 2025 handbook | Now |
|---|---|
| Sample version output `Python 3.12.0` (p. 5), a sample rather than an error | Supported versions are 3.11 to 3.15; 3.10 ended on 2026-10-01; 3.15.0 was released on 2026-10-09 (R-005, R-024). The lesson states the version it ran on and tests it. |
| "Variables are references: stack memory holds names, heap memory holds objects" (p. 25) | The language guarantees names bound to objects in namespaces; "stack" and "heap" are implementation details (executed: `globals()["x"]`). |
| Code shown without being run | Every example in this lesson is executed by the repository tests on CPython 3.11-3.15. |
| Features presented without version limits | Template strings need 3.14, explicit lazy imports and `frozendict` need 3.15 (executed on 3.11-3.15), `match` needs 3.10. |
| Default file encoding not discussed | Pass `encoding="utf-8"`; from 3.15 text I/O defaults to UTF-8 (R-024), before that the locale decides. |

## 10. Common misconceptions

| Misconception | Reality |
|---|---|
| "`b = a` copies the list." | It adds a second name for the same list. Copy explicitly. |
| "`0.1 + 0.2` is a Python bug." | It is how binary floating point works in every language; use `Decimal` for exact decimal amounts. |
| "A CSV gives me numbers." | A CSV gives text; convert and validate. |
| "`is` and `==` are interchangeable." | `==` compares values; `is` compares identity (use it for `None`). |
| "A dictionary has no order." | Since Python 3.7 it remembers insertion order; sets still have no order you can rely on. |

## 11. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Implement five functions and one file wrapper in `datakit.py` until the provided tests pass | `lab-guided/README.md` |
| Independent lab (LO3-LO5) | Implement five log-processing functions in `logkit.py` from a specification with a few published examples; instructors run a larger hidden test suite | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 12. Summary

- Know which Python you run, and read tracebacks from the bottom.
- Floats are approximations; use `Decimal` for exact decimal amounts. `==` compares values, `is` identity.
- Pick the collection by the question you ask of it; comprehensions and `sorted(key=...)` do most of the work.
- Return early, keep functions pure, always give an encoding, and treat file contents as text until converted.
- Work from tests: one failing test at a time, all tests after each change.

## References

- Python Developer's Guide, *Status of Python versions* (R-005); *What's New In Python 3.15* (R-024) and *3.14* (R-046); registry snapshot of 2026-10-14 (R-045).
- Findings and change records addressed: F-PYH-004 (listings not executed), F-PYH-007 (assessment by recall questions only), MC-PYH-01 (language foundations kept and re-run).
