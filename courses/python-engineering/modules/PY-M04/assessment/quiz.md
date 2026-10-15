# PY-M04 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | You run `env/bin/python -m pip install requests` without activating the virtual environment `env`. Where does the package go? | A) Into the system Python's site-packages. B) Into the current directory. C) Into the site-packages of the environment whose interpreter you called. D) Nowhere: pip refuses to install without activation. |
| Q2 | LO1 | Inside a virtual environment, which statement about `sys.prefix` and `sys.base_prefix` is true? | A) They are always equal. B) sys.base_prefix points to the environment. C) Neither exists in Python 3.11 or later. D) sys.prefix points to the environment and differs from sys.base_prefix. |
| Q3 | LO2 | Which `[build-system]` table is the correct way to build a setuptools project with pyproject.toml, using the packaging guide's example? | A) requires = ["setuptools >= 77.0.3"]; build-backend = "setuptools.build_meta". B) requires = ["setup.py"]; build-backend = "distutils.core". C) requires = []; build-backend = "pip". D) requires = ["wheel"]; build-backend = "build". |
| Q4 | LO2 | A pyproject.toml declares `dynamic = ["version"]` and `[tool.setuptools.dynamic] version = { attr = "tinycsv.__version__" }`. What does this achieve? | A) The version is typed twice and must match by hand. B) pip chooses a version at install time. C) The build backend reads the version from one place in the source code. D) The wheel gets no version at all. |
| Q5 | LO3 | After `python -m build`, you list the wheel and find `tests/__init__.py` inside it. What is the most likely cause? | A) Wheels always contain a tests directory. B) pytest copies itself into the wheel. C) The sdist and the wheel were swapped. D) Automatic package discovery included every directory with an __init__.py; the packages to include were not declared. |
| Q6 | LO4 | Why do you run the installed command from a directory that is not your project directory? | A) To make the command run faster. B) So that an import that works only because of the source tree on the path is not mistaken for a working install. C) Because pip refuses to run in the project directory. D) To avoid creating a dist directory. |
| Q7 | LO5 | Where should pytest and ruff, which only developers use, be declared in a modern pyproject.toml? | A) In [dependency-groups]. B) In [project] dependencies. C) In [project.optional-dependencies] under an extra that every user must install. D) In [build-system] requires. |
| Q8 | LO5 | According to the packaging guide, what is the status of running `python setup.py sdist` or `python setup.py bdist_wheel` in a new project? | A) They are the recommended build commands. B) They are required to publish to PyPI. C) They were removed from setuptools and always fail. D) Using setup.py as a command-line tool is deprecated; build with python -m build. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
