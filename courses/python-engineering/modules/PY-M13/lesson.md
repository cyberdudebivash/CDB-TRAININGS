---
id: PY-M13
title: "Iterators, generators, closures, decorators and context managers"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M01 and PY-M02 and now need the language features that make real Python programs lazy, reusable and leak-free: streams of data, functions that wrap functions, and resources that are always released"
prerequisites:
  - "PY-M01 (language core) and PY-M02 (functions, errors and pytest)"
  - "Python 3.11 or newer; the labs and every code block of this lesson were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "pytest 9.1.1 from labs/requirements.txt; no network, no account, no paid service"
estimated_time_hours: {lesson: 3.0, guided_lab: 2.5, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); behaviour of iterators, generators, decorators and context managers by version executed in this lesson (R-097)", pytest: "9.1.1"}
last_verified: 2026-10-15
---

# PY-M13 - Iterators, generators, closures, decorators and context managers

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Explain the iterator protocol and write correct iterators and generators: single-pass behaviour, laziness, `yield from`, the return value of a generator, and what `close()` does. |
| **LO2** | Build lazy pipelines that stop early and clean up after themselves, check arguments when a generator-returning function is *called* rather than when it is first iterated, and say when a generator is the wrong tool. |
| **LO3** | Write closures with `nonlocal` state, recognise the late-binding trap and fix it. |
| **LO4** | Write decorators that preserve arguments, the return value and the metadata of the function (`functools.wraps`), decorators that take arguments, and know the limits of `functools.cache`. |
| **LO5** | Write context managers, as a class and with `contextlib.contextmanager`, that release a resource on every path including exceptions; use `ExitStack` when the number of resources is not fixed. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Programs that handle logs, files, API pages or records almost never need all the data at once, and programs that hold files, locks and connections must let go of them even when something fails. The language features for both are the topic of this module: **iterators and generators** (produce data one item at a time), **closures and decorators** (functions that make or wrap functions), and **context managers** (guaranteed cleanup).

The 2025 handbook introduces each of them in a few lines (PDF pages 33 to 39, 67 to 69 and 78 to 79), and the examples would teach habits that fail in real programs. Each of these is executed in this lesson on five Python versions:

- the **error-handling** example (page 33) opens a file in a `try`, catches *everything* with a bare `except:` and "always" prints in `finally`, but never closes the file (section 8);
- the **custom iterator** (page 35) defines a method `next`, which is Python 2 spelling and does nothing in Python 3 (section 2);
- generators are described as "**faster for large datasets**" (page 36); what they save is memory, and whether they are faster is a measurement, not a promise (section 3);
- the **basic decorator** (page 38) cannot be called with an argument, throws away the return value and renames the function to `wrapper` (section 6);
- the **context manager** examples (pages 66 to 68 and 79) take `*args` in `__exit__` without saying what it receives or what its result means, and open no resource at all (section 8);
- closures, functions as values and caching are listed as "the heart of machine learning pipelines" and "clean architecture" (pages 68 to 69, 78); the lesson replaces the slogans with the mechanisms and their traps (sections 5 to 7).

The labs build a small stream-processing library (guided) and a merge, group, cache and rollback toolkit (independent).

## 2. The iterator protocol (LO1)

An **iterable** is anything you can loop over; an **iterator** is the object that remembers where the loop is. `iter(x)` turns an iterable into an iterator, `next(it)` produces the next item, and the iterator raises `StopIteration` when there are no more. A `for` loop is nothing but a repeated `next()`.

```python run
numbers = [10, 20, 30]
it = iter(numbers)
assert next(it) == 10 and next(it) == 20 and next(it) == 30
try:
    next(it)
except StopIteration:
    pass
else:
    raise AssertionError("an exhausted iterator raises StopIteration")

assert iter(it) is it, "an iterator is its own iterator"
assert iter(numbers) is not numbers, "a list is iterable, not an iterator: every iter() call starts a new walk"
assert list(iter(numbers)) == list(iter(numbers)) == [10, 20, 30]
```

An iterator is **single-pass**: once it is exhausted it stays exhausted. Several everyday objects are iterators, and treating them like lists is one of the commonest bugs:

```python run
squares = (x * x for x in range(3))                 # a generator expression is an iterator
assert list(squares) == [0, 1, 4]
assert list(squares) == [], "the second pass finds nothing"

mapped = map(str, [1, 2])                           # map, filter, zip and enumerate return iterators too
assert list(mapped) == ["1", "2"] and list(mapped) == []

stream = (x for x in range(5))
assert 3 in stream                                  # `in` walks the iterator until it finds the value ...
assert list(stream) == [4], "... and consumes everything up to and including it"
```

To write your own iterator, define `__iter__` (returning `self`) and `__next__`. The handbook's `Counter` also defines a method called `next`; that is the Python 2 name. In Python 3 the built-in `next()` looks only for `__next__`:

```python run
class OnlyNext:                                     # the Python 2 spelling, as on page 35
    def __iter__(self):
        return self

    def next(self):
        return 1

try:
    next(OnlyNext())
except TypeError as exc:
    assert "not an iterator" in str(exc)
else:
    raise AssertionError("next() needs __next__")

class Countdown:
    """Counts from `start` down to 1. A new Countdown is needed for each pass."""

    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < 1:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value

assert list(Countdown(3)) == [3, 2, 1]
```

(The handbook also names its class `Counter`, which hides `collections.Counter` in any module that imports both; pick a name that says what the class is.) Writing iterators by hand is rarely needed, because a generator does the same job with less code.

## 3. Generators: functions that pause (LO1)

A function that contains `yield` is a **generator function**. Calling it runs *nothing*; it returns a generator, which is an iterator. The body runs, up to the next `yield`, each time `next()` is called.

```python run
import inspect

log = []

def numbers():
    log.append("start")
    yield 1
    log.append("after 1")
    yield 2
    log.append("after 2")

gen = numbers()
assert log == [], "calling the function ran none of its body"
assert inspect.getgeneratorstate(gen) == "GEN_CREATED"
assert next(gen) == 1 and log == ["start"] and inspect.getgeneratorstate(gen) == "GEN_SUSPENDED"
assert next(gen) == 2 and log == ["start", "after 1"]
assert list(gen) == [] and log == ["start", "after 1", "after 2"] and inspect.getgeneratorstate(gen) == "GEN_CLOSED"
```

This is **laziness**: work happens only when someone asks for the next item. It is what lets a generator describe an infinite sequence or a file larger than memory, because it never holds more than the current item.

```python run
import itertools

def naturals():
    n = 1
    while True:
        yield n
        n += 1

assert list(itertools.islice(naturals(), 5)) == [1, 2, 3, 4, 5]          # take five from an infinite stream

consumed = []
def counted(n):
    for i in range(n):
        consumed.append(i)
        yield i

it = iter(counted(1_000_000))
next(it); next(it)
assert consumed == [0, 1], "two items were requested, so exactly two were produced"
```

The handbook says generators are "faster for large datasets". What they reliably save is **memory**. Speed depends on the program, so measure it before you promise it. The memory claim can be measured with `tracemalloc`:

```python run
import tracemalloc

def peak_bytes(make):
    tracemalloc.start()
    total = sum(make())
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return total, peak

n = 200_000
total_list, peak_list = peak_bytes(lambda: [x * x for x in range(n)])       # builds the whole list first
total_gen, peak_gen = peak_bytes(lambda: (x * x for x in range(n)))         # one item at a time
assert total_list == total_gen
assert peak_gen * 20 < peak_list, f"the generator's peak memory ({peak_gen}) is a small fraction of the list's ({peak_list})"
```

`yield from` delegates to another iterator, and a generator's `return value` becomes the value of the `yield from` expression, which is how a sub-generator reports a result:

```python run
def subtask():
    yield "working"
    return "result"                                  # not an item: the value of `yield from`

def main():
    outcome = yield from subtask()
    yield f"subtask said {outcome}"

assert list(main()) == ["working", "subtask said result"]
```

Two rules of the language matter in practice. **`raise StopIteration` inside a generator is an error**: since Python 3.7 it becomes a `RuntimeError`, so that a stray `StopIteration` cannot silently end a loop; use `return`. And a generator's `finally` block runs when the generator is **closed**, which is the subject of the next section.

```python run
def bad():
    yield 1
    raise StopIteration

try:
    list(bad())
except RuntimeError:
    pass
else:
    raise AssertionError("StopIteration inside a generator is turned into RuntimeError")

def good():
    yield 1
    return

assert list(good()) == [1]
```

## 4. Pipelines, cleanup and arguments (LO2)

Because each stage of a generator pipeline pulls from the previous one, a chain such as *read lines, parse, filter, batch* handles one record at a time and starts producing output before the input has been read. **Resources** are the difficulty: a generator that opens a file must close it when the consumer stops early. Put the `with` block **inside the generator**, and the file is closed when the generator finishes, when it is closed with `.close()` and when it is garbage collected:

```python run
import contextlib
import gc
import os
import tempfile

events = []

def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        events.append("opened")
        try:
            for line in handle:
                yield line.rstrip("\n")
        finally:
            events.append("cleanup")                  # runs on exhaustion, on close() and on garbage collection

with tempfile.TemporaryDirectory() as folder:
    path = os.path.join(folder, "log.txt")
    with open(path, "w", encoding="utf-8") as out:
        out.write("a\nb\nc\n")

    gen = read_lines(path)
    assert events == [], "nothing is opened until the first item is requested"
    assert next(gen) == "a" and events == ["opened"]
    gen.close()                                       # the consumer stops early: GeneratorExit is raised at the yield
    assert events == ["opened", "cleanup"]

    events.clear()
    gen = read_lines(path)
    next(gen)
    del gen                                           # an abandoned generator is closed by the garbage collector (CPython frees it at once)
    gc.collect()
    assert events == ["opened", "cleanup"]

    events.clear()
    with contextlib.closing(read_lines(path)) as lines:        # make the cleanup explicit when it matters
        for line in lines:
            break
    assert events == ["opened", "cleanup"]
```

Relying on garbage collection is fine in CPython but not a guarantee on every Python; `contextlib.closing` (or a `try/finally` around the loop) makes the release explicit.

A second trap is **when the arguments are checked**. A generator function runs no code at the call, so a check at the top of its body happens at the *first `next()`*, possibly far from the mistake and after other work. If a bad argument should fail at the call, make the public function an ordinary function that checks and then returns the generator:

```python run
def chunks_lazy_check(items, size):
    if size < 1:
        raise ValueError("size must be at least 1")      # runs at the first next(), not at the call
    chunk = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

gen = chunks_lazy_check([1, 2, 3], 0)                    # no error yet: the call only created a generator
try:
    next(gen)
except ValueError:
    pass

def chunks(items, size):
    if size < 1:
        raise ValueError("size must be at least 1")      # runs now
    return _chunks(iter(items), size)

def _chunks(iterator, size):
    while True:
        chunk = []
        for item in iterator:
            chunk.append(item)
            if len(chunk) == size:
                break
        if not chunk:
            return
        yield chunk
        if len(chunk) < size:
            return

try:
    chunks([1, 2, 3], 0)                                 # fails here, at the call
except ValueError:
    pass
else:
    raise AssertionError("expected an immediate ValueError")
assert list(chunks(range(5), 2)) == [[0, 1], [2, 3], [4]]
```

The standard library already has many building blocks, all lazy: `itertools.islice` (take a slice), `chain`, `zip`, `pairwise` (3.10+), `batched` (3.12+, so the guided lab writes its own `chunks`) and `groupby`. `groupby` has a trap that has caught many programs: it groups **consecutive** items, so unsorted input gives repeated keys, and each group is a view that is invalidated as soon as the outer iterator moves on:

```python run
import itertools

pairs = list(itertools.groupby("aabaa"))
assert [key for key, _ in pairs] == ["a", "b", "a"], "consecutive runs only: 'a' appears twice"
assert [list(group) for _, group in pairs] == [[], [], []], "list(groupby(...)) moved on past every group, so every group is already empty"

groups = [(key, list(group)) for key, group in itertools.groupby("aabaa")]     # materialise each group before advancing
assert groups == [("a", ["a", "a"]), ("b", ["b"]), ("a", ["a", "a"])]
```

Finally, know when **not** to use a generator: when you need `len()`, indexing, more than one pass, or the data is small enough that a list is clearer. `list(generator)` is always available when you do need the whole thing.

## 5. Closures (LO3)

A **closure** is a function together with the variables of the scope in which it was defined. The inner function keeps those variables alive after the outer function has returned, and `nonlocal` lets it assign to them:

```python run
def make_counter(start=0):
    count = start

    def next_value():
        nonlocal count                                # without this, `count += 1` would try to create a local name and fail
        count += 1
        return count

    return next_value

a, b = make_counter(), make_counter(10)
assert (a(), a(), b(), a()) == (1, 2, 11, 3), "each closure has its own `count`"
assert a.__closure__ is not None and [c.cell_contents for c in a.__closure__] == [3]
```

Closures capture **variables, not values**. A closure created in a loop sees whatever the variable holds *when it is called*, so every function made in the loop shares the loop's last value. This "late binding" is one of the best-known surprises of Python:

```python run
import functools

late = [lambda: i for i in range(3)]
assert [f() for f in late] == [2, 2, 2], "all three see the final value of i"

by_default = [lambda i=i: i for i in range(3)]       # a default argument is evaluated when the lambda is created
assert [f() for f in by_default] == [0, 1, 2]

def power(exponent, base):
    return base ** exponent

squares = [functools.partial(power, e) for e in range(3)]       # partial binds the value now
assert [f(2) for f in squares] == [1, 2, 4]

def make(i):                                          # a factory function gives each closure its own scope
    return lambda: i

by_factory = [make(i) for i in range(3)]
assert [f() for f in by_factory] == [0, 1, 2]
```

A closure with state is a small object; when it needs more than one or two pieces of state, or tests need to look inside, write a class (guided-lab step E uses both forms).

## 6. Decorators (LO4)

A decorator is a function that takes a function and returns a function; `@d` above a `def f` means `f = d(f)`. The handbook's first example (page 38) shows the idea and three defects, each of which breaks real code:

```python run
import io
from contextlib import redirect_stdout

def log(func):                                        # the handbook's decorator
    def wrapper():
        print("Function called!")
        func()
    return wrapper

@log
def greet():
    """Say hello."""
    return "Hello!"

with redirect_stdout(io.StringIO()):
    assert greet() is None, "the return value was thrown away"
assert greet.__name__ == "wrapper" and greet.__doc__ is None, "the name and docstring of greet were lost"

@log
def greet_person(name):
    return f"Hello, {name}!"

try:
    greet_person("Ann")
except TypeError:
    pass                                              # wrapper() takes no arguments
else:
    raise AssertionError("the handbook's decorator cannot wrap a function with parameters")
```

The fix is the pattern every decorator should follow: accept `*args, **kwargs`, return what the function returns, and copy its metadata with `functools.wraps`, which also records the original in `__wrapped__`:

```python run
import functools

def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        calls.append(func.__name__)
        return func(*args, **kwargs)
    return wrapper

calls = []

@log
def greet(name, punctuation="!"):
    """Say hello."""
    return f"Hello, {name}{punctuation}"

assert greet("Ann", punctuation="?") == "Hello, Ann?" and calls == ["greet"]
assert greet.__name__ == "greet" and greet.__doc__ == "Say hello." and greet.__wrapped__("x") == "Hello, x!"
```

A decorator **with arguments** is a function that returns a decorator, so there are three levels: the factory takes the arguments, the decorator takes the function, the wrapper takes the call. Validate the arguments in the factory, where a mistake is reported at the line that wrote it:

```python run
import functools

def repeat(times):
    if isinstance(times, bool) or not isinstance(times, int) or times < 1:
        raise ValueError("times must be a positive int")          # reported when @repeat(...) is evaluated

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

seen = []

@repeat(3)
def record(item):
    seen.append(item)
    return len(seen)

assert record("x") == 3 and seen == ["x", "x", "x"]
try:
    repeat(0)
except ValueError:
    pass
```

Decorators apply from the bottom up and run from the top down:

```python run
order = []

def tag(name):
    def decorator(func):
        order.append(f"decorate {name}")
        def wrapper(*args, **kwargs):
            order.append(f"enter {name}")
            try:
                return func(*args, **kwargs)
            finally:
                order.append(f"leave {name}")
        return wrapper
    return decorator

@tag("outer")
@tag("inner")
def work():
    order.append("work")

work()
assert order == ["decorate inner", "decorate outer", "enter outer", "enter inner", "work", "leave inner", "leave outer"]
```

`functools.cache` and `functools.lru_cache` are decorators that remember results. The handbook (page 79) shows `@lru_cache(maxsize=None)` without the limits. Their arguments must be **hashable**, an unbounded cache keeps every result and every argument alive for the life of the program, and a cached function must give the same answer for the same arguments:

```python run
import functools

@functools.cache
def square(x):
    return x * x

assert square(3) == 9 and square(3) == 9
info = square.cache_info()
assert (info.hits, info.misses, info.currsize) == (1, 1, 1)

try:
    square([1, 2])
except TypeError:
    pass
else:
    raise AssertionError("a list is not hashable, so it cannot be a cache key")

@functools.lru_cache(maxsize=2)
def double(x):
    return 2 * x

double(1); double(2); double(3)                       # the least recently used entry (1) is evicted
assert double.cache_info().currsize == 2
```

On a method, the cache key includes `self`, so the cache keeps every instance alive and a mutable instance can return stale answers; cache a plain function of the values you need instead. The independent lab asks you to write a bounded cache yourself so that you meet these questions from the inside.

## 7. Functions are values (LO3, LO4)

The handbook's list (page 69: stored in variables, passed to functions, returned from functions, kept in lists and dictionaries) is correct and is what makes everything above work. Two small examples show why it matters in everyday code: a dictionary of operations replaces an `if` ladder, and a function passed as a `key` or a callback is how behaviour is injected.

```python run
import operator

OPERATIONS = {"add": operator.add, "sub": operator.sub, "mul": operator.mul}

def apply(name, a, b):
    try:
        operation = OPERATIONS[name]
    except KeyError:
        raise ValueError(f"unknown operation: {name!r}") from None
    return operation(a, b)

assert apply("add", 2, 3) == 5 and apply("mul", 4, 5) == 20
words = ["pear", "fig", "banana"]
assert sorted(words, key=len) == ["fig", "pear", "banana"]
assert sorted(words, key=lambda w: w[-1]) == ["banana", "fig", "pear"]
```

The claim that this is "the heart of machine learning pipelines" (page 69) is not something a lesson can check; the mechanism is all that is needed here.

## 8. Context managers (LO5)

`with` guarantees that cleanup runs on every path out of a block. The statement calls `__enter__` on entry and `__exit__` on exit, **also when the block raised**; `__exit__` receives the exception type, value and traceback, and a true result *suppresses* the exception, which is almost never what you want.

First, the handbook's own error-handling example (page 33), which shows why `with` exists. The file is opened and never closed, the bare `except:` hides every kind of error (including `KeyboardInterrupt`), and `finally` runs a `print`, not a `close`:

```python run
import os
import tempfile

with tempfile.TemporaryDirectory() as folder:
    path = os.path.join(folder, "data.txt")
    open(path, "w", encoding="utf-8").close()

    try:                                              # the handbook's pattern (bare except, no close)
        f = open(path, encoding="utf-8")
    except:
        pass
    finally:
        pass                                          # the page prints "Always executed" here
    assert not f.closed, "nothing closed the file"
    f.close()

    with open(path, encoding="utf-8") as g:
        assert not g.closed
    assert g.closed, "the with statement closed it, whatever happened inside the block"
```

A class becomes a context manager with two methods. Return `False` (or `None`) from `__exit__` so that exceptions propagate:

```python run
class Resource:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        self.log.append("open")
        return self                                   # what `as r` receives

    def __exit__(self, exc_type, exc, traceback):
        self.log.append(f"close ({exc_type.__name__ if exc_type else 'no error'})")
        return False                                  # True would swallow the exception

log = []
with Resource(log) as r:
    assert r.log is log
assert log == ["open", "close (no error)"]

log.clear()
try:
    with Resource(log):
        raise ValueError("boom")
except ValueError:
    pass
assert log == ["open", "close (ValueError)"], "the cleanup ran although the block raised, and the exception still reached us"
```

For simple cases a generator is shorter: `@contextlib.contextmanager` turns the code before the `yield` into `__enter__` and the code after it into `__exit__`. **Put the cleanup in `try/finally`**, because an exception in the block is raised at the `yield`, and without `finally` the code after it never runs:

```python run
import contextlib

events = []

@contextlib.contextmanager
def forgetful():
    events.append("open")
    yield
    events.append("close")                            # skipped when the block raises

@contextlib.contextmanager
def careful():
    events.append("open")
    try:
        yield
    finally:
        events.append("close")

for manager in (forgetful, careful):
    events.clear()
    try:
        with manager():
            raise ValueError
    except ValueError:
        pass
    if manager is forgetful:
        assert events == ["open"], "no cleanup: the exception skipped the code after yield"
    else:
        assert events == ["open", "close"]
```

`contextlib.ExitStack` handles a number of resources that is not known in advance, closes them in reverse order and keeps going when a close fails (the exception of the *last* failing close is the one that propagates). Other useful members are `contextlib.closing` (call `close()` on exit), `contextlib.suppress` (ignore listed exceptions in one block) and, from Python 3.11, `contextlib.chdir` (change the working directory and change back).

```python run
import contextlib

closed = []

class Handle:
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail

    def close(self):
        closed.append(self.name)
        if self.fail:
            raise OSError(self.name)

stack = contextlib.ExitStack()
for handle in (Handle("a"), Handle("b", fail=True), Handle("c", fail=True), Handle("d")):
    stack.callback(handle.close)
try:
    stack.close()
except OSError as exc:
    assert str(exc) == "b", "the last failing close (in closing order) propagates"
assert closed == ["d", "c", "b", "a"], "every handle was closed, in reverse order, although two failed"

with contextlib.suppress(FileNotFoundError):
    open("this-file-does-not-exist-anywhere", encoding="utf-8")          # ignored: and only this exception type is
```

The handbook's `__exit__(self, *args)` (pages 66 to 68 and 79) works, but it hides the three arguments and the rule about the return value, and its examples print "Open file" and "Close file" without opening a file. The lab's `temp_env` and `timer` are the realistic version: change something, and restore it on every path.

## 9. Testing generators, decorators and context managers (LO2, LO4, LO5)

The tests that matter for this kind of code are not about the values returned. They are about **how much was consumed**, **whether cleanup ran** and **what was preserved**. A counting iterator makes laziness testable, and an injected clock or sleep makes decorators testable without real time:

```python module=lazy
class Counting:
    """An iterator that counts the items it has handed out and records close()."""

    def __init__(self, items):
        self._it = iter(items)
        self.taken = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._it)
        self.taken += 1
        return item

    def close(self):
        self.closed = True


def first_even(items):
    """The first even item, or None; stops reading as soon as it has found one."""
    for item in items:
        if item % 2 == 0:
            return item
    return None


import functools


def retry(times, sleep):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except ValueError:
                    if attempt == times - 1:
                        raise
                    sleep(0.1)
        return wrapper
    return decorator
```

```python test
import pytest
from lazy import Counting, first_even, retry


def test_first_even_stops_reading_when_it_has_its_answer():
    source = Counting([1, 3, 4, 5, 6])
    assert first_even(source) == 4
    assert source.taken == 3, "it must not read the 5 and the 6"


def test_a_second_call_continues_where_the_first_stopped():
    source = Counting([2, 4, 6])
    assert (first_even(source), first_even(source)) == (2, 4)


def test_retry_sleeps_between_attempts_but_not_after_the_last_one():
    sleeps, calls = [], []

    @retry(3, sleeps.append)
    def flaky():
        calls.append(1)
        raise ValueError("still failing")

    with pytest.raises(ValueError):
        flaky()
    assert len(calls) == 3 and sleeps == [0.1, 0.1]
```

## 10. What differs between Python versions (executed)

Every row was produced by running the same code on CPython 3.11, 3.12, 3.13, 3.14 and 3.15 (R-097) and is asserted again by this lesson on whichever interpreter runs it.

| Behaviour | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|---|
| `itertools.pairwise` | yes | yes | yes | yes | yes |
| `itertools.batched` | no | yes | yes | yes | yes |
| `contextlib.chdir` | yes | yes | yes | yes | yes |
| `StopIteration` raised inside a generator becomes `RuntimeError` | yes | yes | yes | yes | yes |
| an abandoned generator's `finally` runs at once on CPython | yes | yes | yes | yes | yes |

```python run
import contextlib
import itertools
import sys

v = sys.version_info[:2]
assert hasattr(itertools, "pairwise")
assert hasattr(itertools, "batched") == (v >= (3, 12))
assert hasattr(contextlib, "chdir")
assert list(itertools.pairwise("abc")) == [("a", "b"), ("b", "c")]
if hasattr(itertools, "batched"):
    assert list(itertools.batched("abcde", 2)) == [("a", "b"), ("c", "d"), ("e",)]
```

The course baseline is 3.11, so the labs write their own `chunks` and `windows` instead of `batched`.

## 11. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 33 to 34 | error handling with `try`, `except`, `finally` and a bare `except:` around `open()` | section 8: why `with` exists; the bare `except:` and the missing `close()` are shown executed |
| 35 to 36 | iterators; a class with `next` and `__next__` | section 2: the protocol, single-pass behaviour, why `next` is not a Python 3 method |
| 37 to 38 | generators: "faster for large datasets", infinite generator, generator expression | sections 3 and 4: laziness measured, memory measured, speed not promised; cleanup and argument checks |
| 38 to 39 | decorators: "the most important Python concept"; a wrapper without arguments | section 6: arguments, return value, `functools.wraps`, decorators with arguments, order |
| 66 to 68, 79 | `__enter__` / `__exit__(self, *args)`; a `Log` class | section 8: the three `__exit__` arguments, the meaning of the return value, `contextmanager` with `finally`, `ExitStack` |
| 68 | closures | section 5: `nonlocal`, late binding and three fixes |
| 69 | functions as first-class values | section 7 |
| 78 to 79 | `lru_cache(maxsize=None)` | section 6: hashable arguments, unbounded growth, methods |

## 12. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| iterating an iterator twice | the second pass is empty | `list()` it once, or call the function again |
| a generator function that validates its arguments | the error appears at the first `next()` | an ordinary function that checks, then returns the generator |
| opening a file in a generator without `with` | the file stays open when the consumer stops early | `with` inside the generator; `contextlib.closing` for the consumer |
| `itertools.groupby` on unsorted input, or reading a group after advancing | repeated keys; empty groups | sort first; `list()` each group before moving on |
| a lambda created in a loop | every closure returns the last value | default argument, `partial` or a factory function |
| a decorator without `functools.wraps`, `*args` and `return` | lost name, lost arguments, lost result | the three-line pattern of section 6 |
| `@contextmanager` without `try/finally` | cleanup skipped when the block raises | `try: yield  finally: cleanup` |
| `except:` or `except BaseException:` around cleanup-critical code | `Ctrl+C` is swallowed | name the exceptions; let `BaseException` pass |
| `lru_cache(maxsize=None)` on a method or on an open-ended input | memory grows for the life of the program | bound it; cache a plain function of values |

## 13. Check yourself

1. `gen = (x for x in range(3))`; `list(gen)`; `list(gen)`. What does the second `list` return, and why?
2. A generator function begins with `if size < 1: raise ValueError`. When is the error raised, and what is the smallest change that makes it immediate?
3. `fs = [lambda: i for i in range(3)]`. What are the values of `[f() for f in fs]`, and name two fixes.
4. A decorator's wrapper is `def wrapper(): return func()`. Name three things that break.
5. A `@contextmanager` function has code after `yield` but no `try/finally`. What happens to that code when the block raises?

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 14. Sources and verification trail

- Every assertion in this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 (R-097; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). Language reference for the iterator protocol, generators and the `with` statement: <https://docs.python.org/3/reference/datamodel.html>, <https://docs.python.org/3/reference/expressions.html#yield-expressions>, <https://docs.python.org/3/library/contextlib.html>, <https://docs.python.org/3/library/functools.html>, <https://docs.python.org/3/library/itertools.html> (R-005).
- Handbook corrections: finding F-PYH-012 (bare `except:` and unclosed file, the Python 2 `next` method, an unqualified speed claim for generators, a decorator that drops arguments, results and metadata, `__exit__(*args)` examples that open nothing, an unbounded `lru_cache`).
- Not verified here and therefore not claimed: speed differences between generator pipelines and lists (no benchmark was run; the memory comparison is the only measurement), and the behaviour of generators and context managers under `asyncio` (see PY-M06 for asynchronous code).
