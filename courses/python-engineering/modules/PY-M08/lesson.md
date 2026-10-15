---
id: PY-M08
title: "Databases and persistence: safe SQL, transactions, repositories, migrations and query cost"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M01, PY-M02 and PY-M12 and now need to store data safely: tools that keep events, cases or inventory in a file and must not lose, duplicate, leak or let anyone rewrite it"
prerequisites:
  - "PY-M01 (language core), PY-M02 (functions, errors and pytest) and PY-M12 (classes and dataclasses); PY-M13 (context managers) helps"
  - "Python 3.11 or newer; the labs and every code block of this lesson were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "pytest 9.1.1 from labs/requirements.txt; no network, no account, no paid service, no database server: SQLite is part of Python"
estimated_time_hours: {lesson: 2.5, guided_lab: 3.0, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); behaviour of the sqlite3 module by version executed in this lesson (R-098)", sqlite: "the library bundled with the interpreter: 3.45.1 on the 3.11 to 3.13 builds and 3.53.1 on the 3.14 and 3.15 builds used here; nothing in the labs needs more than 3.35", pytest: "9.1.1"}
last_verified: 2026-10-15
---

# PY-M08 - Databases and persistence

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Put data into SQL only as bound parameters, show with an exploit that string formatting is injectable and parameters are not, and handle the three things that cannot be parameters: identifiers, `ORDER BY` and `LIKE` wildcards. |
| **LO2** | Use transactions correctly: know what `with conn` does and does not do, make a multi-step change atomic, roll back on every failure, close connections, and explain what the connection's default settings (foreign keys off, implicit transactions) do to you. |
| **LO3** | Build a repository layer that keeps all SQL in one place, maps rows to typed values, lets constraints be the second line of defence, and turns database errors into the errors your program defines. |
| **LO4** | Evolve a schema safely: versioned, atomic, forward-only migrations; adopt a database that has no version; rebuild a table to add a constraint; refuse a database from the future. |
| **LO5** | Make writes idempotent and concurrency-safe (retries, conflicts, optimistic locking) and judge a query by its shape: how many statements it runs, whether an index serves it, and how it pages. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Almost every tool a security or operations team writes ends up keeping something: events, cases, indicators, inventory, results. The first version is a `sqlite3.connect()` and an `INSERT`. The failures arrive later: a quote in a hostname changes the meaning of a query; a crash leaves half a change behind; a retry creates a duplicate; two analysts overwrite each other; a schema change needs the old file to keep working; a report that took a second now takes a minute.

The 2025 handbook shows the database code of a log-analysis tool (PDF pages 141 to 142 and 154 to 156) and a Flask site (pages 234 to 241). The examples are short and mostly work, and several habits in them fail in production. Each of these is executed in this lesson on five Python versions:

- the **`save_event`** function (page 154 to 155) binds its values correctly, which is good, but it opens a connection, runs `CREATE TABLE IF NOT EXISTS` and commits **for every event**, and closes the connection only on the happy path: any error in between leaks the connection (sections 4 and 6);
- the **report** (page 156) opens a connection and never closes it (section 4);
- the **MySQL** and **PostgreSQL** examples (pages 141 to 142) put the user `root` and a password in the source code and never close the connection (sections 3, 4 and 10);
- the Flask site creates its tables with **`db.create_all()`** (page 236) and keeps a `SECRET_KEY` in `config.py` (page 240): `create_all()` creates missing tables and does not change existing ones, so the first schema change has no path (section 7);
- document-store examples (pages 142, 172 to 174, 181 to 182) are outside this module, which teaches the relational ideas that carry over: parameters, transactions, constraints, migrations and query cost.

The labs build a persistent event store (guided: ten steps, a safe write, a versioned schema, a batch, an injection-safe search, retention and query shape) and a case tracker with optimistic concurrency that upgrades an older database (independent). Everything runs on your computer: SQLite needs no server, no account and no network.

## 2. SQLite from Python in ten minutes (LO1, LO3)

`sqlite3` is in the standard library. A **connection** is one open database; a **cursor** runs statements; rows come back as tuples unless you ask for something else:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")                     # a private database that lives as long as this connection
conn.execute("CREATE TABLE note (id INTEGER PRIMARY KEY, author TEXT NOT NULL, text TEXT NOT NULL)")
cur = conn.execute("INSERT INTO note (author, text) VALUES (?, ?)", ("alice", "first"))
assert cur.lastrowid == 1 and cur.rowcount == 1       # the new id, and how many rows the statement changed
assert conn.execute("SELECT id, author FROM note").fetchall() == [(1, "alice")]       # tuples by default

conn.row_factory = sqlite3.Row                         # rows that can be read by name (set it once, right after connecting)
row = conn.execute("SELECT id, author, text FROM note").fetchone()
assert row["author"] == "alice" and row[0] == 1 and row.keys() == ["id", "author", "text"]
assert conn.execute("SELECT * FROM note WHERE id = ?", (99,)).fetchone() is None      # no row: None, not an exception
assert conn.execute("UPDATE note SET text = ? WHERE author = ?", ("changed", "nobody")).rowcount == 0
conn.close()
```

Three details matter for everything that follows:

- **`:memory:` is per connection.** Two `connect(":memory:")` calls give two empty, unrelated databases. A file path gives a database that outlives the program.
- **`rowcount` is how you learn what a statement did.** An `UPDATE` that matched nothing is not an error. Section 8 builds optimistic locking on that fact.
- **SQLite types are flexible.** A column's declared type is an *affinity*, a preference, not a rule:

```python run
import datetime
import sqlite3
import sys
import warnings

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t (i INTEGER, s TEXT)")
conn.execute("INSERT INTO t VALUES (?, ?)", ("12", 34))            # text into an INTEGER column, a number into a TEXT column
assert conn.execute("SELECT i, typeof(i), s, typeof(s) FROM t").fetchone() == (12, "integer", "34", "text")      # converted when it looks right
conn.execute("INSERT INTO t VALUES (?, ?)", ("abc", 1))            # ... and stored as it is when it does not
assert conn.execute("SELECT typeof(i) FROM t WHERE i = 'abc'").fetchone()[0] == "text"

try:
    import decimal
    conn.execute("SELECT ?", (decimal.Decimal("1.1"),))            # types SQLite has no notion of cannot be bound
except sqlite3.ProgrammingError:
    pass
else:
    raise AssertionError("a Decimal should not be bindable")

# Times: store ISO-8601 text. The module's built-in date adapters were deprecated in 3.12 and warn from then on.
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    conn.execute("INSERT INTO t (s) VALUES (?)", (datetime.date(2026, 10, 15),))
assert conn.execute("SELECT s FROM t WHERE s LIKE '2026%'").fetchone()[0] == "2026-10-15"
assert (DeprecationWarning in {w.category for w in caught}) == (sys.version_info >= (3, 12))
fixed = datetime.datetime(2026, 10, 15, 8, 30, tzinfo=datetime.timezone.utc).isoformat(timespec="microseconds")
assert fixed == "2026-10-15T08:30:00.000000+00:00"
# Fixed-width text in ONE time zone sorts alphabetically in time order, which is what ORDER BY and range queries rely on.
assert sorted(["2026-11-01T00:00:00.000000+00:00", "2026-10-09T23:59:59.000000+00:00", fixed]) == ["2026-10-09T23:59:59.000000+00:00", fixed, "2026-11-01T00:00:00.000000+00:00"]
```

The habit to take away: **decide the representation yourself.** Times as fixed-width UTC text, money as integer cents, booleans as 0 or 1, JSON as text. A `STRICT` table (section 5) makes SQLite enforce the declared types.

## 3. Parameters: the only safe way to put data into SQL (LO1)

SQL **injection** happens when text from outside becomes part of the *statement* instead of staying a *value*. The attacker does not need to break anything: a quote ends the string you meant, and the rest is read as SQL. Here is the same lookup written twice, with a hostile input:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript("""
    CREATE TABLE items (label TEXT, price TEXT);
    CREATE TABLE users (name TEXT, pw TEXT);
    INSERT INTO items VALUES ('pen', '1');
    INSERT INTO users VALUES ('alice', 'secret1');
""")


def find_unsafe(label):
    return conn.execute(f"SELECT label, price FROM items WHERE label = '{label}'").fetchall()


def find_safe(label):
    return conn.execute("SELECT label, price FROM items WHERE label = ?", (label,)).fetchall()


attack = "pen' UNION SELECT name, pw FROM users --"
assert find_unsafe(attack) == [("alice", "secret1"), ("pen", "1")]       # the password column came out through the "price" column
assert find_safe(attack) == []                                            # the whole string is one label, and no label looks like that

always_true = "' OR '1'='1"
assert len(find_unsafe(always_true)) == 1 and find_safe(always_true) == []     # every row matches the injected condition
```

With `?` the statement text is fixed *before* any value is known. SQLite compiles the statement, then binds the values into it as data; no value can change the structure. That is why the rule is absolute: **every value that comes from outside reaches SQL through a placeholder.** There is no escaping function to remember and no "safe enough" input.

### What `sqlite3` already stops, and what it does not

The classic `'; DROP TABLE items; --` payload fails against `execute()` for a reason that is easy to misread as safety:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE items (label TEXT)")
payload = "x'; DROP TABLE items; --"
try:
    conn.execute(f"SELECT * FROM items WHERE label = '{payload}'")
except sqlite3.ProgrammingError as exc:
    assert "one statement" in str(exc)                    # execute() runs ONE statement and refuses a second
else:
    raise AssertionError("expected a refusal")
assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'items'").fetchone()[0] == 1

conn.executescript(f"SELECT * FROM items WHERE label = '{payload}'")          # executescript() runs them all
assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'items'").fetchone()[0] == 0     # the table is gone
```

So `execute()` protects you from stacked statements, not from `UNION`, `OR 1=1` or a subquery; and `executescript()` protects you from nothing. **Never pass text from outside to `executescript()`**; use it only for trusted, fixed scripts.

The same mistake exists outside SQL: handbook page 373 builds a shell command with an f-string (`os.system(f"iptables -A INPUT -s {ip} -j DROP")`), and any `ip` that contains `; rm -rf ...` becomes more commands. The fix has the same shape (pass the value separately, as an argument list, never inside the text) and is taught in PY-M07.

### Three things that cannot be parameters

A placeholder stands for a **value**. It cannot stand for a table name, a column name or a keyword. The three cases that tempt people into string formatting:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
conn.executemany("INSERT INTO t (name) VALUES (?)", [("b",), ("a",), ("c",)])

# 1. A table or column name is not a value.
try:
    conn.execute("SELECT * FROM ?", ("t",))
except sqlite3.OperationalError:
    pass
else:
    raise AssertionError("a table name cannot be a parameter")

# 2. ORDER BY ? is accepted and does nothing: it sorts by the constant string "name".
assert [r[0] for r in conn.execute("SELECT name FROM t ORDER BY ?", ("name",))] == ["b", "a", "c"]      # insertion order, not sorted
assert [r[0] for r in conn.execute("SELECT name FROM t ORDER BY name")] == ["a", "b", "c"]

# The fix: choose the text from an allow-list your own code owns.
SORTABLE = {"name": "name", "id": "id"}


def names(order_by="id", descending=False):
    if order_by not in SORTABLE:
        raise ValueError(f"cannot sort by {order_by!r}")
    direction = "DESC" if descending else "ASC"
    return [r[0] for r in conn.execute(f"SELECT name FROM t ORDER BY {SORTABLE[order_by]} {direction}, id {direction}")]


assert names("name") == ["a", "b", "c"] and names("name", True) == ["c", "b", "a"]
try:
    names("name; DROP TABLE t")
except ValueError:
    pass
assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 3

# 3. A list of values: build the run of question marks, never the values.
ids = [1, 3]
marks = ", ".join("?" * len(ids))
assert [r[0] for r in conn.execute(f"SELECT name FROM t WHERE id IN ({marks})", ids)] == ["b", "c"]
```

The dictionary lookup is what makes `f"... {SORTABLE[order_by]} ..."` safe: the text that reaches the statement is one of the strings *you* wrote, never the caller's. The same pattern serves a dynamic `WHERE`: fixed fragments such as `"severity >= ?"` are joined with `AND`, and the values travel separately.

### `LIKE`: the wildcards are data too

A parameter protects the *statement*; it does not stop a user's `%` from being a wildcard *inside* the `LIKE` pattern. Searching for `100%` should find the text `100%`, not everything that starts with `100`:

```python run
import sqlite3


def like_pattern(text):
    """'%text%' with the wildcards of `text` turned into ordinary characters (use with ESCAPE '\\')."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE msg (text TEXT)")
conn.executemany("INSERT INTO msg VALUES (?)", [("Disk 100% full",), ("100 percent sure",), ("user_name",), ("userXname",)])

naive = [r[0] for r in conn.execute("SELECT text FROM msg WHERE text LIKE ?", ("%100%%",))]
assert sorted(naive) == ["100 percent sure", "Disk 100% full"]                       # the user's % matched anything
exact = [r[0] for r in conn.execute("SELECT text FROM msg WHERE text LIKE ? ESCAPE '\\'", (like_pattern("100%"),))]
assert exact == ["Disk 100% full"]
assert [r[0] for r in conn.execute("SELECT text FROM msg WHERE text LIKE ? ESCAPE '\\'", (like_pattern("user_name"),))] == ["user_name"]
assert conn.execute("SELECT 'ABC' LIKE 'abc'").fetchone()[0] == 1                 # LIKE ignores the case of ASCII letters; use GLOB or a collation for exact case
```

Escaping the backslash first matters: it is the escape character itself.

### What to test

A test for injection-safety does not call the function once with a quote. It sends a **battery** of hostile strings to **every** parameter, and checks three things after each: the call returned only what the data justifies (usually nothing), the schema is intact, and the row count did not change. The guided lab's step 8 has exactly this test; the lab's checks were validated by replacing a correct parameter with string formatting and confirming that the test notices.

## 4. Transactions: all of a change, or none of it (LO2)

A **transaction** is a group of statements that succeed or fail together, and that other connections see only when it is complete. The mistake to avoid is a half-finished change that stays on disk: a transfer that debited one account and never credited the other.

By default `sqlite3` opens a transaction for you **before the first `INSERT`, `UPDATE` or `DELETE`** and leaves it open until you call `commit()` or `rollback()` (this is called legacy transaction control). Two consequences are worth seeing:

```python run
import contextlib
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE account (name TEXT PRIMARY KEY, cents INTEGER NOT NULL CHECK (cents >= 0))")
conn.executemany("INSERT INTO account VALUES (?, ?)", [("alice", 1000), ("bob", 0)])
assert conn.in_transaction                                  # the INSERT opened one
conn.commit()
assert not conn.in_transaction


def transfer(conn, source, target, cents):
    """Both updates happen, or neither does. `with conn` commits on success and rolls back on any exception."""
    with conn:
        conn.execute("UPDATE account SET cents = cents - ? WHERE name = ?", (cents, source))
        conn.execute("UPDATE account SET cents = cents + ? WHERE name = ?", (cents, target))


transfer(conn, "alice", "bob", 300)
assert dict(conn.execute("SELECT name, cents FROM account")) == {"alice": 700, "bob": 300}

try:
    transfer(conn, "alice", "bob", 5000)                    # the CHECK constraint refuses the first UPDATE ...
except sqlite3.IntegrityError:
    pass
assert dict(conn.execute("SELECT name, cents FROM account")) == {"alice": 700, "bob": 300}       # ... and nothing changed

# `with conn` ends the transaction. It does NOT close the connection.
assert conn.execute("SELECT 1").fetchone() == (1,)
with contextlib.closing(conn):                              # closing() is what closes
    pass
try:
    conn.execute("SELECT 1")
except sqlite3.ProgrammingError:
    pass
else:
    raise AssertionError("the connection should be closed")
```

The handbook's `save_event` opens, writes, commits and closes in a straight line. When the write raises, `close()` is never reached. Python 3.13 and later even say so when a connection is garbage-collected while still open:

```python run
import gc
import sqlite3
import sys
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    leaked = sqlite3.connect(":memory:")
    del leaked
    gc.collect()
assert (ResourceWarning in {w.category for w in caught}) == (sys.version_info >= (3, 13))    # 3.13 added the warning; earlier versions leak silently
```

### Two details of the default behaviour that surprise people

```python run
import sqlite3

# 1. A rollback undoes EVERYTHING since the last commit, including statements outside the `with` block.
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t (v TEXT)")
conn.commit()
conn.execute("INSERT INTO t VALUES ('written before the block')")           # opens a transaction that nobody committed
try:
    with conn:
        conn.execute("INSERT INTO t VALUES ('written inside the block')")
        raise RuntimeError("the block fails")
except RuntimeError:
    pass
assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0           # both rows are gone

# 2. executescript() commits first, whatever was pending, and then runs its statements.
conn.execute("INSERT INTO t VALUES ('pending')")
assert conn.in_transaction
conn.executescript("CREATE TABLE other (x)")
assert not conn.in_transaction
conn.rollback()                                                             # too late: 'pending' was committed by executescript
assert conn.execute("SELECT v FROM t").fetchall() == [("pending",)]
```

### Choosing who controls the transaction

For anything where the order of statements and the moment of locking matter (migrations, check-then-write, batches), take control: connect with `isolation_level=None` (autocommit: the module issues no `BEGIN` for you) and write `BEGIN IMMEDIATE`, `COMMIT` and `ROLLBACK` yourself.

```python run
import sqlite3

conn = sqlite3.connect(":memory:", isolation_level=None)
conn.execute("CREATE TABLE t (v TEXT)")
assert not conn.in_transaction                                              # nothing opens by itself now


def add_all(conn, values):
    conn.execute("BEGIN IMMEDIATE")                                         # take the write lock now, not at the first write
    try:
        for v in values:
            conn.execute("INSERT INTO t VALUES (?)", (v,))
        conn.execute("COMMIT")
    except BaseException:                                                   # also KeyboardInterrupt: never leave a transaction open
        conn.execute("ROLLBACK")
        raise


add_all(conn, ["a", "b"])
try:
    add_all(conn, ["c", None.__class__])                                    # the second value cannot be bound
except sqlite3.ProgrammingError:
    pass
assert [r[0] for r in conn.execute("SELECT v FROM t")] == ["a", "b"] and not conn.in_transaction

# SQLite can roll back schema changes too (many databases cannot): DDL is transactional.
conn.execute("BEGIN")
conn.execute("CREATE TABLE draft (x)")
conn.execute("ROLLBACK")
assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'draft'").fetchone()[0] == 0
```

`BEGIN IMMEDIATE` matters when a method first *reads* ("does this event exist?") and then *writes*: with a plain deferred `BEGIN`, two processes can both read "no" and both write, or one fails with "database is locked" halfway. Taking the write lock first makes the read-then-write sequence atomic. Section 8 uses it.

Python 3.12 added a clearer way to ask for the same thing, the `autocommit` parameter. It is not used in the labs (the course baseline is 3.11), but you will meet it:

```python run
import sqlite3
import sys

if sys.version_info >= (3, 12):
    off = sqlite3.connect(":memory:", autocommit=False)        # a transaction is always open; commit() and rollback() start the next one
    assert off.autocommit is False and off.in_transaction
    on = sqlite3.connect(":memory:", autocommit=True)          # no implicit transactions; `with conn` no longer commits or rolls back
    assert on.autocommit is True and not on.in_transaction
    assert sqlite3.connect(":memory:").autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL     # the default is the legacy behaviour above
    for c in (off, on):
        c.close()
else:
    assert not hasattr(sqlite3.connect(":memory:"), "autocommit")
```

## 5. Constraints: the second line of defence (LO3)

Validation in Python is the first line. The database is the last one, and the only one that every program writing to the file must pass. Declare what is true and let SQLite refuse the rest:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE user (
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        age INTEGER CHECK (age BETWEEN 0 AND 150),
        role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'analyst', 'admin'))
    )
""")
conn.execute("INSERT INTO user (email, age) VALUES (?, ?)", ("a@example.org", 30))
refused = []
for sql, args in [
    ("INSERT INTO user (email) VALUES (?)", (None,)),                        # NOT NULL
    ("INSERT INTO user (email) VALUES (?)", ("a@example.org",)),              # UNIQUE
    ("INSERT INTO user (email, age) VALUES (?, ?)", ("b@example.org", 200)),   # CHECK
    ("INSERT INTO user (email, role) VALUES (?, ?)", ("c@example.org", "root")),
]:
    try:
        conn.execute(sql, args)
    except sqlite3.IntegrityError as exc:
        refused.append(str(exc))
assert len(refused) == 4 and "UNIQUE constraint failed: user.email" in refused[1]
assert conn.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 1
assert conn.execute("SELECT role FROM user").fetchone()[0] == "viewer"      # the default applied
```

`sqlite3.IntegrityError` is the one exception type for all of them; the message tells them apart. A repository (section 6) catches it where the *meaning* is known ("this email is taken") and raises its own error.

### Foreign keys are off until you turn them on

This is the single most surprising default of SQLite: **foreign key constraints are declared but not enforced** unless each connection asks for it, and the request is silently ignored once a transaction has started.

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 0              # off by default, for every new connection
conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
conn.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id) ON DELETE CASCADE)")
conn.execute("INSERT INTO child (parent_id) VALUES (999)")                 # an orphan: accepted, and now a transaction is open
conn.execute("PRAGMA foreign_keys = ON")                                   # ignored inside a transaction
assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 0
conn.rollback()

conn.execute("PRAGMA foreign_keys = ON")                                   # the first statement after connecting: it works
assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
try:
    conn.execute("INSERT INTO child (parent_id) VALUES (999)")
except sqlite3.IntegrityError as exc:
    assert "FOREIGN KEY" in str(exc)
conn.execute("INSERT INTO parent (id) VALUES (1)")
conn.execute("INSERT INTO child (parent_id) VALUES (1)")
conn.execute("DELETE FROM parent WHERE id = 1")                            # ON DELETE CASCADE removes the child
assert conn.execute("SELECT COUNT(*) FROM child").fetchone()[0] == 0
```

So the connection function of every program that declares a foreign key sets `PRAGMA foreign_keys = ON` as its **first** statement, and checks that it took effect (the guided lab's step 1 and step 6 do exactly that).

### `STRICT` tables

By default an `INTEGER` column accepts the text `'abc'` (section 2). A `STRICT` table (SQLite 3.37 and later; the interpreters used here bundle 3.45 or 3.53) enforces the declared types:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
if sqlite3.sqlite_version_info >= (3, 37):
    conn.execute("CREATE TABLE strict_t (i INTEGER, s TEXT) STRICT")
    try:
        conn.execute("INSERT INTO strict_t VALUES (?, ?)", ("abc", "x"))
    except sqlite3.IntegrityError as exc:
        assert "INTEGER" in str(exc)
    else:
        raise AssertionError("a STRICT table should refuse text in an INTEGER column")
    conn.execute("INSERT INTO strict_t VALUES (?, ?)", ("12", "x"))        # text that is a whole number is still converted
    assert conn.execute("SELECT typeof(i) FROM strict_t").fetchone()[0] == "integer"
```

The labs do not use `STRICT` because a learner's machine may bundle an older SQLite; check `sqlite3.sqlite_version` before relying on a feature.

## 6. A repository layer (LO3)

A **repository** is the one place in a program that knows SQL. Callers ask for things in the program's own terms (`add(note)`, `find_by_author("alice")`) and receive values the program defines (dataclasses, its own exceptions). Three rules keep it honest:

1. **All SQL lives in the repository**, every value is a parameter, and the only text placed into a statement is a fixed fragment.
2. **The repository does not commit and does not close.** The caller (a *unit of work*) owns the transaction, so one business action that touches several repositories is one transaction.
3. **Database errors become program errors** at the place where their meaning is known.

```python module=notes
import sqlite3
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE note (
    id INTEGER PRIMARY KEY,
    author TEXT NOT NULL CHECK (length(author) BETWEEN 1 AND 50),
    title TEXT NOT NULL UNIQUE,
    text TEXT NOT NULL
)
"""


class NoteNotFound(LookupError):
    pass


class DuplicateTitle(ValueError):
    pass


@dataclass(frozen=True)
class Note:
    id: int | None
    author: str
    title: str
    text: str


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")          # first, before any transaction
    conn.row_factory = sqlite3.Row
    return conn


class NoteRepo:
    """All SQL for notes. It never commits and never closes: the caller owns the transaction."""

    def __init__(self, conn):
        self._conn = conn

    def add(self, note: Note) -> Note:
        try:
            cur = self._conn.execute("INSERT INTO note (author, title, text) VALUES (?, ?, ?)", (note.author, note.title, note.text))
        except sqlite3.IntegrityError as exc:
            if "note.title" in str(exc):
                raise DuplicateTitle(note.title) from exc          # the meaning is known here
            raise
        return Note(cur.lastrowid, note.author, note.title, note.text)

    def get(self, note_id: int) -> Note:
        row = self._conn.execute("SELECT id, author, title, text FROM note WHERE id = ?", (note_id,)).fetchone()
        if row is None:
            raise NoteNotFound(note_id)
        return Note(**row)

    def by_author(self, author: str) -> list[Note]:
        rows = self._conn.execute("SELECT id, author, title, text FROM note WHERE author = ? ORDER BY id", (author,)).fetchall()
        return [Note(**r) for r in rows]
```

The tests need no files and no mocks: an in-memory database is a real database. They check the contract (round trip, errors), the transaction behaviour (nothing commits behind the caller's back) and hostile input:

```python test
import sqlite3

import pytest
from notes import SCHEMA, DuplicateTitle, Note, NoteNotFound, NoteRepo, connect


@pytest.fixture
def conn():
    c = connect()
    c.execute(SCHEMA)
    yield c
    c.close()


def test_round_trip_and_lookup(conn):
    repo = NoteRepo(conn)
    saved = repo.add(Note(None, "alice", "First", "hello"))
    assert saved.id == 1 and repo.get(1) == saved and repo.by_author("alice") == [saved] and repo.by_author("bob") == []


def test_unknown_id_is_the_programs_error_not_a_none_or_a_database_error(conn):
    with pytest.raises(NoteNotFound):
        NoteRepo(conn).get(404)


def test_a_duplicate_title_becomes_the_domain_error_and_other_integrity_errors_pass_through(conn):
    repo = NoteRepo(conn)
    repo.add(Note(None, "alice", "Same", "x"))
    with pytest.raises(DuplicateTitle):
        repo.add(Note(None, "bob", "Same", "y"))
    with pytest.raises(sqlite3.IntegrityError):                   # an empty author breaks the CHECK, not the title rule
        repo.add(Note(None, "", "Other", "z"))


def test_the_repository_leaves_the_transaction_to_the_caller(conn):
    repo = NoteRepo(conn)
    conn.commit()
    repo.add(Note(None, "alice", "Draft", "x"))
    assert conn.in_transaction
    conn.rollback()
    assert repo.by_author("alice") == []                           # the caller decided; nothing was committed behind its back


@pytest.mark.parametrize("hostile", ["' OR '1'='1", "x'; DROP TABLE note; --", "alice' UNION SELECT 1, 'a', 'b', 'c' --"])
def test_hostile_text_is_data_in_every_parameter(conn, hostile):
    repo = NoteRepo(conn)
    saved = repo.add(Note(None, "alice", hostile[:60], hostile))
    assert repo.get(saved.id).text == hostile
    assert repo.by_author(hostile[:50]) == []
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'note'").fetchone()[0] == 1
```

A **unit of work** puts the transaction around the repositories. It is the context manager of PY-M13 applied to a connection: enter opens, a clean exit commits, any exception rolls back, and the connection is closed on every path. The guided lab's step 3 and step 7 are its two essential cases (one write, and a batch).

## 7. Schema migrations (LO4)

The first version of a schema is easy. The second is the problem: the program is in use, the file exists, and the new code expects a column that is not there. `db.create_all()` (handbook page 236) and `CREATE TABLE IF NOT EXISTS` (page 154) create what is missing and **never change what exists**, so they are not a migration strategy.

A **migration** is a numbered change that is applied once, in order, to every database that has not seen it. The number of the last one applied is stored *in the database file itself*, in the `user_version` pragma, so the file always says what it contains.

### The naive version, and how it fails

```python run
import sqlite3

MIGRATIONS = [
    "CREATE TABLE event (id INTEGER PRIMARY KEY, kind TEXT NOT NULL);",
    "ALTER TABLE event ADD COLUMN source TEXT; UPDATE event SET source = 'unknown'; THIS IS NOT SQL;",      # a typo in migration 2
]


def naive_migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        conn.executescript(script)                          # executescript commits as it goes
        conn.execute(f"PRAGMA user_version = {number}")


conn = sqlite3.connect(":memory:")
try:
    naive_migrate(conn)
except sqlite3.OperationalError:
    pass
columns = [r[1] for r in conn.execute("PRAGMA table_info(event)")]
version = conn.execute("PRAGMA user_version").fetchone()[0]
assert version == 1 and columns == ["id", "kind", "source"], (version, columns)      # version says 1, but the column of migration 2 already exists
```

The database is now in a state that matches **no version**: it says version 1, but half of migration 2 was applied and committed. Running the fixed migration 2 later fails with "duplicate column name". This is the usual way a production database gets wedged.

### The rule: one transaction per migration, with the version bump inside it

```python run
import sqlite3

conn = sqlite3.connect(":memory:", isolation_level=None)                     # autocommit: the transactions below are ours


def apply(conn, statements, new_version):
    conn.execute("BEGIN IMMEDIATE")
    try:
        for statement in statements:                                          # single statements, run one by one (not executescript)
            conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {new_version}")                  # an int the program computed: PRAGMA cannot take a parameter
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


apply(conn, ["CREATE TABLE event (id INTEGER PRIMARY KEY, kind TEXT NOT NULL)"], 1)
try:
    apply(conn, ["ALTER TABLE event ADD COLUMN source TEXT", "THIS IS NOT SQL"], 2)
except sqlite3.OperationalError:
    pass
assert [r[1] for r in conn.execute("PRAGMA table_info(event)")] == ["id", "kind"]       # the half that worked was rolled back with the rest
assert conn.execute("PRAGMA user_version").fetchone()[0] == 1                           # and the version still tells the truth
apply(conn, ["ALTER TABLE event ADD COLUMN source TEXT"], 2)                             # the corrected migration applies cleanly
assert [r[1] for r in conn.execute("PRAGMA table_info(event)")] == ["id", "kind", "source"]
```

Around this core, a complete runner has to decide five more things, and the guided lab's step 6 asks you to implement each of them:

1. **Read the version after the lock is taken**, not before: two processes starting together must not both apply migration 3.
2. **A database newer than the program** (`user_version` greater than the number of migrations you know) must be refused and left untouched. Downgrading by guessing destroys data.
3. **Do nothing, quickly, when up to date** — and leave no transaction open when doing nothing.
4. **Adopt a database that has no version.** The first release created its tables with `CREATE TABLE IF NOT EXISTS` and never stored a version, so its file says `0` and already has tables. If migration 1 is written with `IF NOT EXISTS`, the runner "applies" it harmlessly and the file is brought under version control without being rebuilt.
5. **Never edit a migration that has been released.** Databases in the field have already applied the old text. Fix forward with a new number.

### Changing a column or adding a constraint: rebuild the table

`ALTER TABLE` can add a column and rename things. It cannot add a `CHECK`, a `UNIQUE` or a `FOREIGN KEY` to an existing table. SQLite's documented procedure is to **build the new table, copy, drop the old one, rename the new one**, all inside one transaction:

```python run
import sqlite3

conn = sqlite3.connect(":memory:", isolation_level=None)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript("""
    CREATE TABLE author (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE post (id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, title TEXT NOT NULL);   -- version 1: no foreign key, no checks
    INSERT INTO author VALUES (1, 'alice');
    INSERT INTO post VALUES (1, 1, 'kept'), (2, 99, 'orphan: nobody wrote it');
""")

conn.execute("BEGIN IMMEDIATE")
conn.execute("""CREATE TABLE post_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL REFERENCES author(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 100)
)""")
orphans = conn.execute("SELECT COUNT(*) FROM post WHERE author_id NOT IN (SELECT id FROM author)").fetchone()[0]
conn.execute("INSERT INTO post_new (id, author_id, title) SELECT id, author_id, title FROM post WHERE author_id IN (SELECT id FROM author)")
conn.execute("DROP TABLE post")
conn.execute("ALTER TABLE post_new RENAME TO post")
conn.execute("COMMIT")

assert orphans == 1                                                                   # the old table never enforced its relationship, so it holds rows that cannot be carried over
assert conn.execute("SELECT id, title FROM post").fetchall() == [(1, "kept")]
fk = conn.execute("PRAGMA foreign_key_list(post)").fetchall()
assert len(fk) == 1 and fk[0][2] == "author" and fk[0][6] == "CASCADE"
conn.execute("DELETE FROM author WHERE id = 1")
assert conn.execute("SELECT COUNT(*) FROM post").fetchone()[0] == 0                   # the new guarantee works
conn.execute("INSERT INTO author VALUES (2, 'bob')")
conn.execute("INSERT INTO post (author_id, title) VALUES (2, 'next')")
assert conn.execute("SELECT id FROM post").fetchone()[0] == 2                         # post 1 was deleted; AUTOINCREMENT does not hand its id out again
```

Two decisions in that block are the ones an upgrade needs to make **on purpose**: what to do with rows that break the new rule (here they are counted, then not copied; the independent lab asks for exactly this), and whether ids may be reused. `INTEGER PRIMARY KEY` alone hands out `max(id) + 1`, so after the last row is deleted its id comes back; `AUTOINCREMENT` never reuses one. If other systems or humans refer to ids (a case number in an e-mail), reuse is a defect.

Real projects often use a migration tool (Alembic for SQLAlchemy, handbook pages 302 and 311). A tool automates the bookkeeping; it does not remove the decisions above, and it cannot know what to do with your orphans. This lesson teaches the mechanism so that the tool's output can be reviewed.

## 8. Retries, conflicts and concurrent edits (LO5)

Networks resend, schedulers run a job twice, two analysts open the same case. A write path that is only correct when nothing is repeated and nobody else is working is not correct.

### A retry is not a conflict

When the same request arrives twice, the second one must be recognised as **the same request** and do nothing. When the same *key* arrives with *different content*, that is not a retry; it is a conflict someone must hear about. SQLite offers three shortcuts, and two of them hide exactly this difference:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("CREATE TABLE ticket (ref TEXT PRIMARY KEY, title TEXT NOT NULL)")
conn.execute("CREATE TABLE note (id INTEGER PRIMARY KEY, ticket_ref TEXT NOT NULL REFERENCES ticket(ref) ON DELETE CASCADE, text TEXT)")
conn.execute("INSERT INTO ticket VALUES ('T-1', 'original')")
conn.execute("INSERT INTO note (ticket_ref, text) VALUES ('T-1', 'analyst comment')")
conn.commit()

try:
    conn.execute("INSERT INTO ticket VALUES ('T-1', 'original')")                  # a plain INSERT: a retry fails loudly ...
except sqlite3.IntegrityError:
    pass
conn.rollback()

# INSERT OR IGNORE: the retry is harmless, and rowcount says whether anything was written ...
assert conn.execute("INSERT OR IGNORE INTO ticket VALUES ('T-1', 'original')").rowcount == 0
assert conn.execute("INSERT OR IGNORE INTO ticket VALUES ('T-2', 'new')").rowcount == 1
# ... but it also swallows a CONFLICT: same key, different content, no error, and the caller thinks it succeeded.
assert conn.execute("INSERT OR IGNORE INTO ticket VALUES ('T-1', 'DIFFERENT')").rowcount == 0
assert conn.execute("SELECT title FROM ticket WHERE ref = 'T-1'").fetchone()[0] == "original"

# INSERT OR REPLACE is worse: it overwrites the original, and deleting the old row cascades to its children.
conn.execute("INSERT OR REPLACE INTO ticket VALUES ('T-1', 'DIFFERENT')")
assert conn.execute("SELECT title FROM ticket WHERE ref = 'T-1'").fetchone()[0] == "DIFFERENT"
assert conn.execute("SELECT COUNT(*) FROM note").fetchone()[0] == 0                # the analyst's comment disappeared with it
```

For an append-only history (events, audit records) `OR REPLACE` rewrites the past and `OR IGNORE` hides disagreement. The reliable shape is *decide inside one write-locked transaction*:

```python run
import sqlite3


class Conflict(ValueError):
    pass


def record(conn, ref, title):
    """True if stored now, False if it was already stored identically, Conflict if the key exists with other content."""
    conn.execute("BEGIN IMMEDIATE")                                    # read and write under one lock: no other writer can slip in between
    try:
        row = conn.execute("SELECT title FROM ticket WHERE ref = ?", (ref,)).fetchone()
        if row is not None:
            if row[0] != title:
                raise Conflict(ref)
            conn.execute("COMMIT")
            return False
        conn.execute("INSERT INTO ticket VALUES (?, ?)", (ref, title))
        conn.execute("COMMIT")
        return True
    except BaseException:
        conn.execute("ROLLBACK")
        raise


conn = sqlite3.connect(":memory:", isolation_level=None)
conn.execute("CREATE TABLE ticket (ref TEXT PRIMARY KEY, title TEXT NOT NULL)")
assert record(conn, "T-1", "original") is True
assert record(conn, "T-1", "original") is False                         # a retry
try:
    record(conn, "T-1", "DIFFERENT")                                    # a conflict
except Conflict:
    pass
assert conn.execute("SELECT title FROM ticket").fetchall() == [("original",)] and not conn.in_transaction
```

Upsert (`INSERT ... ON CONFLICT(key) DO UPDATE ...`, SQLite 3.24 and later) is the right tool when "last write wins" is genuinely what you want, such as a counter or a heartbeat. It is the wrong tool when a difference needs a human.

### Two people edit the same record: optimistic concurrency

The lost update is silent: both read, both change, the second write overwrites the first, and nobody sees an error. **Optimistic concurrency** puts a version number on the row and makes the write conditional on it:

```python run
import os
import sqlite3
import tempfile

path = os.path.join(tempfile.mkdtemp(), "docs.db")
setup = sqlite3.connect(path, isolation_level=None)
setup.execute("CREATE TABLE doc (id INTEGER PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1)")
setup.execute("INSERT INTO doc (body) VALUES ('draft')")
setup.close()

alice = sqlite3.connect(path, isolation_level=None)
bob = sqlite3.connect(path, isolation_level=None)
alice.execute("SELECT body, version FROM doc WHERE id = 1").fetchone()          # both people open the same version
bob.execute("SELECT body, version FROM doc WHERE id = 1").fetchone()

# Without a guard the second write wins and the first vanishes without an error.
alice.execute("UPDATE doc SET body = ? WHERE id = 1", ("alice's edit",))
bob.execute("UPDATE doc SET body = ? WHERE id = 1", ("bob's edit",))
assert alice.execute("SELECT body FROM doc").fetchone()[0] == "bob's edit"


def save(conn, body, expected_version):
    cur = conn.execute("UPDATE doc SET body = ?, version = version + 1 WHERE id = 1 AND version = ?", (body, expected_version))
    return cur.rowcount == 1                                                    # 0 rows matched: somebody changed it since you read it


assert save(alice, "alice v2", 1) is True                                       # the check and the write are ONE statement
assert save(bob, "bob v2", 1) is False                                          # bob is told; he must re-read and decide
assert alice.execute("SELECT body, version FROM doc").fetchone() == ("alice v2", 2)
alice.close()
bob.close()
```

The guard works because the condition and the change are one atomic statement. Reading the version in Python and then updating it in a second statement would reopen the gap. When `rowcount` is 0 you still have to say *why*: the row is gone (not found) or its version moved (stale). That second question is asked inside the same transaction. The independent lab builds this for a whole case tracker.

## 9. The shape of a query (LO5)

A query that is correct on ten rows can be unusable on a million. Three measurements catch most problems, and none needs a stopwatch.

### How many statements?

The N+1 pattern is the classic: one query for the list, then one more per item. It is invisible in small tests and fatal under load. Count the statements SQLite actually runs with a **trace callback**:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript("""
    CREATE TABLE author (id INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE post (id INTEGER PRIMARY KEY, author_id INTEGER, title TEXT);
""")
conn.executemany("INSERT INTO author (name) VALUES (?)", [(f"author{i}",) for i in range(20)])
conn.executemany("INSERT INTO post (author_id, title) VALUES (?, ?)", [(1 + i % 20, f"post{i}") for i in range(100)])

statements = []
conn.set_trace_callback(statements.append)


def selects():
    return [s for s in statements if s.lstrip().upper().startswith("SELECT")]


titles = []
for post_id, author_id, title in conn.execute("SELECT id, author_id, title FROM post").fetchall():
    name = conn.execute("SELECT name FROM author WHERE id = ?", (author_id,)).fetchone()[0]       # one query per post
    titles.append((title, name))
assert len(selects()) == 1 + 100

statements.clear()
joined = conn.execute("SELECT p.title, a.name FROM post p JOIN author a ON a.id = p.author_id").fetchall()
assert len(selects()) == 1 and sorted(joined) == sorted(titles)
```

A test that asserts "at most N SELECT statements for a page of 50 items" fails the moment someone writes the loop. The labs use exactly that test. (Object-relational mappers hide the loop behind attribute access; the same trace counts it.)

### Is an index used?

`EXPLAIN QUERY PLAN` shows how SQLite will run a statement. The wording changes between versions; the words **SEARCH** (uses an index or the primary key) and **SCAN** (reads the whole table) are stable:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE event (id INTEGER PRIMARY KEY, kind TEXT, at TEXT, message TEXT)")
conn.execute("CREATE INDEX idx_event_kind_at ON event (kind, at)")


def plan(sql, params=()):
    return " | ".join(str(row[3]) for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params))


assert "SEARCH" in plan("SELECT * FROM event WHERE kind = ?", ("login",)) and "idx_event_kind_at" in plan("SELECT * FROM event WHERE kind = ?", ("login",))
assert "TEMP B-TREE" not in plan("SELECT * FROM event WHERE kind = ? ORDER BY at", ("login",))        # the index also delivers the order
assert "SCAN" in plan("SELECT * FROM event WHERE lower(kind) = ?", ("login",))                           # a function around the column defeats the index
assert "SCAN" in plan("SELECT * FROM event WHERE message LIKE ?", ("%failed%",))                         # a leading % cannot use an index either
assert "SCAN" in plan("SELECT * FROM event WHERE at > ?", ("2026-01-01",))                               # the index starts with kind: `at` alone cannot use it
```

Two rules fall out of the plan: put the column you **compare** in the index and **compare the column itself** (not `lower(column)`); and an index on `(a, b)` serves queries on `a`, or on `a` and `b`, but not on `b` alone.

### How much work?

The plan says *whether* an index is used; to say *how much* work a call did, count the instructions SQLite ran. The count does not depend on the speed of the machine, so a test can compare it with a budget:

```python run
import sqlite3


def work(conn, sql, params=()):
    ticks = [0]

    def tick():
        ticks[0] += 1
        return 0

    conn.set_progress_handler(tick, 10)                     # called every 10 virtual-machine instructions
    conn.execute(sql, params).fetchall()
    conn.set_progress_handler(None, 10)
    return ticks[0] * 10


conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE event (id INTEGER PRIMARY KEY, kind TEXT, at TEXT)")
conn.executemany("INSERT INTO event (kind, at) VALUES (?, ?)", [(f"kind{i % 50}", f"2026-10-{1 + i % 28:02d}") for i in range(20_000)])
without_index = work(conn, "SELECT id FROM event WHERE kind = ?", ("kind7",))
conn.execute("CREATE INDEX idx_kind ON event (kind)")
with_index = work(conn, "SELECT id FROM event WHERE kind = ?", ("kind7",))
assert without_index > 10 * with_index, (without_index, with_index)
```

The independent lab's hidden tests use this to fail a `find` that reads every comment for every case.

### Paging: OFFSET shifts, keysets do not

`LIMIT n OFFSET m` means "skip m rows, then take n". When rows are added between two page requests, the skipped count refers to a different list:

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE item (id INTEGER PRIMARY KEY)")
conn.executemany("INSERT INTO item (id) VALUES (?)", [(i,) for i in range(1, 10)])      # 1..9, listed newest first

page1 = [r[0] for r in conn.execute("SELECT id FROM item ORDER BY id DESC LIMIT 3")]
assert page1 == [9, 8, 7]
conn.execute("INSERT INTO item (id) VALUES (10)")                                         # something arrives between the two requests

by_offset = [r[0] for r in conn.execute("SELECT id FROM item ORDER BY id DESC LIMIT 3 OFFSET 3")]
by_keyset = [r[0] for r in conn.execute("SELECT id FROM item WHERE id < ? ORDER BY id DESC LIMIT 3", (page1[-1],))]
assert by_offset == [7, 6, 5]                      # 7 appears on both pages
assert by_keyset == [6, 5, 4]                      # the next page starts after the last row the caller saw
```

**Keyset pagination** ("seek": `WHERE (sort_key, id) > (last_sort_key, last_id)`) needs a **deterministic order**: if two rows tie on the sort key, the order between them is up to the database, and a page boundary can fall between them. Always end the `ORDER BY` with a unique column, and say so in the query, not only in the index: an index happens to deliver the order today, and a dropped index or a changed plan removes it silently. The guided lab drops the index to prove its query does not depend on it.

## 10. Files, locks, backups and what a database file reveals (LO2, LO5)

### The file is data, and often sensitive data

SQLite creates a new file with the permissions the process's *umask* leaves, typically `0644`: readable by every user of the machine. A database of events, cases or credentials should be created `0600`. Create the file yourself first (an empty file is a valid new database):

```python run
import contextlib
import os
import sqlite3
import stat
import tempfile

folder = tempfile.mkdtemp()
shared, private = os.path.join(folder, "shared.db"), os.path.join(folder, "private.db")
old = os.umask(0o022)
try:
    with contextlib.closing(sqlite3.connect(shared)) as c:
        c.execute("CREATE TABLE t (x)")
    os.close(os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))        # O_EXCL: never follow or reuse something that appeared meanwhile
    with contextlib.closing(sqlite3.connect(private)) as c:
        c.execute("CREATE TABLE t (x)")
finally:
    os.umask(old)
if os.name == "posix":
    assert stat.S_IMODE(os.stat(shared).st_mode) == 0o644
    assert stat.S_IMODE(os.stat(private).st_mode) == 0o600
```

Backups and exports inherit the sensitivity. And **a log of SQL is a log of the data**: the trace callback shows each statement with its values filled in.

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE token (value TEXT)")
seen = []
conn.set_trace_callback(seen.append)
conn.execute("INSERT INTO token VALUES (?)", ("s3cret-token-value",))
assert any("s3cret-token-value" in statement for statement in seen)      # never enable statement logging with values in production
```

Passwords are never stored as they are; PY-M07 shows how to store a salted, slow hash instead.

### Locks, timeouts and WAL

SQLite allows many readers or **one** writer. A second writer waits up to `timeout` seconds (default 5) and then fails with `database is locked`:

```python run
import os
import sqlite3
import tempfile
import time

path = os.path.join(tempfile.mkdtemp(), "locks.db")
first = sqlite3.connect(path, isolation_level=None)
first.execute("CREATE TABLE t (x)")
first.execute("BEGIN IMMEDIATE")                                           # holds the write lock

second = sqlite3.connect(path, timeout=0.2, isolation_level=None)
started = time.monotonic()
try:
    second.execute("BEGIN IMMEDIATE")
except sqlite3.OperationalError as exc:
    assert "locked" in str(exc)
else:
    raise AssertionError("the second writer should have been refused")
assert time.monotonic() - started >= 0.15                                  # it waited for the timeout first

first.execute("ROLLBACK")
second.execute("BEGIN IMMEDIATE")                                          # now it can
second.execute("ROLLBACK")

# Write-ahead logging lets readers keep reading while a writer works. It is a property of the file.
assert second.execute("PRAGMA journal_mode = wal").fetchone()[0] == "wal"
second.execute("INSERT INTO t VALUES (1)")
assert os.path.exists(path + "-wal")
first.close()
second.close()
```

Keep write transactions short, set a timeout, and treat `database is locked` as an expected condition that callers handle (retry with a limit, or report). WAL needs shared memory and does not work reliably on network file systems.

### Read-only access, backups and threads

```python run
import os
import pathlib
import sqlite3
import tempfile
import threading

path = os.path.join(tempfile.mkdtemp(), "data.db")
conn = sqlite3.connect(path)
conn.execute("CREATE TABLE t (x)")
conn.execute("INSERT INTO t VALUES (1)")
conn.commit()

# A reporting job should not be able to change the data: open it read-only.
reader = sqlite3.connect(pathlib.Path(path).as_uri() + "?mode=ro", uri=True)
try:
    reader.execute("INSERT INTO t VALUES (2)")
except sqlite3.OperationalError as exc:
    assert "readonly" in str(exc)
reader.close()

# A consistent online copy, even while the file is in use.
copy = sqlite3.connect(":memory:")
conn.backup(copy)
assert copy.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
copy.close()

# A connection belongs to the thread that made it.
errors = []


def use_from_another_thread():
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError as exc:
        errors.append(exc)


worker = threading.Thread(target=use_from_another_thread)
worker.start()
worker.join()
assert len(errors) == 1
conn.close()
```

One connection per thread (or a pool owned by a framework) is the safe model.

### When SQLite is the wrong tool

SQLite is excellent for a tool, a test, a desktop program or a small service that one process owns. Move to a server database (PostgreSQL is the usual choice) when **several machines** must write, when many writers contend, when you need per-user database permissions, or when the file would live on a network share. The habits in this module carry over unchanged: bound parameters (the placeholder is `%s` in psycopg), explicit transactions, constraints, versioned migrations, query plans. What changes is the driver, the locking model and the operations around it. Object-relational mappers such as SQLAlchemy bind parameters for you and generate N+1 patterns just as easily; their raw-SQL escape hatches (`text()`) are injectable if you format into them. None of that is executed here: the course uses only what ships with Python.

## 11. What differs between Python versions (executed)

Every row was produced by running the same code on CPython 3.11, 3.12, 3.13, 3.14 and 3.15 (R-098) and is asserted again by this lesson on whichever interpreter runs it.

| Behaviour | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|---|
| `connect(..., autocommit=...)` and `Connection.autocommit` | no | yes | yes | yes | yes |
| default `date` / `datetime` adapters emit `DeprecationWarning` | no | yes | yes | yes | yes |
| an unclosed connection emits `ResourceWarning` when collected | no | no | yes | yes | yes |
| `execute()` refuses two statements (`ProgrammingError`) | yes | yes | yes | yes | yes |
| foreign keys off by default; `PRAGMA foreign_keys` ignored inside a transaction | yes | yes | yes | yes | yes |

```python run
import sqlite3
import sys
import warnings

v = sys.version_info[:2]
conn = sqlite3.connect(":memory:")
assert hasattr(conn, "autocommit") == (v >= (3, 12))
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    conn.execute("CREATE TABLE d (x TEXT)")
    import datetime
    conn.execute("INSERT INTO d VALUES (?)", (datetime.datetime(2026, 10, 15),))
assert (DeprecationWarning in {w.category for w in caught}) == (v >= (3, 12))
assert sqlite3.sqlite_version_info >= (3, 35)              # the labs rely on nothing newer
conn.close()
```

The library behind the module is a separate version: `sqlite3.sqlite_version` was 3.45.1 on the 3.11 to 3.13 interpreters and 3.53.1 on the 3.14 and 3.15 interpreters used here, because it depends on how the interpreter was built. Check it before using a newer feature (`STRICT` needs 3.37, `RETURNING` 3.35, upsert 3.24).

## 12. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 141 to 142 | MySQL, PostgreSQL and MongoDB connection snippets; user `root` with a password in the source; no `close()` | sections 3 and 4: parameters and lifecycle; section 10: secrets and when a server database is the right tool; the server drivers themselves are not executed (no server in the course) |
| 148 to 150 | architecture sketch: a storage layer "(MongoDB / SQL)" and a `storage/sqlite.py` | sections 6 and 7: the repository layer and the schema it needs to grow |
| 154 to 155 | `save_event`: parameterised `INSERT`, `CREATE TABLE IF NOT EXISTS` and a connection per event | sections 3, 4 and 8; guided lab part 1 (idempotent, transactional append) |
| 155 to 156 | the report query and a file written from `fetchall()` | section 9 (statement counts, plans); guided lab step 8 (`count_by_type`) |
| 172 to 174, 181 to 182 | document-store (MongoDB) examples | not covered: outside the relational ideas of this module; the principles of sections 3, 8 and 10 apply |
| 234 to 241 | Flask-SQLAlchemy models, `db.create_all()`, a `SECRET_KEY` in `config.py` | section 7 (why `create_all()` is not a migration path); the web layer and secrets are PY-M10 and PY-M07 |
| 108, 176, 231, 243, 373, 395 | pages that the page mapper assigned here by keyword: an automation introduction, an indicator schema, Flask forms, a shell-command f-string, an offensive-security loader and fuzzer | not carried here: see the source map for where each belongs (the shell-command mistake is named in section 3 and taught in PY-M07) |
| 302 and 311 | "multi-tenant migrations with Alembic" | section 7: the mechanism a migration tool automates, and the decisions it cannot make |

## 13. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| building SQL with an f-string or `%` | `' OR '1'='1` returns every row; a `UNION` returns another table | placeholders for every value; an allow-list for names |
| `ORDER BY ?` | no error, no sorting | pick the column name from a dictionary you wrote |
| `LIKE` with user text | `%` and `_` act as wildcards | escape them and add `ESCAPE` |
| assuming `with conn` closes the connection | leaked connections, `ResourceWarning` on 3.13+ | `contextlib.closing`, or a unit of work that closes |
| `executescript()` for migrations | a failed migration leaves half of itself applied | one transaction per migration, single statements, the version bump inside |
| foreign keys "declared" but not enabled | orphans, cascades that never run | `PRAGMA foreign_keys = ON` first, then verify it |
| `INSERT OR REPLACE` / `OR IGNORE` for retries | silent overwrite and cascade, or a hidden conflict | decide inside a `BEGIN IMMEDIATE` transaction |
| read the row, change it in Python, write it back | the lost update | a version column and `UPDATE ... WHERE version = ?` |
| a query per item in a loop | works on ten rows, collapses on a thousand | a join or one `IN (...)` query; assert the statement count in a test |
| `OFFSET` paging on a changing table | repeated or skipped rows | keyset paging with a unique tie-breaker |
| a world-readable database file | any local user can read the data | create it `0600` yourself |
| SQL logging with values | secrets in the logs | log statement text and a hash, never the bound values |

## 14. Check yourself

1. Why does `find_safe("pen' UNION SELECT name, pw FROM users --")` return nothing while the f-string version returns the passwords?
2. A teammate writes `conn.execute("SELECT * FROM events ORDER BY ?", (column,))`. What happens, and what is the fix?
3. `with conn:` raises inside the block. What is rolled back, and is the connection still usable afterwards?
4. A migration runner uses `executescript()` and the second statement fails. What state is the database in, and what does `user_version` say?
5. Two analysts open version 3 of the same case. The first saves. What does the second save return in your design, and which single SQL fact tells you?

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 15. Sources and verification trail

- Every assertion in this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 (R-098; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). Reference documentation: the `sqlite3` module <https://docs.python.org/3/library/sqlite3.html> (placeholders, transaction control, the adapter deprecation and the `autocommit` parameter), SQLite's own documents on foreign keys, `ALTER TABLE` and the table-rebuild procedure, `EXPLAIN QUERY PLAN`, write-ahead logging and the conflict clause <https://www.sqlite.org/docs.html> (R-005 for the Python versions).
- Handbook corrections: finding F-PYH-013 (a connection and a table-creation statement per event and a connection closed only on success, a report that never closes its connection, server-database snippets with a literal password and no `close()`, `create_all()` presented as schema management).
- Not verified here and therefore not claimed: behaviour of PostgreSQL, MySQL or any document store; SQLAlchemy, Alembic and psycopg (not part of the course dependencies); behaviour of SQLite on Windows file systems (the file-mode check is skipped there) or on network shares; performance numbers (the lesson counts statements and virtual-machine instructions and never claims seconds).
