# PY-M07 guided lab - Fix eight vulnerabilities, then prove each fix

**Time:** about 3 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+, the packages in `../../../labs/requirements.txt` (pytest, PyYAML, ruff). Shell checks need a POSIX system (Linux, macOS, or WSL on Windows). No network is used.

> **Safety.** Every attack in this lab is a harmless probe against code in this repository (an empty directory is created, `echo` is run, an in-memory database is queried). Never point such tests at a system you do not own or have written authorisation to test.

`starter/helpdesk.py` contains small helper functions of an internal help-desk tool. Each function works for friendly input and is **vulnerable to hostile input**. Your job: fix the module without breaking its behaviour,
then write tests that would catch each vulnerability if it came back.

## The contract (what each function must do)

| Function | Must do |
|---|---|
| `calculate(expression)` | Evaluate arithmetic: numbers, `+ - * / %`, unary signs, parentheses, `**` with a whole exponent from 0 to 64. Anything else (names, calls, attributes, strings), text longer than 100 characters, or division by zero raises `ValueError`. |
| `find_users(conn, name)` | Rows `(name, email, role)` of users whose name equals `name` exactly. |
| `list_files(directory)` | Sorted names in the directory; `NotADirectoryError` (or `FileNotFoundError`) if it is not a directory. |
| `read_attachment(base, filename)` | The bytes of a file **inside** `base`. Anything that would leave the folder (`..`, absolute paths, links pointing out) or names the folder itself raises `ValueError("invalid attachment name")`. |
| `dump_session(data)` / `load_session(blob)` | A session is `{"user": 1-64 characters, "role": "viewer" \| "agent" \| "admin"}`. Round trip works; anything else raises `ValueError("invalid session")`. Loading must never execute anything contained in the bytes. |
| `load_config(text)` | Parse a YAML document that must be a mapping; otherwise `ValueError("invalid configuration")`. Loading must never build Python objects or run code. |
| `make_tls_context()` | A TLS client context that verifies certificates and host names and keeps the library's protocol defaults. |
| `hash_password(password)` / `verify_password(password, stored)` | `scrypt$<salt hex>$<hash hex>` with a fresh random salt each time; verification is constant-time and returns `False` for malformed or legacy values. |

## Setup

```bash
cd courses/python-engineering/modules/PY-M07/lab-guided
python -m venv .venv && . .venv/bin/activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                      # checks/ against starter/ - the exploit and static checks fail at the start
```

Checks named `test_works_*` describe behaviour that **must keep working**; they pass on the starter and must still pass after your fixes. Checks named `test_exploit_*` attack the code and fail while a vulnerability exists.
`test_static_*` runs ruff's security rules.

## Step A - See the failures (LO1)

Run `python -m pytest -q --tb=line` and read the failing `test_exploit_*` names. For each of the eight areas (calculator, SQL, shell, path, session, config, TLS, passwords) write one sentence in `notes.md`: *what can an attacker make the function do?*
Pay attention to the check about names with apostrophes: an honest user is also hurt by one of these bugs. Which one, and what does that tell you about "secure" versus "correct"?

## Step B - Fix the injections (LO2)

Fix `calculate` (parse with `ast`, allow only the node types in the contract; do not call `eval`), `find_users` (a parameter placeholder, never string building) and `list_files` (no shell). Run `python -m pytest -q -k "calculator or sql or shell or files or users or apostrophe"`.

## Step C - Files, parsers and TLS (LO3)

Fix `read_attachment` (resolve, then check containment; remember absolute paths and links), `load_session` and `dump_session` (JSON plus validation instead of `pickle`), `load_config` (`yaml.safe_load` plus validation) and `make_tls_context`.
Run the matching checks. Note that the session and YAML checks look for a **side effect** (a directory being created), not only for an exception. Why is validating after an unsafe parse too late?

## Step D - Passwords and secrets (LO4)

Replace the MD5 functions with `hashlib.scrypt` (parameters `n=2**14, r=8, p=1, dklen=32`), a random 16-byte salt from `secrets`, the `scrypt$salt$hash` format and `hmac.compare_digest`. Malformed or legacy values must verify as `False`.

## Step E - Static analysis

```bash
python -m ruff check --no-cache --select S starter/helpdesk.py
```

On the starter it reports eight findings. Which of the eight vulnerabilities did it **not** report? Run it on your fixed module: it must be clean (`test_static_ruff_security_rules_are_clean`). A clean run does not prove safety - say in `notes.md` what it cannot see.

## Step F - Regression tests (LO5)

Write tests in `student_tests/test_regressions.py` - at least one per vulnerability - that **fail if the vulnerability is put back**. Then run the mutation check against the secure reference (`solution/helpdesk.py`),
which reintroduces each vulnerability one at a time:

```bash
python ../../../labs/_tools/mutation_check.py --module-dir solution --module helpdesk --tests student_tests --mutants checks/mutants.json
```

- You pass when your tests pass on the correct module and all **eight required** mutants (V1-V8) are killed.
- Five **stretch** mutants cover a naive `..` filter, a missing role check, limits on size, and a timing-unsafe comparison. The last one cannot be seen by behaviour tests: it is **expected to survive**, and noticing why is the point.
- Test the *effect*: for deserialisation check that no marker was created; for shell injection check that the injected command did not run. A test that only expects an exception can pass while the damage is done.

Do not read `solution/` before you have tried: the reference is used by the check and is public, but the learning is in finding the weak spots yourself.

## Reflection (write in `notes.md`)

1. Which vulnerability was hardest to test, and why?
2. Which mutant survived your first attempt and what did you add?
3. Name one security property of this module that neither the linter nor your tests check.

## What the automated checks prove - and what they do not

They prove that the listed attacks fail, the listed behaviour is kept, the security lint rules are clean and your tests detect the reintroduced vulnerabilities. They do not prove the module is secure: other attacks, other inputs and deployment settings are out of scope.
