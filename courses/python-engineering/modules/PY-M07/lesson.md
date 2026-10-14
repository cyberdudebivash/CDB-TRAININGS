---
id: PY-M07
title: "Secure coding for Python"
course: COURSE-PY-ENG
level: 2
audience: "Developers and operations staff who write Python that handles input from users, files, networks or other programs"
prerequisites:
  - "PY-M02 (tests with pytest); PY-M01 (language core)"
  - "Python 3.11 or newer; the packages in labs/requirements.txt (pytest, PyYAML, PyJWT, ruff)"
  - "All attacks in this module are harmless probes against code in this repository. Never run an exploit against a system you do not own or have written authorisation to test."
estimated_time_hours: {lesson: 2.0, guided_lab: 3.0, independent_lab: 3.0, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "supported 3.11-3.15 (R-005)", pyyaml: "6.0.3 (executed)", pyjwt: "2.15.1 (executed)", ruff: "0.17.0 (executed, rules S307 S608 S602 S301 S506 S323 S324)", owasp: "Top 10:2025 (R-035) and LLM Top 10 2025 (R-028), official page summaries"}
last_verified: 2026-10-14
---

# PY-M07 - Secure coding for Python

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Explain why untrusted text must be treated as data and never as code, SQL or a shell command, for five injection patterns. |
| **LO2** | Replace `eval`, string-built SQL and `shell=True` with a safe alternative that keeps the behaviour. |
| **LO3** | Make file access, deserialisation and TLS safe: stay inside a folder, parse data without executing it, verify certificates. |
| **LO4** | Store passwords and compare secrets safely, and keep secrets out of source code and logs. |
| **LO5** | Write a regression test for each fixed vulnerability that fails if the vulnerability is reintroduced, and say what static analysis can and cannot find. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Most Python vulnerabilities are not exotic. They are a few patterns repeated: text from outside becomes code (`eval`, SQL, a shell command), a parser is allowed to build arbitrary objects
(`pickle`, an unsafe YAML loader), a path or a certificate is trusted without checking, a secret is written into source or a log.

The 2025 handbook this module replaces teaches several of them as normal practice, with no warning. An audit of its listings found, among others: a tool for an AI agent that runs `eval(expr)` on model-controlled text
(F-PYH-001, page 585) and automation examples with plaintext passwords (p. 163), an SSH client that accepts any host key (p. 164), `verify=False` for API calls (p. 428), a hard-coded JWT signing secret (p. 269),
a hard-coded admin password (p. 252), `os.system` with an f-string (pp. 122, 373) and Flask's `debug=True` (pp. 222, 228) (F-PYH-002). For an AI-security brand these are the lessons most worth replacing.

> **Safety.** The labs use harmless probes: a function that creates an empty directory, a shell command that only runs `echo`, an in-memory database. Do not adapt them to attack anything real.

## 2. The one idea: data is not code (LO1)

An *injection* flaw has one shape: a program builds a string that another interpreter will parse (Python's evaluator, a SQL engine, a shell), and some of the text came from someone else.
The attacker's text changes the *structure* of the command instead of being a *value* inside it. The fix is always to keep the two channels separate: pass values as values.

| Interpreter | Vulnerable pattern | Safe pattern |
|---|---|---|
| Python evaluator | `eval(text)` | Parse to a syntax tree and allow only the node types you intend (or `ast.literal_eval` for literals) |
| SQL engine | `f"... WHERE name = '{name}'"` | `conn.execute("... WHERE name = ?", (name,))` - the driver sends the value separately |
| Shell | `subprocess.run(f"ls {path}", shell=True)` | No shell at all (`os.listdir`) or an argument list: `subprocess.run(["ls", "--", path])` |
| File system | `open(base + "/" + name)` | Resolve the path and check it is inside `base` |
| Parser | `pickle.loads(blob)`, `yaml.load(text, Loader=yaml.Loader)` | Data formats that cannot describe code: `json.loads`, `yaml.safe_load`, then validate |

OWASP's *Top 10:2025* lists Injection as category A05 and Software or Data Integrity Failures as A08 (R-035). For LLM applications, the *LLM Top 10 2025* adds Improper Output Handling (LLM05) and Excessive Agency (LLM06) (R-028):
an agent tool that `eval`s what a model produced turns a prompt-injection into code execution.

```python run
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE users (name TEXT, role TEXT)")
db.executemany("INSERT INTO users VALUES (?, ?)", [("ada", "agent"), ("grace", "admin")])

name = "x' OR '1'='1"                                                         # attacker-controlled
unsafe = db.execute(f"SELECT name FROM users WHERE name = '{name}'").fetchall()       # structure changed: every row returned
safe = db.execute("SELECT name FROM users WHERE name = ?", (name,)).fetchall()        # the text is just a (non-matching) name
assert len(unsafe) == 2 and safe == []
assert db.execute("SELECT name FROM users WHERE name = ?", ("O'Brien",)).fetchall() == []   # an apostrophe is harmless as a value
```

Note the side benefit: the f-string version also *breaks on honest input* (`O'Brien` is a syntax error). Correct code and secure code are usually the same code.

## 3. Replacing eval (LO2)

`eval` runs anything. "Sanitising" the string is a losing game; the robust answer is to parse and accept only a small grammar. Python's `ast` module gives you the tree:

```python run
import ast

ALLOWED_BINARY = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b}


def calc(text: str):
    tree = ast.parse(text, mode="eval")

    def walk(node):
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BINARY:
            return ALLOWED_BINARY[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        raise ValueError("not allowed")                      # everything else: names, calls, attributes, strings...

    return walk(tree.body)


assert calc("1 + 2 * 3") == 7
for hostile in ("__import__('os').getpid()", "(1).__class__", "open('x')"):
    try:
        calc(hostile)
    except ValueError:
        pass
    else:
        raise AssertionError(hostile)
```

An allow-list fails closed: a node type you did not think of is rejected. A deny-list ("no `import`") fails open. The lab version also bounds the input length and the exponent, because `9 ** 9 ** 9` is not code execution but it is a denial of service.

## 4. Shells, paths and parsers (LO3)

**Shells.** `shell=True` hands the whole string to `/bin/sh`, which treats `;`, `&&`, `$()` and backticks as syntax. The best fix is to avoid the shell: most tasks have a library call (`os.listdir`, `shutil`, `zipfile`).
If you must run a program, pass a list and put `--` before user-supplied arguments so one starting with `-` cannot be read as an option.

**Paths.** Joining a base folder and a user-supplied name does not confine the result: `../` climbs out, an absolute path replaces the base, and a symbolic link inside the folder can point anywhere. Resolve first, then check:

```python run
import tempfile
from pathlib import Path


def read_inside(base: Path, name: str) -> bytes:
    base = base.resolve()
    target = (base / name).resolve()                 # resolves .., absolute paths and symbolic links
    if not target.is_relative_to(base) or target == base:
        raise ValueError("invalid attachment name")
    return target.read_bytes()


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "files").mkdir()
    (root / "files" / "ok.txt").write_bytes(b"hello")
    (root / "secret.txt").write_bytes(b"s")
    assert read_inside(root / "files", "ok.txt") == b"hello"
    for hostile in ("../secret.txt", str(root / "secret.txt"), ".."):
        try:
            read_inside(root / "files", hostile)
        except ValueError:
            pass
        else:
            raise AssertionError(hostile)
```

A "block the string `..`" filter looks similar and is wrong: it lets absolute paths and symbolic links through (the lab includes that as a mutant so you can watch your tests catch it).

**Parsers.** `pickle` is a program, not a data format: loading it can call any function. YAML's full loader can build arbitrary Python objects from tags such as `!!python/object/apply:`. Use formats that cannot describe code (`json`, `yaml.safe_load`) and then **validate the result**.
Validation after an unsafe parse is too late: the damage happens *during* parsing, so the labs' tests look for a side effect (a directory being created) and not only for an exception.
On PyYAML 6.0.3, `yaml.load(text)` without a `Loader` raises `TypeError` (executed probe `pyyaml-unsafe-load`), but `yaml.load(text, Loader=yaml.Loader)` is still unsafe: the old safety net is gone, the dangerous option remains.

**TLS.** `ssl.create_default_context()` verifies certificates and host names. Contexts built with `ssl._create_unverified_context()` or `requests.get(..., verify=False)` accept any certificate, so anyone on the network path can impersonate the server.

## 5. Secrets, passwords and tokens (LO4)

- **Never store a password you can read back.** Store a salted, deliberately slow hash. The lab uses `hashlib.scrypt` (a memory-hard key-derivation function in the standard library; it needs a Python built with an OpenSSL that provides scrypt, which the lab checks by running it) with a fresh random salt per password; unsalted MD5 means equal passwords have equal hashes, and a fast hash lets an attacker test a very large list of guesses cheaply.
- **Compare secrets in constant time**: `hmac.compare_digest(a, b)`, not `==`, which stops at the first differing byte.
- **Keep secrets out of source and logs.** Read them from the environment or a secret store, fail closed when missing, and never log them. A "default" secret in source is a published secret.
- **Verify tokens fully.** PyJWT 2.15.1 refuses `jwt.decode(token, key)` without an `algorithms` list (it raises `DecodeError`, executed probe `pyjwt-decode-algorithms`), and `options={"verify_signature": False}` switches verification off entirely: it is a debugging tool, never a production setting. Always pin the algorithm, require `exp`, and use a key of at least the recommended length (PyJWT warns about shorter HMAC keys).
- **Host keys.** An SSH client that auto-accepts unknown host keys (`paramiko.AutoAddPolicy`) is open to impersonation. paramiko 5.0.0 still ships both `AutoAddPolicy` and `RejectPolicy` (executed probe `paramiko-host-key-policy`); choose the rejecting policy and load known hosts.

## 6. Regression tests and what static analysis finds (LO5)

Fixing a vulnerability without a test invites its return. A **regression test** attacks the code with the exact input that used to work, and you prove it is worth having the same way as in PY-M02: reintroduce the vulnerability and watch the test fail.
Test the *effect*, not just the error: for deserialisation, check that the payload had no side effect; for injection, check that the injected command did not run.

Static analysis helps and has limits. Ruff 0.17.0 with `--select S` (its flake8-bandit rules) flagged eight places in the lab's vulnerable starter - `eval` (S307), string-built SQL (S608), `shell=True` (S602), `pickle` (S301), the unsafe YAML loader (S506),
the unverified TLS context (S323) and MD5 twice (S324) - and **did not flag the path-traversal bug** (executed in this module's checks). A clean linter run means the patterns it knows are absent, not that the code is safe.

## 7. What changed since the 2025 handbook

Verified on 2026-10-14:

| 2025 handbook | Now |
|---|---|
| `eval(expr)` in an agent "math tool" (p. 585), "this is how ChatGPT agents run" | LLM05 Improper Output Handling and LLM06 Excessive Agency are on OWASP's 2025 LLM list (R-028); use an allow-list parser. |
| Plaintext passwords in inventory files, hard-coded signing secrets (pp. 163, 252, 269) | Secrets from the environment or a store; salted slow hashes; fail closed when missing. |
| `AutoAddPolicy()` in SSH automation (p. 164) | Reject unknown host keys (paramiko 5.0.0 still has both policies, executed). |
| `requests` with `verify=False` (p. 428) | Verify certificates; fix trust-store problems instead of disabling checks. |
| `os.system(f"...{ip}...")` (pp. 122, 373) | No shell, or an argument list with `--`. |
| `yaml.load(f)` | PyYAML 6.0.3 requires a `Loader` (executed); use `yaml.safe_load`. |
| `jwt.decode(token, key)` | PyJWT 2.15.1 requires `algorithms=[...]` (executed); never disable signature verification. |
| No mention of OWASP lists | OWASP Top 10:2025 (R-035) and LLM Top 10 2025 (R-028) are the shared vocabulary. |

## 8. Common misconceptions

| Misconception | Reality |
|---|---|
| "I'll just strip the dangerous characters." | Deny-lists fail open. Separate data from structure (parameters, argument lists, parsers that cannot run code). |
| "Validating the result makes `pickle.loads` safe." | The code runs while loading. Validation afterwards cannot undo it. |
| "My internal tool does not need this." | Internal tools run with internal privileges: they are the better target. |
| "A clean linter run means secure." | It means the known patterns are absent. The path-traversal bug passed. |
| "MD5/SHA-256 is fine for passwords if I add a salt." | Fast hashes are cheap to brute-force. Use a deliberately slow, memory-hard function (scrypt, Argon2, bcrypt). |

## 9. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Fix eight seeded vulnerabilities in `helpdesk.py`, then write regression tests graded against reintroduced vulnerabilities | `lab-guided/README.md` |
| Independent lab (LO3-LO5) | Review `notes_service.py` against a security specification, fix it and write regression tests; graded on hidden exploit tests and mutants | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 10. Summary

- Injection is one mistake in many forms: text from outside changed the structure of a command. Pass values as values.
- Allow-lists fail closed; deny-lists fail open. Avoid the shell, parse with formats that cannot run code, resolve paths before trusting them, verify certificates and token signatures.
- Store passwords as salted slow hashes, compare secrets in constant time, never keep secrets in source or logs.
- Prove each fix with a regression test that checks the effect, and remember what a linter cannot see.

## References

- OWASP Top 10:2025 (R-035) and OWASP Top 10 for LLM Applications 2025 (R-028), as read from the official pages on 2026-10-14.
- Executed probes: `pyyaml-unsafe-load`, `pyjwt-decode-algorithms`, `paramiko-host-key-policy` (docs/research/data/api_probes_2026-10-14.json).
- Findings addressed: F-PYH-001, F-PYH-002 (P0/P1 security defects in the source), F-PYH-007.
