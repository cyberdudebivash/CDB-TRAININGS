# PY-M07 independent lab - Review and fix `notes_service`

**Time:** about 3 hours  |  **Outcomes:** LO3-LO5  |  **Graded by:** instructor exploit tests, hidden vulnerability mutants and a reviewer rubric (`../assessment/rubric.yaml`)

> **Safety.** Work only on the code in this folder. Never use the techniques you find here against a system you do not own or have written authorisation to test.

`starter/notes_service.py` handles session tokens, renders notes as HTML, exports notes to a file, logs logins and validates redirect targets. It works for friendly input and **does not meet the security specification below**. There is no list of defects and no reference solution
in this repository: reading the specification against the code is the exercise.

## Security specification

1. **Secret.** Tokens are signed (HS256) with a secret read from the environment variable `NOTES_SECRET` at the moment it is needed. A missing secret or one shorter than 32 characters raises `RuntimeError` (fail closed). No secret value may appear in the source.
2. **Tokens.** `verify_token` returns the `sub` claim only for a token that has a valid signature made with the secret, an unexpired `exp`, and both `sub` and `exp` claims. Anything else raises `ValueError("invalid token")`. Unsigned and differently signed tokens are never accepted.
3. **Rendering.** `render_note` output must be safe to place in an HTML page: the title and the body are HTML-escaped, including quotes.
4. **Export.** `export_notes` creates a new file with an unpredictable name that no other user can read or write (mode 0600 on POSIX), even when the process has a permissive umask. Content is the notes joined by newlines.
5. **Logging.** `log_login` records the user name and the result, and never the password or anything derived from it.
6. **Redirects.** `safe_redirect` returns the target only if it is a local absolute path: it starts with a single `/`, is not protocol-relative, contains no backslash and no control characters. Everything else (including an empty string) becomes `/`.

## Setup and running

```bash
cd courses/python-engineering/modules/PY-M07/lab-independent
python -m venv .venv && . .venv/bin/activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs student_tests/ against starter/ (your working copy)
```

## What you hand in

1. A fixed `starter/notes_service.py` that meets the specification and keeps the behaviour for friendly input.
2. `student_tests/` - regression tests, at least one per specification item, that fail if the vulnerability is reintroduced. Test effects, not only exceptions.
3. `notes.md` - one page: for each fix, the attack that worked before and why it stops now; and what your tests and the specification do **not** cover.

## How it is graded

Instructors run their exploit suite on your fixed module (rubric C1 and C2, must-pass), run your tests against hidden reintroduction mutants (C3, must-pass: at least 8 of 9 required mutants killed), and score effect-based testing and threat reasoning (C4 and C5).
Finishing the lab without meeting the pass rule is not a completion claim.
