# PY-M01 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | A script stops and Python prints a long traceback. Which part tells you most quickly what kind of error occurred and why? | A) The first line, because Python prints the most important line first. B) The last line, which names the error type and its message. C) The number of lines in the traceback. D) The longest file path in the traceback. |
| Q2 | LO1 | You ran `pip install requests`, but `python app.py` fails with `ModuleNotFoundError: No module named 'requests'`. Which check is the most useful first step? | A) Reinstall Python from scratch. B) Rename app.py to requests.py. C) Run `python --version` and nothing else. D) Print `sys.executable` from the interpreter that runs app.py and compare it with the interpreter that pip installed into. |
| Q3 | LO2 | What does `0.1 + 0.2 == 0.3` evaluate to in Python, and why? | A) False, because binary floating point stores most decimal fractions only approximately. B) True, because Python rounds results automatically. C) It raises ValueError. D) False, but only on Windows. |
| Q4 | LO2 | After `a = [1, 2]`, `b = a` and `b.append(3)`, what does `print(a)` show? | A) [1, 2]. B) [3]. C) [1, 2, 3]. D) TypeError. |
| Q5 | LO3 | Which function is pure (the same inputs always give the same output and nothing outside it changes)? | A) def add(items, x): items.append(x); return items. B) def add(items, x): return [*items, x]. C) def add(x): log.append(x); return x + 1   # log is a module-level list. D) def add(x): return x + random.random(). |
| Q6 | LO3 | A function `band(score)` returns 'A' when score >= 90; otherwise returns 'B' when score >= 75; otherwise returns 'C'. What do `band(90)`, `band(89)` and `band(75)` return, in that order? | A) 'A', 'A', 'B'. B) 'B', 'B', 'B'. C) 'A', 'C', 'B'. D) 'A', 'B', 'B'. |
| Q7 | LO4 | You read a CSV file with `csv.DictReader` and want the total of its `age` column. What must you do? | A) Convert each value with `int()` (and decide what to do with bad values), because everything read from a CSV is text. B) Nothing: the csv module detects numbers and returns them as int. C) Open the file in binary mode so that numbers are preserved. D) Pass the file contents to `json.loads` first. |
| Q8 | LO5 | One test in a provided suite fails with `assert 6 == 7`. What is the best next step? | A) Delete the test, because it is probably wrong. B) Rewrite the whole function from scratch. C) Read the specification and the test, then make the smallest change that explains the difference, and run all tests again. D) Change the expected value in the test until it passes. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
