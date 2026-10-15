# PY-M01 independent lab - `logkit`: summarise a log file

**Time:** about 4 hours  |  **Outcomes:** LO1-LO5  |  **Graded by:** automated checks plus a reviewer rubric (`../assessment/rubric.yaml`)

You are given `starter/logkit.py` (five functions that raise `NotImplementedError`), `starter/examples.md` (a few worked examples that you can run) and `starter/sample.log`. You implement the functions from the specification below, then write a small command-line script that uses them on a file.
The published examples are only a sample: instructors check your module against a **larger hidden test suite**, so reading the specification closely and thinking about edge cases is part of the task. There is no reference solution in this repository.

## Specification

A **valid log line** has the form `YYYY-MM-DD HH:MM:SS LEVEL message`:

- The timestamp is a real date and time written with the ASCII digits 0-9 (`2026-02-30` and `24:00:00` are not valid; 29 February exists only in leap years; digits from other writing systems are not accepted).
- `LEVEL` is exactly one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (upper case only) and is followed by at least one space.
- The message is everything after the level: leading spaces removed, trailing whitespace removed, inner spacing kept. It must contain at least one non-space character.
- Spaces or tabs around the whole line are ignored.

| Function | Contract |
|---|---|
| `parse_log_line(line)` | Returns `(timestamp, level, message)` as three strings. Raises `ValueError` with the message `invalid log line: <line>` (the line exactly as it was given) when the line is not valid. |
| `count_levels(lines)` | Returns a dictionary of how many **valid** lines each level has, ordered by severity (the order of the list above). Lines that are not valid, and not blank, are counted together under `"INVALID"`, which comes last. Blank lines (empty or only spaces) are ignored. Levels with a count of zero are left out; no lines gives `{}`. |
| `top_messages(lines, n)` | Returns the `n` most frequent messages among the valid lines as `(message, count)` tuples, most frequent first; messages with equal counts are ordered alphabetically. Fewer than `n` distinct messages gives all of them. `n` below 1 raises `ValueError("n must be at least 1")`. |
| `busiest_hour(lines)` | Returns the hour with most valid lines as text like `"2026-10-14 12"` (date and hour; different dates are different hours). Ties go to the earliest hour. No valid lines gives `None`. |
| `mask_ips(text)` | Replaces the last number of every valid IPv4 address in `text` with `x` (`192.168.1.25` becomes `192.168.1.x`) and changes nothing else. A valid address is four numbers from 0 to 255 without leading zeros, separated by dots, that is not part of a longer run of digits and dots (`1.2.3.4.5` and `256.1.1.1` are not addresses). A full stop after an address is not part of it. |

None of the functions may change the list or the text it receives. The same input must always give the same output.

## Setup and running the checks

```bash
cd courses/python-engineering/modules/PY-M01/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs the published examples against starter/logkit.py
```

Work in this order: (1) `parse_log_line`, because the other functions depend on it; (2) `count_levels`; (3) `top_messages` and `busiest_hour`; (4) `mask_ips`; (5) `report.py`.
After each function, run the examples again. Add **your own** examples or tests for every edge case you can think of - the hidden suite will contain cases that are not in `examples.md`.

## The script `starter/report.py` (you write it)

Write a script that prints a JSON summary of a log file:

```bash
python starter/report.py starter/sample.log
```

For `starter/sample.log` it must print JSON with exactly these keys, in this order, and these values (indentation is free):

```json
{
  "levels": {"DEBUG": 1, "INFO": 2, "WARNING": 1, "ERROR": 2, "INVALID": 1},
  "top_messages": [["service started", 2], ["cache warm", 1], ["paiement échoué for order 7", 1]],
  "busiest_hour": "2026-10-14 09"
}
```

Accented letters must be written as themselves, not as escape sequences such as `\u00e9`: pass `ensure_ascii=False` to `json.dumps`.

- The path comes from the command line. Open it with `pathlib` and an explicit UTF-8 encoding, inside a `with` block or with `Path.read_text`.
- The three most frequent messages are shown, with `mask_ips` applied so that the report never prints a full IP address.
- A file that cannot be read gives a one-line message on standard error naming the path and exit status 2, not a traceback.
- Use only the standard library and your own `logkit` module.

## What you hand in

1. `starter/logkit.py` and `starter/report.py`.
2. `notes.md` - one page: the Python version and interpreter you used (output of `python --version` and `sys.executable`); the order in which you got examples to pass; the edge cases you thought of and how you tested each; which data structure you chose for each function and why;
   and what your tests and the published examples do **not** prove.

## How it is graded

Two automated criteria are must-pass: the published examples and the hidden test suite (see the rubric for the threshold). A reviewer scores code clarity, file handling in `report.py` and the honesty of `notes.md` from 0 to 3 each. Finishing the lab without meeting the pass rule is not a completion claim.
