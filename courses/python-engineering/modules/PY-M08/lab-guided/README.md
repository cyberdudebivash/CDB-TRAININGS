# PY-M08 guided lab - A persistent event store that is safe, idempotent and versioned

**Time:** about 3 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`. No network, no account and no paid service: everything runs on your computer, and SQLite is part of Python.

You build `EventStore`, the storage layer of a small support or security tool: events arrive (sometimes twice), are stored once, read back page by page, searched, retained for a while and kept in a schema that can grow. `starter/eventstore.py` holds the names, the docstrings, the exceptions, the migrations and the `Event` value; **every body that raises `NotImplementedError` is yours**. Each docstring is the specification and `checks/` holds the tests.

**History of this lab.** Part 1 (steps 1 to 5: open, close, idempotent append, seek pagination, count; the 14 contract tests in `checks/test_eventstore.py`) is the first increment of this lab, merged in `cyberdudebivash/CDB-TRAININGS#4`. Part 2 (steps 6 to 10: migrations, atomic batches, injection-safe search, retention, query shape; the other checks) was added to turn it into a complete module. The Part 1 contract is unchanged.

## Setup

```bash
cd courses/python-engineering/modules/PY-M08/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/eventstore.py`. Run one step with `python -m pytest checks/test_step6_migrations.py` (also `test_step3_validation.py`, `test_step7_batch.py`, `test_step8_search.py`, `test_step9_retention.py`, `test_step10_query_shape.py`); the 14 contract tests of Part 1 are `checks/test_eventstore.py`, which also runs with the standard library alone (`python -m unittest discover -s checks -p "test_eventstore.py"`).

`PY_M08_TARGET=solution python -m pytest` (or `LAB_TARGET=solution`) checks the public reference instead of your work; read `solution/eventstore.py` only after your own version passes, and compare the *shape* of the two. The checks open a store **inside** each test, so a step you have not written yet is reported as a failed check with the step's name, never as a set-up error.

A note on the order: the steps build on each other (search needs the validation of step 3, the migration of step 6 runs when you open the store), so work in order and keep earlier checks green.

## The case

A support platform receives event messages that can be delivered more than once. Store one canonical copy of each event; tell an exact retry from a conflicting submission; validate timestamps; give customer-scoped timelines page by page; evolve the schema without losing data; and keep the file private. Everything here is a controlled local demonstration: no network, no cloud resource, no customer data. Never present synthetic local SQLite operations as a live customer integration.

## Part 1 - The first release (steps 1 to 5)

### Step 1 - open the store (LO2, LO3)

`EventStore(filename=":memory:", *, clock=None)` opens a connection with `timeout=5` and `isolation_level=None` (autocommit: the transactions are the ones you write), keeps it in `self._db`, turns on `PRAGMA foreign_keys` and `PRAGMA busy_timeout=5000`, and calls `migrate` (step 6). Read the docstring for the three extra rules (empty path, private file, close on failure); most of them are checked in step 6's file because they need the migration. Lesson sections 4, 5 and 10.

### Step 2 - close it (LO2)

`close()` closes the connection; closing twice is harmless; `with EventStore(path) as store:` closes on exit (given).

### Step 3 - append: validate, normalise, decide inside one transaction (LO1, LO2, LO5)

Write `_identifier`, `_utc` and `_prepare` (everything is validated **before** the transaction: a bad event touches nothing), then `append`:

- `BEGIN IMMEDIATE`; look the `event_id` up; **exact retry** (same entity, type, time and payload) returns `False` and changes nothing; **same id with other content** raises `IdempotencyConflict` and changes nothing; otherwise insert and return `True`; `COMMIT`; on any failure, **including `KeyboardInterrupt`**, `ROLLBACK` and re-raise.
- Values are bound parameters. The payload is stored as compact JSON with sorted keys, so two payloads with the same content give the same text, and the size limit counts UTF-8 bytes of that text.
- The time of receipt (`self._now()`, given) is stored in the `received_at` column that migration 3 adds; a retry never changes it.

Run `python -m pytest checks/test_eventstore.py checks/test_step3_validation.py`. Lesson sections 3, 4 and 8.

### Step 4 - `list_for_entity`: seek pagination (LO1, LO5)

The events of one entity ordered by `(occurred_at, event_id)`, at most `limit`, strictly after a cursor `(timestamp text, event_id)` compared as a **pair**. Write `_limit` (a strict `int` from 1 to 100) and the query. Order the query by `occurred_at, event_id` **in the SQL**: the check `test_the_order_of_a_page_is_in_the_query_not_in_the_index` drops the index to see whether you rely on it. Lesson section 9.

### Step 5 - `count` (LO3)

The number of stored events.

## Part 2 - Making it maintainable (steps 6 to 10)

### Step 6 - `migrate()`: a versioned schema (LO4)

`MIGRATIONS` is given. Write `schema_version` and `migrate`: each migration in its **own** `BEGIN IMMEDIATE` transaction together with `PRAGMA user_version = n`; read the version **after** the lock is taken; refuse a database from the future (`SchemaTooNew`, untouched); do nothing when current and leave no transaction open; `StoreError` inside a transaction; roll back on `BaseException`. Then finish step 1's `__init__`: a database created by the first release has **version 0 and tables already in it**, and must be adopted with its rows (read why migration 1 says `IF NOT EXISTS`). Run `python -m pytest checks/test_step6_migrations.py`. Lesson section 7.

In `notes.md`: why does `executescript()` make a poor migration runner (lesson sections 4 and 7), and what would two processes starting together do if you read `user_version` before taking the lock?

### Step 7 - `append_many()`: a batch is one transaction (LO2, LO5)

Validate the whole batch first, then one `BEGIN IMMEDIATE ... COMMIT`; a conflict anywhere rejects **all** of it; duplicates (stored before, or repeated inside the batch) are counted. Reuse what you wrote in step 3: a private helper that works inside an open transaction is the natural way. Run `python -m pytest checks/test_step7_batch.py`.

In `notes.md`: what does the statement-count check in `test_a_batch_is_one_transaction` tell you about the cost of appending 1,000 events one at a time?

### Step 8 - `search()` and `count_by_type()`: user input is data (LO1)

Build the `WHERE` clause from **fixed fragments joined with `AND`**, bind every value, escape `LIKE` wildcards (`_like_pattern`) and pick the `ORDER BY` column from `ORDER_COLUMNS`. The injection battery in `checks/test_step8_search.py` sends ten hostile strings to three parameters. Run `python -m pytest checks/test_step8_search.py`. Lesson section 3.

In `notes.md`: write the sentence that explains why `ORDER BY ?` would pass your tests for the ordering you chose first and fail for the other columns.

### Step 9 - retention: purge by time of receipt (LO3, LO5)

`received_at(event_id)` and `purge_received_before(cutoff)`. Retention counts from the moment the store **received** an event, not from when it happened: an old event that arrives late must survive the next purge. Run `python -m pytest checks/test_step9_retention.py`.

### Step 10 - the shape of a query (LO5)

`explain(sql, params)` returns the plan steps as strings. The checks then look at your own queries: one `SELECT` for a page, an index for the entity and for the type, one short transaction per append, no transaction for a read. Run `python -m pytest checks/test_step10_query_shape.py`. Lesson section 9.

In `notes.md`: `search(text=...)` cannot use an index. Say why (lesson section 9), and what a real system would do for a large table (name the feature; do not build it).

## Questions that belong in `notes.md` (from the first release of this lab)

1. Explain why `INSERT OR REPLACE` can silently corrupt an event history (lesson section 8, and the cascade in the executed example).
2. Show, with your own test in `checks/test_mine.py`, that a SQL injection probe in an **event payload** is stored as data and found again.
3. Extend the provided negative tests with two cases of your own for identifiers (a tab, a very long id).
4. Document when SQLite's single-process model is unsuitable for a distributed production environment (lesson section 10).

## When you are done

All checks pass and `notes.md` has your answers. Then read `solution/eventstore.py` and compare where each of you keeps state, which exceptions each raises, and where each transaction begins and ends. The independent lab asks you to build a different store (cases and comments, with optimistic locking and an old database to upgrade) from a specification, with no starter code.

## What the checks do not tell you

They test behaviour, not design taste, and they cannot tell you that a name is confusing or that a helper does two jobs. They cannot see concurrent processes either: the lock-order checks look at the statements you run, which is evidence of the design, not a stress test. An automated check run is not a review by an experienced engineer, and the module has not been used with learners.
