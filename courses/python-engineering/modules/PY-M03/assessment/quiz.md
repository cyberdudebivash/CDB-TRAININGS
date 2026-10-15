# PY-M03 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | A function is annotated `def double(x: int) -> str` and its body is `return x * 2`. It is called with 3. What happens when the program runs? | A) It raises TypeError because 6 is not a string. B) It returns 6: annotations are not enforced when the program runs. C) It returns the text '6' because Python converts to the annotated type. D) It raises SyntaxError when the function is defined. |
| Q2 | LO1 | A dataclass has the field `age: int` and you create `User('ada', 'thirty-six')`. What happens? | A) The object is created: dataclasses do not validate types at run time. B) TypeError is raised by the generated __init__. C) ValueError is raised because the text is not a number. D) The text is converted to 0. |
| Q3 | LO2 | You run mypy with default settings on a file whose functions have no annotations and it reports 'no issues found'. What does that tell you? | A) The code is free of type errors. B) The code is fully typed. C) Almost nothing: by default mypy does not check the bodies of functions that have no annotations. D) mypy could not read the file. |
| Q4 | LO2 | mypy reports `Item "None" of "User \| None" has no attribute "name"  [union-attr]` for `find(users, 'ada').name`. What is the right fix? | A) Handle the missing case explicitly (test for None and raise or return early) before using the value. B) Add `# type: ignore` to the line. C) Wrap the call in `cast(User, ...)`. D) Change the return annotation to `Any`. |
| Q5 | LO2 | Rows from a CSV are typed `dict[str, str]` and the code compares `row['qty'] < row['reorder_level']`. mypy is satisfied, yet `'9' < '10'` is false. What is the lesson? | A) mypy is broken for comparisons. B) Strings should never be compared. C) The comparison needs a `# type: ignore`. D) The type said 'text', so the bug was invisible; model quantities as int in a typed record and convert once at the boundary. |
| Q6 | LO3 | What does `__all__` in a package's `__init__.py` do? | A) It makes every other name private and inaccessible. B) It documents the public interface and controls what `from package import *` brings in; it does not make other names private. C) It speeds up imports. D) It is required for mypy to run. |
| Q7 | LO3 | Module a imports module b at the top, and b imports a at the top. Importing a fails with a message about a partially initialized module. What is the best fix? | A) Wrap one import in try/except ImportError. B) Import the module twice. C) Move the shared code into a third module that both import, so dependencies point one way. D) Rename the modules. |
| Q8 | LO4 | Why do many projects use a `src/` layout? | A) It stops the working directory from being importable, so tests only pass if the package is importable the way users will import it. B) It makes Python run faster. C) It is required by pytest. D) It lets tests live inside the package. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
