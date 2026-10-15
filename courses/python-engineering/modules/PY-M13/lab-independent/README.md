# PY-M13 independent lab - Merge, group, cache and roll back

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`; no network, account or paid service. **Prerequisite:** the guided lab (it shows every technique used here).

You are given **no solution and no step list**. `starter/flowkit.py` contains the four names that the checks import, as stubs, and nothing else. Write the module from this specification. Ten published checks (`python -m pytest`) show the shape of the task; the instructors run a **hidden suite** of many more checks against your `flowkit.py`, built from the three questions of lesson section 9 (how much is consumed, does cleanup run on every path, what is preserved). Passing the published checks is necessary, not sufficient. How you are graded is in `../assessment/rubric.yaml`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M13/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/flowkit.py`. Standard library only (`heapq`, `functools`, `collections` and friends).

## The task

### `merge_sorted(*sources, key=None)`

Merge any number of **already sorted** iterables into one sorted stream, **lazily**. The result is an iterator (a generator).

- Items come out in order of `key(item)` (the item itself if `key` is `None`). When two items have equal keys, the one from the **earlier source** comes first; items themselves are never compared with each other when a key is given.
- Every `source` may be any iterable (list, tuple, string, range, iterator, generator, infinite iterator) or empty; no sources at all gives an empty stream.
- A source that is not iterable raises `TypeError` **when `merge_sorted` is called**, before anything is read from any source.
- Nothing is read from any source until the first item is requested. The first request reads exactly one item from each non-empty source. Afterwards a source is advanced only when the item it produced has been consumed: after the second `next()`, only the source that produced the first item has been read a second time.
- Cleanup: if the merged iterator is closed (`gen.close()`, a `contextlib.closing` block, garbage collection) before it is exhausted, or if it raises (a source raises, or `key` raises), every source that is not exhausted and has a `close` method is closed. If a `close` raises, the others are still closed and the first of those exceptions is raised afterwards.

### `group_runs(iterable, key=None)`

Yield `(key, items)` for every **maximal run of consecutive items with equal keys** (`items` is a new list each time). Keys are compared with `==`, so unhashable keys work. Lazy: it reads no more than one item ahead (after the first group has been yielded, the items of the group and the one that ended it have been read). A non-iterable argument raises `TypeError` at the call. Empty input gives nothing. An exception from `key` propagates.

### `memo(maxsize=128)`

A decorator **factory**: a bounded cache with *least recently used* eviction.

- Calls with equal arguments return the remembered result without calling the function. Positional and keyword arguments are part of the key; the **order of keyword arguments does not matter**, but `f(1, b=2)` and `f(a=1, b=2)` are separate entries (the same as `functools.lru_cache`).
- A cache **hit** makes the entry the most recently used. When the cache holds more than `maxsize` entries, the least recently used one is dropped. `maxsize=None` means unbounded; `maxsize=0` remembers nothing (every call is a miss).
- The same result **object** is returned each time (no copies). Results that are falsy or `None` are cached like any other.
- Arguments that cannot be hashed do not raise: the function is called and nothing is remembered (it counts as a miss). **An exception raised by the function is not remembered.**
- The wrapper keeps the function's name, docstring and `__wrapped__`. It gets two methods: `cache_info()`, a dict `{"hits": ..., "misses": ..., "size": ..., "maxsize": ...}`, and `cache_clear()`, which empties the cache **and resets the counters**.
- `maxsize` must be `None` or an `int` that is not a `bool` (`TypeError`) and not negative (`ValueError`), checked when `memo(...)` is called.
- Each decorated function has its own cache; the decorator works on methods (the instance is part of the key).

### `Transaction(target)`

A context manager that guards a **dict**: if the block raises (any exception, including `KeyboardInterrupt`), the dict is restored to its state at entry and the exception **is not suppressed**; if the block succeeds, the changes stay.

- `target` must be a `dict` (a subclass is fine); anything else is a `TypeError` at construction.
- `__enter__` returns the very same dict object. Restoring keeps the object's identity and its key order, removes keys added in the block and restores keys changed or deleted.
- Transactions **nest**: an inner failure rolls back only the inner block; an outer failure also undoes a committed inner block; the same `Transaction` object can be entered again, also while it is active. Two transactions on different dicts do not interfere.
- The snapshot is **shallow**: a mutable value changed in place (for example `d["items"].append(2)`) is not rolled back. Document that limit in your notes.

## Suggested order (not a step list)

Start with `Transaction` (smallest), then `group_runs`, `memo` and `merge_sorted`. Run the published checks after each part. When they pass, write `notes.md` and ask the three questions of lesson section 9 about each function.

## What you hand in

1. `starter/flowkit.py`.
2. `notes.md` (half a page): for each of the four, how much it consumes or remembers and what releases it; where your cleanup runs (and which test would prove it); one design decision you reconsidered, and why.

## Hints that are not solutions

- `heapq` compares tuples; put something in the tuple that makes ties deterministic and keeps items from ever being compared.
- A generator function runs no code at the call; a function that *returns* a generator does. Choose by when an error should appear.
- `try/finally` around the `yield` of a generator is what runs on `close()`.
- `functools.wraps` copies the metadata; a decorator with arguments has three levels.
- Restoring a dict in place needs `clear()` and `update()`, not a new dict.
