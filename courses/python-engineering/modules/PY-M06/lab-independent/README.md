# PY-M06 independent lab - `wordjob`: make an I/O-bound job faster and prove it

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Graded by:** automated checks plus a reviewer rubric (`../assessment/rubric.yaml`)

`starter/wordjob.py` counts the words of many remote documents. It gives you the result record `JobResult`, the path helper `doc_path` and a **sequential baseline** `count_words_sequential` that works but waits for every document in turn. You write the asynchronous version `count_words`, and a benchmark script that
shows how much faster it is. The published checks (`checks/test_wordjob.py`) are a sample; instructors grade your module against a **larger hidden suite** that measures concurrency, speed, failures, deadlines and cancellation. There is no reference solution in this repository; you may reuse ideas and code from your guided lab.

## The documents

`GET {base_url}/docs/<id>` returns the document as UTF-8 text with status 200. `starter/fixture.py` starts a local server for your own experiments: `serve(count, latency)` returns `(base_url, stop)`; document *i* has `(i % 7) + 3` words and every answer takes `latency` seconds.
The checks use stricter servers: slow documents, dropped connections, error statuses, bytes that are not UTF-8.

## Specification of `count_words(client, doc_ids, *, limit=8, timeout=2.0, deadline=30.0)`

`client` is an `httpx.AsyncClient` with its base URL already set; do not create another one. The function returns a `JobResult`.

1. **Same answers as the baseline.** For every distinct id (ids may be given as text or numbers and are used as text; each distinct id is requested **once**), the outcome is exactly what `count_words_sequential` would record: the number of words (`str.split()` on the UTF-8 text) in `counts`, or a reason in `errors`:
   `"HTTP <status>"` for any status other than 200, `"bad encoding"` when the body is not valid UTF-8, `"connection error"` when the connection fails, `"timeout"` when a time limit passes (yours or the client's own). Nothing is retried.
2. **Bounded concurrency.** At most `limit` requests are in flight at any moment, and the limit is really used. `limit` below 1 raises `ValueError("limit must be at least 1")`. The default is 8.
3. **A time limit per document.** `timeout` seconds for one request, counted from the moment that request starts (not from the start of the job, and not including the time spent waiting for a free slot). A document that exceeds it is recorded as `"timeout"` and does not affect the others.
4. **A deadline for the whole job.** After `deadline` seconds the job stops: requests still running are cancelled, and every distinct id that has neither a count nor an error is recorded as `"deadline"`. The function returns promptly (about the deadline) with no task left running.
5. **Failures are local.** One failing document never stops, delays or changes the result of another.
6. **Cancellation.** If the task running `count_words` is cancelled, all its requests are cancelled and `asyncio.CancelledError` propagates to the caller; no task is left behind.
7. **Never block the event loop.** No `time.sleep`, no synchronous HTTP, no long computation inside a coroutine: other tasks of the caller must keep running while the job runs.
8. **Safe paths.** Build every URL path with `doc_path(id)`; an id must never be able to change the path.
9. **Bookkeeping.** `requests` is the number of HTTP requests started; `elapsed_s` is the wall-clock time of the call in seconds (use `time.perf_counter`).

## The benchmark script `starter/benchmark.py` (you write it)

```bash
python starter/benchmark.py --docs 40 --latency 0.05 --limit 8 --repeats 5
```

It starts a local server with `fixture.serve`, runs the sequential baseline and your `count_words` **alternately** `--repeats` times each on the **same ids**, and prints **one JSON object** on standard output with exactly these keys:

| Key | Meaning |
|---|---|
| `docs`, `latency_s`, `limit`, `repeats` | the parameters used |
| `baseline_median_s`, `concurrent_median_s` | median wall-clock seconds of each candidate |
| `speedup` | `baseline_median_s / concurrent_median_s` |
| `baseline_range_s`, `concurrent_range_s` | `[fastest, slowest]` of the runs of each candidate |
| `results_identical` | `true` when both candidates returned the same `counts` and `errors` in every repeat |
| `not_tested` | one sentence naming what the benchmark does **not** show (other sizes, real network, failures, memory, ...) |

The exit status is 0 when the results were identical and 1 when they were not. The script must not print anything else on standard output.

## Setup and running the checks

```bash
cd courses/python-engineering/modules/PY-M06/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs the published checks against starter/wordjob.py - they fail until you have written count_words
```

## What you hand in

1. `starter/wordjob.py` and `starter/benchmark.py`.
2. `notes.md`, one page: the numbers your benchmark printed and the computer you ran it on; what limit you chose and what happened with a smaller and a larger one; what the benchmark does not show; the failure you think is most dangerous for a nightly job using this code and how your code handles it; and the rules of the specification you tested **yourself** beyond the published checks.

## How it is graded

Three automated criteria are must-pass: the published checks, the hidden suite (see the rubric for the threshold) and the benchmark report contract. A reviewer scores code clarity and the honesty of `notes.md` from 0 to 3 each. Finishing the lab without meeting the pass rule is not a completion claim.
