# PY-M07 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | Which change makes `conn.execute(f"SELECT name FROM users WHERE name = '{name}'")` safe against injection? | A) Replace every apostrophe in name with two apostrophes before building the string. B) Wrap the f-string in str(). C) Pass the value as a parameter: conn.execute("SELECT name FROM users WHERE name = ?", (name,)). D) Convert name to lower case first. |
| Q2 | LO1 | A user named O'Brien searches with the f-string query from Q1. What happens? | A) It returns O'Brien's row. B) The query is a syntax error because the apostrophe ends the string literal early. C) It returns every row in the table. D) It returns no rows and no error. |
| Q3 | LO2 | Which design for a calculator that evaluates text typed by users fails closed (rejects anything it did not expect)? | A) Parse the text into a syntax tree and accept only a list of allowed node types. B) Reject text that contains the words import or open, then call eval. C) Call eval inside try/except and return None on any error. D) Call eval with an empty dictionary as the builtins. |
| Q4 | LO2 | `subprocess.run(f"ls {path}", shell=True)` is called with path = "x; echo hi". What runs? | A) Only ls, with one odd directory name. B) Nothing: subprocess refuses text containing a semicolon. C) ls with the option -x. D) ls x, and then echo hi, because the shell treats the semicolon as a command separator. |
| Q5 | LO3 | Which check confines a user-supplied file name to an attachment folder? | A) Reject names that contain the text .. B) Check that the joined, unresolved string starts with the folder path. C) Resolve the joined path and verify that it lies inside the resolved folder. D) Check that the file exists. |
| Q6 | LO3 | A function calls pickle.loads(blob) and then raises ValueError if the result is not a dict. Why is this not a fix for unsafe deserialisation? | A) The payload's code runs while the data is being loaded, before any check on the result. B) isinstance checks are too slow. C) A dict cannot be pickled. D) Pickle cannot return a dict. |
| Q7 | LO4 | Why is hashlib.md5(password.encode()).hexdigest() unsuitable for storing passwords? | A) It produces output that is too long to store. B) It cannot hash text that contains non-ASCII characters. C) It was removed from Python 3.13. D) It is unsalted and fast: equal passwords give equal hashes and an attacker can test guesses cheaply. |
| Q8 | LO5 | A security-focused linter run (for example ruff --select S) reports no findings for a module. What can you conclude? | A) The module has no vulnerabilities. B) None of the patterns the rules know are present; other flaws, such as path traversal, can remain. C) The module's tests are complete. D) The module's dependencies are free of known vulnerabilities. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
