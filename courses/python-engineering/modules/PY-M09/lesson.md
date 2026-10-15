---
id: PY-M09
title: "Profiling, performance and maintainable architecture"
course: COURSE-PY-ENG
level: 3
audience: "Programmers who have finished PY-M01, PY-M02 and PY-M13 (and ideally PY-M08 and PY-M12) and now need to make a working program fast enough and keep it easy to change: measure first, find the one function that matters, fix it without changing an answer, and structure the code so that the next change is cheap"
prerequisites:
  - "PY-M01 (language core), PY-M02 (functions, errors and pytest), PY-M13 (generators and context managers); PY-M08 (statement counts and query plans) and PY-M12 (classes) help"
  - "Python 3.11 or newer; the labs and every code block of this lesson were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "pytest 9.1.1 and ruff 0.17.0 from labs/requirements.txt; no network, no account, no paid service"
estimated_time_hours: {lesson: 2.5, guided_lab: 3.0, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); behaviour of profilers, reference counting, interning and tracemalloc by version executed in this lesson (R-099)", pytest: "9.1.1", ruff: "0.17.0"}
last_verified: 2026-10-15
---

# PY-M09 - Profiling, performance and maintainable architecture

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Measure a Python program correctly: wall-clock time with `perf_counter` and `timeit` (and why the smallest of several runs), and a deterministic profile with `cProfile` and `pstats` (call counts, own time and cumulative time); name what the sampling profiler of Python 3.15 adds. |
| **LO2** | Find the function that dominates a run, predict how much fixing it can gain (and how little fixing anything else can), replace a quadratic algorithm by a linear one, and prove that no answer changed. |
| **LO3** | Measure and reduce memory with `tracemalloc`; explain reference counting, cycles, interning and `__slots__` without relying on implementation details that differ between versions. |
| **LO4** | Write performance tests that do not flake: counts instead of clocks, ratios between input sizes instead of absolute seconds, and budgets an order of magnitude away from both a good and a bad solution. |
| **LO5** | Structure a program so that it stays changeable: a core that only computes and an edge that reads and writes, one-way dependencies enforced by a test, interfaces (ports) with swappable adapters, and a linter configuration the whole team shares. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

A program that is correct on the demonstration data and unusable on the real data is the usual reason somebody opens a profiler. The usual response is worse than the problem: people rewrite the part they *think* is slow, make the code harder to read, and gain nothing. The discipline of this module is short: **measure, change one thing, measure again, keep the proof that the answers did not change.**

The 2025 handbook has a section on memory (PDF pages 56 to 57) and one on "execution optimization" (pages 79 to 80). Each claim in them is executed in this lesson on five Python versions:

- reference counting is introduced with `sys.getrefcount(x)` and no warning that the number includes the call's own reference, or that on Python 3.12 and later some objects have no counting at all (section 7);
- interning is presented as "speed optimization" with `a is b → True`; comparing strings with `is` is a bug, Python itself warns about it when the code is compiled, and which objects are shared is an implementation detail that changed between the versions tested here (section 7);
- "use PyPy, Cython, NumPy, caching, `lru_cache`" is a list of tools without a measurement that says when any of them is the answer (sections 2, 3 and 5); `lru_cache(maxsize=None)` on a recursive `fib` is shown without its cost, which is that the cache never forgets (section 5);
- `__slots__` is listed as a memory technique; it does save memory, and also removes the instance dictionary, which changes what the class can do (section 7);
- caching and generators are named as optimisations without saying how to find out whether they matter for *this* program.

The labs optimise a log-digest program (guided) and an alert-triage program (independent), and for both the checks count work instead of timing it.

## 2. Measure first (LO1)

Python gives you three clocks and one rule. The clock for intervals is `time.perf_counter()`: monotonic, the highest resolution available. `timeit` runs a statement many times to average out the noise. The rule: **a single timing proves nothing.** The same code takes different times on different runs because of the operating system, other processes, CPU frequency and caches; the *smallest* of several runs is the best estimate of the cost of the code itself, because noise only ever adds time.

```python run
import timeit

timer = timeit.Timer("sum(range(1000))")
number, total = timer.autorange()                        # grows the repeat count until a run takes at least 0.2 s
assert total >= 0.2 and number >= 1

runs = timer.repeat(repeat=5, number=number)             # five independent measurements of `number` executions each
per_call = min(runs) / number                            # the minimum is the estimate; the spread is the noise
assert 0 < per_call <= max(runs) / number
```

Three habits keep a measurement honest: measure only the code you are asking about (not `print`, not building the input), measure on input the size of the real thing (a quadratic algorithm looks fine on ten items), and change one thing between two measurements.

### Counting is better than timing when you can

A clock measures how fast the machine is today. A **count** measures how much work the code does, and gives the same answer on every machine, so it can sit in a test. The handbook's `fib` with `lru_cache(maxsize=None)` shows the idea: the cache does not make function calls faster, it makes most of them not happen.

```python run
import functools


def count_calls(func):
    @functools.wraps(func)
    def counting(*args):
        counting.calls += 1
        return func(*args)
    counting.calls = 0
    return counting


@count_calls
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


assert fib(20) == 6765 and fib.calls == 21891            # exactly this many calls, on every machine and every Python

calls = []


@functools.lru_cache(maxsize=None)
def fib_cached(n):
    calls.append(n)
    return n if n < 2 else fib_cached(n - 1) + fib_cached(n - 2)


assert fib_cached(20) == 6765 and len(calls) == 21       # each n computed once
info = fib_cached.cache_info()
assert (info.hits, info.misses, info.currsize) == (18, 21, 21)       # 21 values computed once each; every other request was answered from the cache
```

The price is in `currsize`: with `maxsize=None` the cache holds every result for the life of the program (PY-M13 section 6). A cache is a trade of memory for work; say which one you are short of.

## 3. Profiling: where does the time go? (LO1, LO2)

`cProfile` records every function call: how many calls, how much time in the function itself (`tottime`) and in the function plus everything it called (`cumtime`). Its call counts are exact, and its times include some overhead of watching, so use the times to rank functions and the counts to compare runs.

Here is a program with three weaknesses. The task: match orders to stock items, rank the customers, and print a summary.

```python module=shop
def match(orders, stock):
    """For each order the matching stock item (same sku), or None."""
    result = []
    for order in orders:
        found = None
        for item in stock:                      # a scan of the whole stock for every order
            if item["sku"] == order["sku"]:
                found = item
                break
        result.append(found)
    return result


def ranking(orders):
    """Customers by total quantity, largest first, ties alphabetical."""
    totals = {}
    for order in orders:
        totals[order["customer"]] = totals.get(order["customer"], 0) + order["qty"]
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))


def summary(orders, stock):
    matched = match(orders, stock)
    missing = sum(1 for m in matched if m is None)
    text = ""
    for customer, qty in ranking(orders)[:3]:
        text += f"{customer}: {qty}\n"
    return missing, text


def make_data(n_orders, n_stock):
    stock = [{"sku": f"sku{i}", "price": i} for i in range(n_stock)]
    orders = [{"sku": f"sku{(i * 7919) % (n_stock + 50)}", "customer": f"c{i % 97}", "qty": 1 + i % 5} for i in range(n_orders)]
    return orders, stock
```

```python run
import cProfile
import pstats

from shop import make_data, summary

orders, stock = make_data(3000, 3000)
profiler = cProfile.Profile()
result = profiler.runcall(summary, orders, stock)
stats = pstats.Stats(profiler)

assert result[0] > 0                                                  # some orders have no stock item
# stats.stats maps (file, line, function) -> (primitive calls, calls, own time, cumulative time, callers)
rows = {name: (calls, own, cum) for (file, line, name), (cc, calls, own, cum, callers) in stats.stats.items() if file.endswith("shop.py")}
assert rows["match"][0] == 1 and rows["summary"][0] == 1 and rows["ranking"][0] == 1      # call counts are exact
total = stats.total_tt
share = rows["match"][2] / total                                       # the share of the whole run spent in match and below
assert share > 0.5, share                                              # one function dominates: that is where to look
assert rows["ranking"][2] < 0.2 * total                                # the part that looks complicated is cheap

# The report you would read at a terminal: sort by cumulative time, show the first rows.
import io
buffer = io.StringIO()
pstats.Stats(profiler, stream=buffer).sort_stats("cumulative").print_stats(5)
text = buffer.getvalue()
assert "match" in text and "cumulative" in text and "ncalls" in text
```

How to read the table: **ncalls** is how many times; **tottime** is time in the function's own lines, which points at the code to change; **cumtime** includes the callees, which points at the part of the program to question. `match` has the largest cumulative time because it scans the stock for each order. Which function is *called most* or *looks worst* is not evidence; the profile is.

### How much can a fix gain? Amdahl's law

If a fraction `p` of the run is spent in the part you improve, and you make that part `s` times faster, the whole run gets faster by

```python run
def amdahl(p, s):
    return 1 / ((1 - p) + p / s)


assert round(amdahl(0.60, 10), 2) == 2.17        # a function that takes 60 percent, made ten times faster: the run is 2.2 times faster
assert amdahl(0.05, 1000) < 1.06                 # a function that takes 5 percent can never gain more than 5 percent, however clever the rewrite
assert amdahl(1.0, 4) == 4.0 and amdahl(0.0, 4) == 1.0
```

So the order of work is fixed by the profile: fix the largest share first, measure again, and stop when the next share is too small to be worth the code it costs. Rewriting `ranking` (6 percent of the run in the example) would be hours of work for a gain you cannot see.

### Fix, then prove nothing changed

The fix for `match` is a data structure: a dictionary from sku to item makes each lookup one step. The proof is a comparison against the old version on many inputs, including the awkward ones:

```python run
import random
import time

from shop import make_data, match


def match_fast(orders, stock):
    by_sku = {}
    for item in stock:
        by_sku.setdefault(item["sku"], item)         # setdefault keeps the FIRST item of a duplicated sku, like the scan did
    return [by_sku.get(order["sku"]) for order in orders]


def best_time(func, *args):
    best = float("inf")
    for _ in range(3):
        started = time.perf_counter()
        func(*args)
        best = min(best, time.perf_counter() - started)
    return best


rnd = random.Random(1)
for _ in range(200):                                  # equivalence on random, small and awkward inputs
    n_stock = rnd.randint(0, 8)
    stock = [{"sku": f"s{rnd.randint(0, 5)}", "price": rnd.random()} for _ in range(n_stock)]       # duplicated skus on purpose
    orders = [{"sku": f"s{rnd.randint(0, 7)}", "customer": "c", "qty": 1} for _ in range(rnd.randint(0, 8))]
    assert match_fast(orders, stock) == match(orders, stock)

orders, stock = make_data(3000, 3000)
assert match_fast(orders, stock) == match(orders, stock)
assert 10 * best_time(match_fast, orders, stock) < best_time(match, orders, stock)      # at least ten times faster; the real gap is hundreds of times
```

Notice the measure. A count of function calls would have said the new version is *not* better (it calls `get` once per order where the old one called nothing), because the saving is in the comparisons inside a loop, which no call count sees. Choose the metric that sees the work you removed: calls for call-heavy code, comparisons or statements for scans and queries, time with a very wide margin when nothing else fits.

The loop with duplicated skus is the part people skip: the scan returned the *first* match, and a dictionary built with plain assignment would return the *last*. An equivalence test over random inputs finds that kind of difference in a second; a code review often does not.

## 4. Sampling profilers and what Python 3.15 added (LO1)

`cProfile` is a **tracing** profiler: it is told about every call and return, so its counts are exact and it slows the program (more for programs that make many tiny calls). A **sampling** profiler looks at the running program a thousand times a second and notes which function is executing: it adds little overhead and its numbers are statistical, so it can profile a program you cannot afford to slow down, and it shows time inside C code the tracing profiler cannot split.

Python 3.15 ships one: the `profiling` package, with `profiling.tracing` (cProfile under a new name, still importable as `cProfile`) and `profiling.sampling`, run as a module. It does not exist on 3.11 to 3.14, where external tools such as `py-spy` play that role.

```python run
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

script = pathlib.Path(tempfile.mkdtemp()) / "spin.py"
script.write_text(
    "import time\n"
    "def busy():\n"
    "    end = time.perf_counter() + 0.6\n"
    "    while time.perf_counter() < end:\n"
    "        sum(range(1000))\n"
    "busy()\n",
    encoding="utf-8",
)

if sys.version_info >= (3, 15):
    assert importlib.util.find_spec("profiling.sampling") is not None and importlib.util.find_spec("profiling.tracing") is not None
    done = subprocess.run([sys.executable, "-m", "profiling.sampling", "run", "-r", "1000", str(script)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0 and "Captured" in done.stdout and "busy" in done.stdout, done.stderr[-300:]
else:
    assert importlib.util.find_spec("profiling") is None
    import cProfile
    assert hasattr(cProfile, "Profile")
    if sys.version_info >= (3, 12):
        assert hasattr(sys, "monitoring")                  # the low-overhead event interface that newer profilers and debuggers use
```

Choose the tool by the question. *Which function is hot in a program I can run under a profiler?* `cProfile`. *Why is production slow, and I cannot slow it down?* A sampling profiler. *How many times was this called?* `cProfile`, or a counter you wrote.

## 5. Better algorithms, not tricks (LO2)

Almost every large speed-up comes from doing **less work**, not from doing the same work faster. The shapes recur:

| Pattern | Why it is slow | Replacement |
|---|---|---|
| `x in some_list`, `list.count`, `list.index` inside a loop | each is a scan of the list: n × m | a `set` or `dict`, built once |
| `sorted()` or `min()` inside a loop over the same data | repeated work | sort once; `heapq.nsmallest` for the top few |
| `for i in range(len(xs)): ... xs[:i]` | slicing copies | indexes, `itertools`, running totals |
| a compiled regex, a parsed date or a connection built for each item | the setup repeats | build once, outside the loop; cache by key |
| a query per item (N+1, PY-M08) | round trips | one query for all |
| everything held in memory "to be safe" | memory and a long wait for the first result | a generator that streams (PY-M13) |

Count the work instead of timing it. Here a class counts how many times two values were compared for equality:

```python run
class Counted:
    comparisons = 0

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        Counted.comparisons += 1
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


items = [Counted(i) for i in range(200)]
probe = Counted(199)
Counted.comparisons = 0
assert probe in items                                          # a list is searched one item at a time
assert Counted.comparisons == 200

as_set = set(items)
Counted.comparisons = 0
assert probe in as_set                                         # a set hashes first, then compares only the matching bucket
assert Counted.comparisons == 1
```

The set paid its price once, when it was built. That is the trade every data structure makes: *build cost* against *lookup cost*. For two lookups a list is fine; for two thousand it is not.

### Quadratic and linear, shown without a stopwatch

How do you *show* that code is quadratic? Run it at size `n` and `4n` and compare the work: linear code does about 4 times as much, quadratic code about 16 times. The comparisons can be counted exactly, so the ratio is the same on every machine:

```python run
class Counted:
    comparisons = 0

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        Counted.comparisons += 1
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


def unique_quadratic(items):
    seen = []
    for x in items:
        if x not in seen:
            seen.append(x)
    return seen


def unique_linear(items):
    return list(dict.fromkeys(items))


def comparisons(fn, n):
    data = [Counted(i) for i in range(n)]
    Counted.comparisons = 0
    fn(data)
    return Counted.comparisons


quadratic_ratio = comparisons(unique_quadratic, 800) / comparisons(unique_quadratic, 200)
linear_ratio = max(comparisons(unique_linear, 800), 1) / max(comparisons(unique_linear, 200), 1)
assert 15 < quadratic_ratio < 17                  # 4 times the data, 16 times the comparisons (n * (n - 1) / 2)
assert linear_ratio == 1                          # the dictionary never compared two different values
assert [c.value for c in unique_quadratic([Counted(1), Counted(1), Counted(2)])] == [c.value for c in unique_linear([Counted(1), Counted(1), Counted(2)])]
```

When no counter fits (the work is spread over many operations), the same ratio can be taken from the clock, with sizes large enough that the fast version takes milliseconds and with limits far from the expected 4 and 16. Section 6 does that.

## 6. Performance tests that do not flake (LO4)

A test such as `assert elapsed < 0.05` passes on the author's laptop and fails on a busy CI runner, and the team learns to ignore it. A performance test must be built so that noise cannot change its verdict. Five rules:

1. **Prefer a count to a clock.** Function calls from `cProfile`, comparisons from a counting class, statements from the SQLite trace callback (PY-M08), virtual-machine instructions from `sys.setprofile`-free tools: all identical on every run.
2. **Compare sizes, not seconds.** Run at `n` and `4n`; assert that the ratio is below a number between the linear and the quadratic expectation.
3. **Put the budget an order of magnitude from both answers.** If a correct solution takes 3 ms and the quadratic one 2 s, a budget of 250 ms fails the bad one every time and the good one never, on any plausible machine.
4. **Take the best of a few runs** and stop early when a run is already far over budget (do not time a hopeless solution three times).
5. **Always pair a speed test with an equivalence test.** The fastest function is the one that returns `[]`.

```python module=budget
import time


def best_of(fn, tries=3, give_up_above=None):
    best = float("inf")
    for _ in range(tries):
        started = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - started)
        if give_up_above is not None and best > give_up_above:
            break
    return best


def scales_linearly(fn, make_input, small=2000, factor=4, limit=8):
    """True if running on `factor` times more data takes less than `limit` times as long (linear: about `factor`, quadratic: about factor squared)."""
    small_input, large_input = make_input(small), make_input(small * factor)
    return best_of(lambda: fn(large_input), tries=5) / best_of(lambda: fn(small_input), tries=5) < limit
```

```python test
from budget import scales_linearly


def dedupe_list(items):
    seen = []
    for x in items:
        if x not in seen:
            seen.append(x)
    return seen


def dedupe_dict(items):
    return list(dict.fromkeys(items))


def test_the_good_solution_passes_the_scaling_test():
    assert scales_linearly(dedupe_dict, lambda n: list(range(20 * n)))                 # 40 000 against 160 000 items: milliseconds, not microseconds, and small enough to stay in the processor cache


def test_the_quadratic_solution_fails_it():
    assert not scales_linearly(dedupe_list, lambda n: list(range(n)), small=1500)


def test_both_give_the_same_answer_on_awkward_input():
    for data in ([], [1], [1, 1, 1], [3, 1, 3, 2, 1], list("abcab")):
        assert dedupe_list(data) == dedupe_dict(data)
```

The guided lab's scaling checks use exactly this construction, and the instructors' mutation test puts the slow algorithm back to confirm that the checks notice.

## 7. Memory (LO3)

`tracemalloc` counts the memory Python allocates, exactly, with the line that allocated it. Two numbers matter: what is held at the end of a piece of code, and the **peak** during it (the peak decides whether the program runs out of memory):

```python run
import tracemalloc


def peak_of(fn):
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        fn()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


as_list = peak_of(lambda: sum([i * i for i in range(200_000)]))        # builds the whole list, then sums it
as_stream = peak_of(lambda: sum(i * i for i in range(200_000)))        # one item at a time
assert as_stream < 0.1 * as_list                                        # memory, not speed: the generator never holds the items

# Where did the memory go? Compare two snapshots.
tracemalloc.start()
before = tracemalloc.take_snapshot()
kept = [str(i) * 5 for i in range(20_000)]
after = tracemalloc.take_snapshot()
top = after.compare_to(before, "lineno")[0]
tracemalloc.stop()
assert top.size_diff > 500_000                                   # the list comprehension line is where the memory went
```

### `__slots__`, and the cost of an attribute dictionary

An ordinary object keeps its attributes in a dictionary. `__slots__` replaces the dictionary by fixed slots:

```python run
import tracemalloc


class Plain:
    def __init__(self, a, b):
        self.a, self.b = a, b


class Slotted:
    __slots__ = ("a", "b")

    def __init__(self, a, b):
        self.a, self.b = a, b


def held(factory):
    tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        objects = [factory(i, i) for i in range(10_000)]
        return tracemalloc.get_traced_memory()[0] - before, objects
    finally:
        tracemalloc.stop()


plain_bytes, _ = held(Plain)
slotted_bytes, objects = held(Slotted)
assert slotted_bytes < 0.8 * plain_bytes                       # measured on all five versions: a clear saving for many small objects

try:
    objects[0].extra = 1                                        # the saving has a price: no `__dict__`, so no new attributes
except AttributeError:
    pass
else:
    raise AssertionError("a slotted object should not accept new attributes")
assert not hasattr(objects[0], "__dict__")
```

`@dataclass(slots=True)` (used since PY-M12) gives the same saving. Use it for the classes you create by the thousand, not by default: slots also change pickling, multiple inheritance and weak references.

### Reference counting, cycles and the garbage collector

CPython frees most objects the moment the last reference disappears (**reference counting**). Objects that refer to each other (a **cycle**) are never freed that way; the cyclic garbage collector finds them periodically:

```python run
import gc
import sys
import weakref


class Node:
    pass


a, b = Node(), Node()
a.other, b.other = b, a                                 # a cycle
probe = weakref.ref(a)
del a, b
assert probe() is not None                              # still alive: each keeps the other's count above zero
gc.collect()
assert probe() is None                                  # the collector found and freed them

x = object()
assert sys.getrefcount(x) == 2                          # the variable plus the temporary reference the call itself makes
holder = [x] * 1000
assert sys.getrefcount(x) == 1002

before = sys.getrefcount(None)
holder_of_none = [None] * 1000
delta = sys.getrefcount(None) - before
assert delta == (0 if sys.version_info >= (3, 12) else 1000)       # 3.12 made None, True, small integers and interned names "immortal": no counting at all
```

The last line is why `sys.getrefcount` is a teaching tool and not a measurement tool: the number depends on the interpreter's version and on temporaries you did not write. A `weakref` is the correct way to ask "is this still alive?" and to build caches that must not keep their keys alive.

### Interning: why `is` on strings and numbers is a bug

The handbook shows two equal string literals and `a is b → True`. That works because the compiler merges equal constants in one piece of code. It is not a language rule:

```python run
import sys
import warnings

a = "hello"
b = "hello"
assert a is b                                           # constants in one compilation unit are merged by the compiler

built = "".join(["hel", "lo"])                          # the same text, made at run time
assert built == a and built is not a                    # equal, not identical
assert sys.intern(built) is sys.intern(a)               # sys.intern gives one shared object per distinct text: useful to save memory on repeated values

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    compile("x is 'a'", "<test>", "eval")
assert [w.category.__name__ for w in caught] == ["SyntaxWarning"]      # Python says so when the code is compiled

# Which small integers are shared differs between versions (257 is shared on 3.15, not before): never compare numbers with `is`.
assert int("256") is int("256")
```

`sys.intern` is a legitimate tool for the case it was made for: millions of objects that repeat a few distinct strings (log addresses and user names, in the guided lab). Compare values with `==`.

## 8. Architecture that stays changeable (LO5)

Speed is one reason to change a program; the others are a new requirement, a new data source, a bug. **Architecture is the set of decisions that are expensive to change.** The cheapest way to keep them few is to follow three rules.

### A core that computes and an edge that reads and writes

Functions that only turn values into values (the **core**) are easy to test, easy to profile and safe to move. Reading files, calling the network, printing and exiting (the **edge**) belong at the outside. The guided lab splits `perfkit` this way: `analyze` and its helpers never open a file or print; `FileSource` and `main` do, and a test enforces it by reading the code:

```python run
import ast

SOURCE = '''
def parse(line):
    return line.split(",")

def total(rows):
    print("computing")             # a core function that prints
    return sum(len(r) for r in rows)

def main(path):
    with open(path) as handle:
        print(total([parse(l) for l in handle]))
'''

FORBIDDEN = {"open", "print", "input"}


def violations(source, core):
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name in core:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id in FORBIDDEN:
                    found.append((node.name, sub.id))
    return found


assert violations(SOURCE, {"parse", "total"}) == [("total", "print")]
assert violations(SOURCE, {"parse"}) == []
```

A rule that is only written in a document is forgotten; a rule that is a failing test is kept.

### Dependencies point one way, and a test says so

Draw the boxes: `cli` calls `service` calls `repository`. The rule is that an arrow never points back (a repository that imports the CLI makes every layer depend on all the others). The imports of a package can be read with `ast`, so the rule is testable:

```python run
import ast
import pathlib
import tempfile

ALLOWED = {"cli": {"service", "repository", "models"}, "service": {"repository", "models"}, "repository": {"models"}, "models": set()}


def imports_of(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}


def breaches(package_dir):
    found = []
    for module, allowed in ALLOWED.items():
        used = imports_of(package_dir / f"{module}.py") & set(ALLOWED)
        found += [(module, bad) for bad in sorted(used - allowed)]
    return found


root = pathlib.Path(tempfile.mkdtemp())
(root / "models.py").write_text("class Item: ...\n", encoding="utf-8")
(root / "repository.py").write_text("from models import Item\n", encoding="utf-8")
(root / "service.py").write_text("import repository\nfrom models import Item\n", encoding="utf-8")
(root / "cli.py").write_text("import service\n", encoding="utf-8")
assert breaches(root) == []

(root / "repository.py").write_text("from models import Item\nimport cli\n", encoding="utf-8")        # somebody takes a shortcut
assert breaches(root) == [("repository", "cli")]
```

PY-M03 built the same kind of check for a package; the rule travels with the code.

### Ports and adapters

The core needs *lines*, not *a file*. Say what it needs as a `Protocol` (a **port**) and write small classes that provide it (**adapters**): one reads a file, one holds a list for tests, a future one reads a network stream. The core does not change when the edge does.

```python module=ports
from collections.abc import Iterable, Iterator
from typing import Protocol


class Source(Protocol):
    def lines(self) -> Iterable[str]: ...


class ListSource:
    def __init__(self, lines):
        self._lines = list(lines)

    def lines(self):
        return iter(self._lines)


class FileSource:
    def __init__(self, path):
        self._path = path

    def lines(self) -> Iterator[str]:
        with open(self._path, encoding="utf-8") as handle:
            for line in handle:
                yield line.rstrip("\n")


def count_errors(source: Source) -> int:
    return sum(1 for line in source.lines() if line.startswith("ERROR"))
```

```python test
import pytest
from ports import FileSource, ListSource, count_errors


def test_the_core_works_with_any_adapter(tmp_path):
    lines = ["ERROR a", "INFO b", "ERROR c"]
    path = tmp_path / "x.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert count_errors(ListSource(lines)) == count_errors(FileSource(str(path))) == 2


def test_the_file_adapter_opens_nothing_until_asked(tmp_path):
    source = FileSource(str(tmp_path / "missing.log"))             # building it is free
    with pytest.raises(FileNotFoundError):
        list(source.lines())                                        # the error appears at the moment of reading
```

The handbook's builder, adapter and facade patterns are small cases of the same idea. A **facade** is one function in front of three steps that callers always do together (`run(source)` in the lab). An **adapter** makes one interface look like another (`ListSource` makes a list look like a log). A **builder** assembles a value step by step (in Python usually a dataclass and `dataclasses.replace`, PY-M12). None needs a framework; each needs a test.

### A shared standard, checked by a tool

Style discussions end when a tool decides. `ruff` (pinned in `labs/requirements.txt`) lints and formats from one configuration in `pyproject.toml`; the rule codes name the problem:

```python run
import json
import subprocess
import sys

sample = "import os\n\n\ndef add(item, items=[]):\n    if item == None:\n        return items\n    items.append(item)\n    return items\n"
done = subprocess.run(
    [sys.executable, "-m", "ruff", "check", "--select", "F,E,B", "--output-format", "json", "--stdin-filename", "sample.py", "-"],
    input=sample, capture_output=True, text=True, timeout=120,
)
codes = sorted({finding["code"] for finding in json.loads(done.stdout)})
assert codes == ["B006", "E711", "F401"], codes            # a mutable default argument, a comparison with None, an unused import
```

Complexity can be measured too, crudely and usefully: count the branches of a function with `ast`, and treat a high number as a prompt to split, not a goal.

```python run
import ast


def branches(source):
    """1 + the number of decision points in each function: if, elif, for, while, except, boolean operators, conditional expressions, comprehension conditions."""
    result = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef):
            count = 1
            for sub in ast.walk(node):
                if isinstance(sub, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)):
                    count += 1 + (len(sub.ifs) if isinstance(sub, ast.comprehension) else 0)
                elif isinstance(sub, ast.BoolOp):
                    count += len(sub.values) - 1
            result[node.name] = count
    return result


code = "def simple(x):\n    return x + 1\n\ndef tangled(a, b):\n    if a and b:\n        for i in range(a):\n            if i % 2:\n                return i\n    return 0\n"
assert branches(code) == {"simple": 1, "tangled": 5}
```

## 9. What differs between Python versions (executed)

Every row was produced by running the same code on CPython 3.11, 3.12, 3.13, 3.14 and 3.15 (R-099) and is asserted again by this lesson on whichever interpreter runs it.

| Behaviour | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|---|
| `cProfile` call counts are exact and repeatable | yes | yes | yes | yes | yes |
| `sys.monitoring` (low-overhead event interface) | no | yes | yes | yes | yes |
| `None` and other immortal objects: reference count does not change | no | yes | yes | yes | yes |
| `sys._is_gil_enabled()` (free-threaded builds exist) | no | no | yes | yes | yes |
| `profiling.sampling` (statistical profiler in the standard library) | no | no | no | no | yes |
| `a is b` for strings built at run time | no | no | no | no | no |

```python run
import sys

v = sys.version_info[:2]
assert hasattr(sys, "monitoring") == (v >= (3, 12))
assert hasattr(sys, "_is_gil_enabled") == (v >= (3, 13))
before = sys.getrefcount(None)
keep = [None] * 100
assert (sys.getrefcount(None) == before) == (v >= (3, 12))
```

## 10. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 56 | Memory management: reference counting with `sys.getrefcount(x)` | section 7: what the number means, why it differs between versions, cycles and `weakref` |
| 57 | Garbage collection; interning "(Speed Optimization)" with `a is b → True` | section 7: `is` is a bug for strings and numbers; `sys.intern` for repeated values |
| 79 | "Execution optimization": PyPy, Cython, NumPy, caching, `lru_cache(maxsize=None)` with `fib` | sections 2, 3 and 5: measure first; call counts; what the unbounded cache costs; tools chosen by the profile |
| 80 | "Memory optimization": generators, `__slots__`, arrays, local variables | section 7: measured with `tracemalloc`; the price of `__slots__`; generators in PY-M13 |
| 64 to 67 | Builder, adapter and facade patterns (as lists of names) | section 8: ports and adapters, facade and builder as small, tested shapes |
| 462 to 464 | "Python for FinOps": cloud cost reduction by scripts | not carried here: a cost topic for the cloud courses; the habit of measuring before changing applies |

## 11. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| optimising before profiling | hours spent, nothing gained | profile; fix the largest share; profile again |
| timing once | a "speed-up" that is noise | the minimum of several runs, on realistic input size |
| a speed test with a clock threshold | passes on a laptop, fails in CI | counts, size ratios, budgets an order of magnitude away |
| a faster function with a different answer | wrong results nobody notices | an equivalence test against the old version on random and awkward input |
| `x in list` or `list.count` in a loop | fine at 100 items, unusable at 100 000 | a set or dict built once |
| `lru_cache(maxsize=None)` on unbounded input | memory grows until the process dies | a bound, or no cache |
| `is` to compare strings or numbers | works until the interpreter changes | `==` (and `is` only for `None`) |
| trusting `sys.getrefcount` | numbers that differ by version | `weakref` and `tracemalloc` |
| I/O inside computing functions | slow, untestable code | the core takes values; the edge reads and writes |
| layers that import each other | a change anywhere breaks everything | one-way imports, enforced by a test |

## 12. Check yourself

1. A profile shows function `f` with 60 percent of the run and function `g` with 5 percent. You can make either ten times faster. Which do you change, and what whole-program speed-up do you expect from each?
2. Why does `unique_linear` take about 4 times as long on 4 times the data and `unique_quadratic` about 16 times, and why is the ratio a better test than a time?
3. `a = "hello"; b = "hello"` gives `a is b` as `True`. Why is it still a bug to write `if name is "hello"`?
4. A class is created 5 million times. What does `__slots__` change, what does it cost, and how do you check the saving?
5. A module-level function opens a file, parses it and prints the result. Name two things that make it hard to test or reuse, and how a core/edge split fixes them.

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 13. Sources and verification trail

- Every assertion in this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 (R-099; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). Reference documentation: <https://docs.python.org/3/library/profile.html> (cProfile, pstats), <https://docs.python.org/3/library/timeit.html>, <https://docs.python.org/3/library/tracemalloc.html>, <https://docs.python.org/3/library/gc.html>, <https://docs.python.org/3/library/sys.html#sys.getrefcount>, <https://docs.python.org/3/whatsnew/3.15.html> for the `profiling` package (R-005); the ruff documentation for the rule codes.
- Handbook corrections: finding F-PYH-014 (an unqualified reference-counting demonstration, interning presented as an optimisation with an identity comparison, optimisation tools listed without any measurement, an unbounded `lru_cache` example).
- Not verified here and therefore not claimed: PyPy, Cython, Numba and NumPy speed-ups (not part of the course dependencies); the speed of any specific CPython version (the lesson compares counts and ratios, never seconds); behaviour of free-threaded builds beyond the existence of `sys._is_gil_enabled`; the overhead of the sampling profiler (only that it runs and reports the busy function).
