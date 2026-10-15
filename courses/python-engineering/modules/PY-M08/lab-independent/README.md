# PY-M08 independent lab - A case tracker that survives concurrent edits, retries and an old database

**Time:** about 3 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`; no network, account or paid service. **Prerequisite:** the lesson (sections 5 to 9 show every technique used here with executed examples) and the guided lab.

You are given **no solution and no step list**. `starter/casestore.py` contains the names, the value classes and the error classes that the checks import, with every method an empty stub. Ten published checks (`python -m pytest`) show the shape of the task; the instructors run a **hidden suite** of many more checks against your `casestore.py`, built from the same questions as the lesson: what is data and what is code, what is atomic, what happens on a retry, what does the old database look like, and how many statements does this call run. Passing the published checks is necessary, not sufficient. How you are graded is in `../assessment/rubric.yaml`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M08/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/casestore.py`. Standard library only (`sqlite3`, `contextlib`, `dataclasses`, `datetime`, ...).

## The task

A security team tracks **cases** (investigations) and the **comments** analysts add to them. Build `Store`, a persistence layer on SQLite. The team has run a first release for months: its database file exists and must be upgraded without losing a row.

### Rules for the whole module

- **Every value reaches SQL as a bound parameter.** The only text you may place into a statement with string formatting is a fixed fragment your own code chose (a column name from an allow-list, a run of question marks).
- **A method that changes data runs in one transaction that takes the write lock first** (`BEGIN IMMEDIATE`, then `COMMIT`, or `ROLLBACK` on any failure including `KeyboardInterrupt`). A method that fails changes nothing. A method that only reads opens no transaction.
- Keep the connection in `self._db` (the checks trace it). Open it in autocommit mode (`isolation_level=None`) so that the transactions are the ones you write.
- Foreign keys are enforced; wait up to 5 seconds for a lock (`timeout=5` and `PRAGMA busy_timeout=5000`).
- A new database **file** is created readable and writable only by its owner (mode `0o600`) whatever the umask; an existing file keeps its mode; an empty path is a `ValueError`; `":memory:"` is allowed. If opening fails after the connection exists, the connection is closed.
- Ids (of cases and of comments) are never handed out again after their row was deleted, and after an upgrade they continue above the highest id the first release used.
- Times are timezone-aware UTC `datetime` objects; they are stored as fixed-width UTC text (`isoformat(timespec="microseconds")`). `clock` returns the current time; a naive time from the clock is a `ValueError` when it is used.

### Values

`Case(id, ref, title, reporter, severity, status, version, created_at, updated_at, comment_count)`, `Comment(id, case_id, author, text, created_at)` and `ImportReport(inserted, updated, unchanged)` are frozen dataclasses (given). `comment_count` is computed, not stored. `version` is 1 for a new case and grows by exactly 1 with every change to the case itself (title, severity, status); adding a comment does not change it.

Limits: `title` 1 to 200 characters, `reporter` and `author` 1 to 120, comment `text` 1 to 2000, `ref` 1 to 100 characters without control characters (code points below 32 and 127). Text that is only spaces is invalid. `severity` is an `int` from 1 to 4: a `bool` or a non-int is a `TypeError`, an `int` outside the range a `ValueError`. Invalid text (not a `str`, the wrong length, or only spaces) is a `ValueError`. `limit` is an `int` (not a `bool`) from 1 to 100, otherwise `ValueError`. A case id that is not an `int` is a `TypeError`.

### `Store(path=":memory:", *, clock=None)` and `close()`

A context manager that closes on exit. `store.orphans_dropped` is described under "The first release's database".

### Cases

- `open_case(title, reporter, severity=2, *, ref=None) -> Case`: a new open case, `version == 1`, `created_at == updated_at ==` the clock time, `comment_count == 0`. With a `ref`, the call is **idempotent**: if a case with that `ref` exists and has the same title, reporter and severity, return the stored case and change nothing; if it differs, raise `RefConflict` (a `ValueError`) and change nothing. Two cases cannot share a `ref` (the database enforces it); `ref=None` may repeat.
- `get(case_id) -> Case`; `CaseNotFound` (a `LookupError`) if there is none.
- `update_case(case_id, *, expected_version, title=None, severity=None) -> Case`: **optimistic concurrency.** Apply the change only if the stored version is `expected_version`; the new case has `version + 1` and `updated_at` from the clock. Order of the errors: no such case -> `CaseNotFound`; version differs -> `StaleVersion` (its attribute `.current` is the stored version); both `title` and `severity` `None` -> `ValueError` before anything else is looked at. The check and the write must be one statement or one transaction: two writers holding the same version cannot both win. `expected_version` is an `int` of at least 1, otherwise `ValueError`.
- `close_case(case_id, *, expected_version)` and `reopen_case(...)` change the status (`open` / `closed`) with the same rules and the same errors, plus `InvalidTransition` (a `ValueError`) when the version matches but the case already has the requested status. A stale version is reported before an invalid transition.
- `delete_case(case_id, *, expected_version) -> None`: same rules; the comments of the case are deleted with it (the database does it).

### Comments

- `add_comment(case_id, author, text) -> Comment`: `CaseNotFound` if there is no such case. The case row does not change.
- `comments(case_id, *, after_id=None, limit=50) -> list[Comment]`: the comments of one case in id order, strictly after `after_id` (`None` means from the start; an `int` below 0 is a `ValueError`), at most `limit`. `CaseNotFound` if there is no such case (an existing case without comments gives `[]`).

### Queries

- `find(*, reporter=None, status=None, min_severity=None, text=None, after_id=None, limit=50) -> list[Case]`: the cases matching **all** the given filters in id order, strictly after `after_id`, at most `limit`, each with its `comment_count`. `reporter` is an exact match; `status` is `"open"` or `"closed"` (`ValueError` otherwise); `min_severity` as for severity; `text` (1 to 200 characters) matches when the title **or any comment of the case** contains it, ignoring ASCII case, with `%`, `_` and a backslash taken literally. **One `SELECT` statement per call**, whatever the number of cases and comments, and it must not read every comment of the table for every case it returns.
- `stats() -> dict`: `{"open": n, "closed": n, "comments": n, "by_severity": {1: n, 2: n, 3: n, 4: n}}` with all four severities present (zero counts included); at most **two** `SELECT` statements.

### `import_cases(rows) -> ImportReport`

Bulk, idempotent, all or nothing. `rows` is any iterable of mappings with the keys `ref` (required), `title` (required), `reporter` (required), `severity` (default 2) and `status` (default `"open"`); any other key is invalid. At most 1000 rows. Validate **every** row before the transaction starts; the first invalid row raises `ImportRejected(index, reason)` (a `ValueError` with attributes `.index`, the position of the row, and `.reason`) and nothing is written. The same `ref` twice in one import is invalid. Then, in one transaction, for each row: no case with that `ref` -> insert (counted in `inserted`); a case with that `ref` and identical title, reporter, severity and status -> `unchanged`; otherwise update those four fields (`version + 1`, `updated_at` from the clock; counted in `updated`). Importing the same rows again therefore changes nothing and reports only `unchanged`.

### The first release's database

The first release created this schema and never stored a schema version:

```sql
CREATE TABLE cases (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    reporter TEXT NOT NULL,
    severity INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

`Store(path)` on such a file must upgrade it in place, **atomically and once**, keeping every case and comment with its id, text and time: the upgraded cases have `ref=None`, `version=1` and `updated_at == created_at`. The upgraded database enforces what the first one never did: `ref` unique, status limited to `open`/`closed`, severity 1 to 4, and a foreign key from `comments.case_id` to `cases.id` **with cascade delete**. The first release never enforced its foreign key, so its file may contain **orphan comments** (their case does not exist): they are not carried over, and `store.orphans_dropped` is their number (0 for any other database). Opening an upgraded file again changes nothing. A schema version is stored in the file (`PRAGMA user_version`); a file whose version is higher than your program knows raises `SchemaTooNew` (a `RuntimeError`) and is left untouched. A failing upgrade (for example a first-release row that the new constraints refuse) raises and leaves the tables and rows exactly as the first release had them: no half-built table, no lost row (a stored version of 0 or 1 is fine, 1 being the first release's own schema). SQLite cannot add a constraint to an existing table: lesson section 7 shows how it is done.

### Query cost

The hidden suite counts statements (`set_trace_callback`) and also the work SQLite does (`set_progress_handler`) on a database with a few hundred cases and a few thousand comments. `find` and `comments` must use indexes for the lookups they do.

## Suggested order (not a step list)

Start with opening, the schema and the migration of the first release's file (write the migration test data yourself from the DDL above). Then `open_case`/`get`, the version rules, comments, `find`, `stats`, and last `import_cases`. After each part run the published checks, and try to break your own code: a hostile string in every parameter, a second `Store` on the same file holding an old version, an exception in the middle of a method, a clock that returns a naive time.

## What you hand in

1. `starter/casestore.py`.
2. `notes.md` (half a page): where you use a transaction and why each one is as long as it is; how `update_case` guarantees that two writers with the same version cannot both succeed; which indexes you created and which query each one serves; one migration risk you considered and what you did about it.

## Hints that are not solutions

- `cursor.rowcount` after an `UPDATE ... WHERE id = ? AND version = ?` tells you whether the guard matched; the code that explains a miss (missing or stale?) runs inside the same transaction.
- A correlated `COUNT(*)` subquery per case is one statement, but without an index it reads the whole comments table for every case.
- `INSERT INTO new SELECT ... FROM old WHERE ...` copies rows; `PRAGMA foreign_key_list(table)` shows the foreign keys a table really has.
- A column name cannot be a bound parameter, and `ORDER BY ?` sorts by a constant: use an allow-list when a name must vary.
- If two things must compare equal after a retry, decide which fields make "the same request".
