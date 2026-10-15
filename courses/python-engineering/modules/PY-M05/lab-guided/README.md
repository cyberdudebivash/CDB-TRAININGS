# PY-M05 guided lab - A catalogue client that survives a bad day

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and the pinned toolchain (`../../../labs/requirements.txt`: `httpx`, `pydantic`, `pytest`). No network and no account: the checks start a small web server on your own computer (`127.0.0.1`) and make it misbehave on purpose.

`starter/syncer.py` is a client for a product-catalogue API. The **schemas, the error classes and the constants are given**; seven functions are not. Each docstring is the specification and `checks/test_syncer.py` is the test suite: work through the steps in order, one failing test at a time (`python -m pytest -k delay_for`).

## The API in the checks

`GET /products?limit=N[&cursor=C]` answers `{"items": [ {id, name, price_cents, currency, tags, ...}, ... ], "next_cursor": "cur-3"}`; `next_cursor` is `null` on the last page. The fixture can answer slowly, close the connection without answering, send status 429 with a `Retry-After`
header, 502/503/504, an HTML error page, broken JSON, a redirect, or items that break the schema. `checks/conftest.py` and `../../../labs/_tools/scripted_server.py` show how; read them once, they are short.

## Setup

```bash
cd courses/python-engineering/modules/PY-M05/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/syncer.py`. Network code is tested **without waiting**: the functions take a `sleep` argument and the checks pass a recorder, so a test about backoff takes milliseconds.

## Step A - `read_settings`: a validated configuration file (LO1, LO2)

Read the TOML file with `tomllib` (open it in **binary** mode; the module decodes UTF-8 itself), then validate the dictionary with `Settings.model_validate`. Turn a `pydantic.ValidationError` into `SettingsError(summarise(error))` (the helper is provided) and an invalid TOML file into
`SettingsError("invalid TOML in <name>: ...")`. Let a missing file raise `FileNotFoundError`. Run `python -m pytest -k read_settings`. In `notes.md` (create it next to this file): why does the schema say `strict=True`, and what would a settings file with `page_size = "50"` do without it?

## Step B - `write_json_atomic`: never leave a half-written file (LO1)

Serialise **first** (a value JSON cannot represent must not touch the disk), write to a temporary file in the same folder, then `os.replace` it over the target. If anything fails, delete the temporary file and let the error continue. The checks make serialisation fail, make the replacement fail, and
then list the folder. In `notes.md`: why must the temporary file be in the *same folder* as the target? (Hint: what does `os.replace` do across file systems?)

## Step C - `make_client`: one shared client with explicit limits (LO3)

Build one `httpx.Client`: base URL from the settings, a `httpx.Timeout` whose read, write and pool values equal `timeout_seconds` and whose connect value is the smaller of that and 3 s, redirects **not** followed, and a `User-Agent` of `catalogsync/1.0`. Pass the optional `transport` through.
In `notes.md`: what would `httpx.get(url)` (no client) have cost you, and what is the default timeout of `requests.get(url)`? (Lesson section 5.)

## Step D - `delay_for`: how long to wait (LO4)

A pure function, so write it first and test it alone. Backoff doubles from 0.5 s and is capped at 8 s. A `Retry-After` header is either whole seconds or an HTTP date; use it when it is longer than the backoff, never beyond 30 s; ignore anything you cannot read, including negative numbers, fractions and `"٣"` (an Arabic-Indic three that `int()`
would accept). For dates use `email.utils.parsedate_to_datetime` and the `now` argument. In `notes.md`: why is there a cap on a server's `Retry-After`?

## Step E - `fetch_json`: one request, done properly (LO3, LO4)

Loop over attempts. Retry only what is transient (`httpx.TransportError` and the statuses in `RETRY_STATUS`); sleep between attempts but never after the last; raise `RetriesExhausted` at the end. Everything else is **not** retried: a 404 will still be a 404, an HTML page will still be HTML.
Check the content type before you decode, and check that the decoded value is an object. In `notes.md`: name two failures you retry and two you do not, and say why each belongs where it is (RFC 9110, section 9.2.2).

## Step F - `iter_products`: pagination that cannot run away (LO2, LO5)

A generator: request a page, validate the page with `Page` and every item with `Product`, yield the products, follow `next_cursor`. It must be lazy (the checks count requests), must report `SchemaError(page, index, ...)`, must stop on a cursor it has already seen, and must stop after `max_pages` pages.
In `notes.md`: which two inputs would make a naive `while next_cursor:` loop run forever?

## Step G - `sync`: all or nothing (LO1, LO5)

Collect everything first (`sorted` by id), then call `write_json_atomic` once. A failure on page 3 of 3 must leave yesterday's file exactly as it was. In `notes.md`: what does the reader of `catalogue.json` see while a sync is running, and why is that better than a file that grows page by page?

## Finish

Run `python -m pytest` and keep the output with your notes. Then refactor and run it again.

## What you hand in

`starter/syncer.py` and `notes.md` (the answers from steps A to G, one page). Passing the provided checks shows that your functions do what the checks test, against one scripted server; it does not show that the code is safe against every server, which the independent lab explores.

## Checking against the public solution (optional)

`solution/syncer.py` is the reference implementation. **Try each step yourself first.** To confirm the checks are sound, run them against the solution:

```bash
LAB_TARGET=solution python -m pytest         # Windows PowerShell:  $env:LAB_TARGET="solution"; python -m pytest
```
