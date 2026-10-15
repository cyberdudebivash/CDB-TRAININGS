# PY-M09 guided lab - Find the bottleneck, fix it, and prove that nothing changed

**Time:** about 3 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`. No network, no account and no paid service.

`starter/perfkit.py` digests a log of login attempts (one per line: `2026-10-14T12:00:03Z 10.0.0.5 alice FAIL`): how many attempts, how many failed, which addresses made at least `threshold` failures within `window` seconds, which users failed most. It **works and gives the right answers, slowly**. `checks/slow_baseline.py` is a copy of that slow program: the checks use it as the oracle (your answers must be identical) and as the thing to beat. You will profile it, fix what the profile points at, use less memory, and keep the core free of input and output. **A refactoring lab:** the correctness checks pass from the first minute (they are your safety net) and the checks that fail are exactly the ones about measuring, speed, memory and structure.

## Setup

```bash
cd courses/python-engineering/modules/PY-M09/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - the speed, memory, profiling and edge checks fail at first
```

Edit only `starter/perfkit.py`. Run one step with `python -m pytest checks/test_step_a_profile.py` (also `b_hotspot`, `c_algorithms`, `d_parse`, `e_memory`, `f_architecture`). `LAB_TARGET=solution python -m pytest` checks the public reference instead; read `solution/perfkit.py` only after your own version passes, and compare the *shape* of the two. Timing checks compare ratios or budgets that are an order of magnitude away from both a correct and an unscalable solution; they will not fail because your machine is slow or busy.

## Step A - measure: `Profile.top` and `profile` (LO1)

Write `profile(func, *args, **kwargs)` with `cProfile` and `pstats`: it returns the function's result and a `Profile` (rows sorted by own time, the total number of calls, the total time). Call counts are exact and identical on every run and every Python version; times are not. Write `Profile.top(n, by)`. Run `python -m pytest checks/test_step_a_profile.py`. Lesson sections 2 to 4.

In `notes.md`: profile `fib(15)`. How many calls does `fib` make, and why does that number not depend on the machine?

## Step B - read the profile: `hotspot` (LO1, LO2)

`hotspot(profile, file, exclude)` names the function of one source file with the largest **cumulative** time, leaving out the entry point (which always contains everything). The checks profile the slow program on a realistic log and expect `top_users`; use your own helpers on the starter's `analyze` and look at the table yourself first. Run `python -m pytest checks/test_step_b_hotspot.py`.

In `notes.md`: the profile says `top_users` carries about 60 percent of the run. If you made it ten times faster, what whole-program speed-up does Amdahl's law (lesson section 3) predict? What if you instead made `unique_ips` (about 6 percent) a thousand times faster?

## Step C - the same answers, a better algorithm (LO2, LO4)

Fix the four functions the profile points at, **largest share first, and re-profile after each**: `top_users`, `bursts`, `failures_by_ip`, `unique_ips`. Every answer must stay exactly what it was, including the order of the results, the handling of ties, out-of-order timestamps and invalid arguments: the checks compare with the slow program on edge cases and on 40 random inputs. The scaling checks give each function an input where a quadratic algorithm needs seconds and a linear one milliseconds (a budget of a quarter of a second sits between them), and the last check demands that the whole analysis be at least 30 percent faster than the slow program. Run `python -m pytest checks/test_step_c_algorithms.py`.

In `notes.md`: why is a budget "less than 0.25 seconds on an input where the slow code needs several seconds" safer than "less than 20 milliseconds"?

## Step D - parse once, convert once (LO2)

`parse_line` builds its pattern for every line and converts the same date again and again. Build the pattern once, cache the date conversion (a small bounded `functools.lru_cache`), and keep every answer, including the many ways a line can be malformed (an octet of 256, hour 24, 30 February). The checks count function calls (exact, never flaky) and date conversions. Run `python -m pytest checks/test_step_d_parse.py`.

In `notes.md`: the check counts *function calls* here and *time* in step C. Why is a call count the right measure for parsing and the wrong one for the matching loop in lesson section 3?

## Step E - memory (LO3)

Make `analyze` use at most 60 percent of the peak memory of the slow program on a stream of 20 000 lines: do not keep the lines, and make repeated addresses and user names share one string object (`sys.intern`). The checks measure with `tracemalloc` (exact) and also look at the bytes held per `Attempt`. Run `python -m pytest checks/test_step_e_memory.py`.

In `notes.md`: what does `Attempt` being a `@dataclass(frozen=True, slots=True)` already save, and what would `sys.intern` do to the memory of a log with 10 million lines and 500 distinct addresses?

## Step F - the core computes, the edge reads and writes (LO5)

Write `FileSource.lines` (lazy, UTF-8, closes its file on every path, strips line endings) and `main(argv, out, err)` (options `--threshold`, `--window`, `--top`; exit code 0 for a report, 2 for a usage error with nothing on `out`, 1 for an unreadable file with one line on `err`; only the given streams, never `sys.stdout`). Subclass `argparse.ArgumentParser` and override `error` so that a usage error raises instead of exiting the process. A check reads the code with `ast` and fails if a core function opens a file, prints or knows the edge. Run `python -m pytest checks/test_step_f_architecture.py`. Lesson section 8.

In `notes.md`: name one thing the core/edge split made easier to test in this lab.

## When you are done

All checks pass and `notes.md` has your answers. Then read `solution/perfkit.py` and compare the three places where you and the reference differ most. The independent lab gives you a different slow program, a hidden suite that tries to catch an "optimisation" that changes an answer, and asks you to write the budget tests yourself.

## What the checks do not tell you

They test behaviour, work and structure, not whether the code is pleasant to read, and not performance on your real data: profile that yourself. A passing run is an automated check, not a review by an experienced engineer, and the module has not been used with learners.
