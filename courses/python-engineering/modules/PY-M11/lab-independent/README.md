# PY-M11 capstone, part B - build authwatch

**Time:** about 8.5 hours  |  **Outcomes:** LO1-LO6  |  **Needs:** Python 3.11+, the packages of `../../../labs/requirements.txt`, and the project of part A (`project/`). No network, account, paid service or open port. **Prerequisite:** the lesson and part A.

You build the application the specification describes. `SPEC.md` is the contract; read all of it before you write a line. The published checks (`python -m pytest` in this folder, 14 functions, 22 cases) show the shape of the answers. The release gate (`python ../lab-guided/tools/gate.py`, thirteen gates) tells you which engineering conditions are not met. Instructors run a hidden suite of several hundred checks on your application and a mutation check on **your own tests**. **A project that passes only the published checks and the gate is not finished.**

## Setup

```bash
cd courses/python-engineering/modules/PY-M11/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against project/src - all fail until you build something
python ../lab-guided/tools/gate.py                    # all thirteen gates; part A's eleven should already pass
```

## What you hand in

1. `project/` complete: the package, `tests/`, `scripts/check.py`, `.github/workflows/ci.yml`, `README.md`, `CHANGELOG.md`, `requirements.lock`.
2. `project/NOTES.md`: the characterisation table of part A, and a **risk table** with one row for each of these ten risks - the sentence of your design that handles it and the check (a test of yours, a published check or a gate) that would notice if someone removed it: input that exhausts memory, input that makes the parser execute something, a diagnostic that repeats input, a report that is half written after a crash, a report readable by other users, a closed pipe, a corrupt archive, a rules file that changes behaviour silently, a dependency with an advisory, a workflow that runs untrusted text. A section **Handover** of at most fifteen lines: how to run every check, what is not done, the decision you are least sure of and what you would do next.
3. Nothing else. In particular no copy of the tools or of the specification.

## The milestones (a suggestion, not a rule)

| Milestone | Hours | What you do |
|---|---|---|
| B1 Reading | 1.5 | `Event`, `ParseError`, `parse_line` with every rule of section 2, `read_events` with the bounded read, the byte-order mark, the line limit and the error budget. Write the tests as you go; the table-driven style of the lesson's section 5 fits. |
| B2 Rules | 1.0 | `Rules` (validation, immutability), `parse_rules` with a safe loader, `load_rules` with the size limit. Every code of section 5 has a test. |
| B3 Detection | 2.0 | `detect` with the three patterns, episodes, the window arithmetic and the skipped out-of-order events; state that does not grow with the input. Write the oracle of lesson section 5 first: a slow function that follows section 4 literally, and compare. |
| B4 Output and command line | 1.5 | `render` (both formats, byte-exact), then `authwatch scan` with every option, the exit statuses and the streams of section 7. |
| B5 Operations | 1.0 | Atomic output with mode `0600`, the closed pipe, Ctrl-C, `-v`, gzip files, no input text in any message. Run the live scenario: `python ../lab-guided/tools/make_events.py --seed 7 --junk 0.002 --skew 30 --bom --crlf --truth /tmp/truth.json \| python -m authwatch scan --format json -`. |
| B6 Standard | 1.5 | Tests to the standard of the gate (at least 30, branch coverage of at least 90 percent, edges and failures, not only the happy path), `NOTES.md`, the README, the changelog, and a final `python ../lab-guided/tools/gate.py` with thirteen of thirteen. |

## The interface the tests call

The published checks and the instructors' suite use only what `SPEC.md` names: `authwatch.parse_line`, `read_events`, `parse_rules`, `load_rules`, `detect`, `render`, the classes of section 3, and the command line (`python -m authwatch`). Anything else is yours to design and to keep private. The same rule applies to **your own tests**: if they import a module the specification does not name, they cannot be run against another implementation, and the instructors' check of your tests (below) will report that they fail on the reference.

## How it is graded

| What | By whom | How |
|---|---|---|
| the gate, thirteen of thirteen | you, then instructors | `tools/gate.py`; it runs your tools with its own settings, so a weaker setting in your `pyproject.toml` cannot hide a problem |
| behaviour | instructors | a hidden suite of 585 checks written from `SPEC.md` only: parsing and the limits of every field, reading and the line limit, rules, the window arithmetic, an oracle written from the specification and compared with `detect` on random streams, the renderings byte for byte, every option and exit status of the command line, and a corpus of hostile input |
| your tests | instructors | your `tests/` folder is copied away from your project and run against the instructors' implementation (it must pass) and against defective copies of it (it must fail on most of them) |
| your notes | a reviewer | the characterisation and the risk table, scored on the rubric |

## Hints that are not solutions

- Decide the order of the checks of one line once, on paper. The specification fixes the code of a line with one fault; the order for a line with two is yours.
- `readline(size)` is the bounded read; iterating over the stream is not.
- The window rule has two edges (the oldest failure and the newest), and the instructors' suite tests both. Test the edge *and one unit beyond it*, on both sides.
- State that is kept for every source seen is a memory leak in a long-running process. Decide when a source may be forgotten and prove that forgetting it changes nothing.
- A test that runs the command line costs a process each. A hundred of them is a minute; keep most of your tests in-process and keep a dozen at the edge.
- The message of an exception is not a place for data.
