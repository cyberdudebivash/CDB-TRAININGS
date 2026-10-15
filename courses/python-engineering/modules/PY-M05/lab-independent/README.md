# PY-M05 independent lab - `feedsync`: synchronise a vendor price feed

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Graded by:** automated checks plus a reviewer rubric (`../assessment/rubric.yaml`)

A vendor publishes its prices as a paginated JSON feed. You write `sync_feed`, which downloads the whole feed and writes three files, **or fails without changing anything**. The published checks (`checks/test_feedsync.py`) are a sample; instructors grade your module against a **larger hidden suite** that
tries slow, broken, hostile and endless servers. There is no reference solution in this repository; you may reuse ideas and code from your guided lab.

`starter/feedsync.py` gives you the exception classes, the `Summary` record and the constants, so that every solution exposes the same names. You write `sync_feed` and whatever helpers you like.

## The feed

`GET {base_url}/v2/prices?page_size=<n>` returns status 200, content type `application/json`, and an object:

```json
{"data": [ {"sku": "ABC-123", "price": "12.50", "currency": "EUR", "updated_at": "2026-10-01T08:00:00Z", "discount_pct": 10} ],
 "next": "http://host:port/v2/prices?page_token=2"}
```

(`data` holds up to `page_size` items; the example shows one.)

`next` is `null` on the last page, an absolute URL, or a path starting with `/`. The first request carries only `page_size`; later requests use the `next` URL exactly as given.

## What counts as a valid item

| Field | Rule |
|---|---|
| `sku` | text of 3 to 20 characters: upper-case ASCII letters, digits and hyphens, not starting with a hyphen |
| `price` | text: 1 to 9 digits, a dot, exactly two digits (`"0.00"`, `"999999999.99"`); a number is not accepted and the value is never converted to `float` |
| `currency` | exactly three upper-case ASCII letters |
| `updated_at` | ISO 8601 date and time with an explicit offset (`Z` or `+hh:mm` or `-hh:mm`), a real moment; fractional seconds are allowed; a timestamp without an offset is not |
| `discount_pct` | optional; a whole number from 0 to 90 (not a boolean, not text) |
| anything else | unknown fields are ignored; an item that is not an object is invalid |

Digits means the ASCII digits 0-9 everywhere. An invalid item does not stop the run: it is **set aside** (see `rejects.jsonl`) and counted.

## What `sync_feed(client, out_dir, ...)` must do

1. **Request and decode.** Use the given `httpx.Client` (it already has its base URL and timeouts; do not create another). A usable answer has status 200, content type `application/json` (parameters such as `charset` are fine), a body of at most **1,048,576 bytes**, and decodes to an object whose
   `data` is a list and whose `next` is text or `null`. Anything else raises `FeedError` immediately and is **not** retried; an oversized body gives a message containing `large`.
2. **Retry** only transient failures: `httpx.TransportError` (timeouts, dropped connections) and the statuses in `RETRY_STATUS`. At most `attempts` tries per request. Before the second try wait 0.5 s, then 1, 2, 4, 8 s and 8 s from then on, **or** the server's `Retry-After` (whole seconds or an HTTP date) when that is longer,
   never more than 30 s; ignore a `Retry-After` you cannot read. Use the given `sleep` and never sleep after the last attempt. When the attempts run out raise `FeedError` whose message contains `gave up`. Every other status (including 500 and redirects) raises `FeedError` at once. The backoff starts again for every page.
3. **Deadline.** `deadline_seconds` limits the whole run, measured with the given `clock`. If waiting before the next try would carry the run past the deadline, raise `FeedError` containing `deadline` *instead of sleeping*; do the same if the deadline has already passed when a request is about to be sent.
4. **Pagination safety.** Follow `next`. A relative path is resolved against the URL it came from. The target must have the **same scheme, host and port as the client's base URL**; otherwise raise `FeedError` containing `origin` and send nothing to it. A `next` URL that was already requested raises `FeedError` containing `loop`.
   More than 200 pages raises `FeedError` containing `200` (exactly 200 pages are fine).
5. **Validate and reduce.** Count every item seen. Set aside invalid ones. When several items have the same `sku`, keep the one with the latest `updated_at` (compared as moments, not as text; on equal moments the later item in the feed wins) and count each dropped item in `duplicates_dropped`.
6. **Reject limit.** If **more than 20 %** of the items seen were invalid, raise `RejectThresholdExceeded(rejected, items_seen)` and write nothing.
7. **Write.** Create `out_dir` if needed and write three files, each replaced atomically (temporary file, then `os.replace`; no temporary file may remain), in this order, **`prices.json` last**:
   - `rejects.jsonl`: one JSON object per line, UTF-8: `{"page": 1-based page number, "index": 0-based position on that page, "errors": non-empty text saying what was wrong, "item": the item exactly as received}`. An empty file when nothing was rejected.
   - `summary.json`: the fields of `Summary` as an object.
   - `prices.json`: a JSON list of `{"sku", "price", "currency", "updated_at", "discount_pct"}` sorted by `sku` (plain text order), `price` still text, `updated_at` converted to UTC and written with a trailing `Z`, `discount_pct` `null` when absent.
8. **Failure means no change.** If any of the above raises, the files that were in `out_dir` before the call are exactly as they were (`prices.json` is the commit point: it is replaced last and only after the other two succeeded).

`Summary` fields: `pages` (read successfully), `requests` (HTTP requests sent, retries included), `retries` (waits followed by another try), `items_seen`, `accepted` (distinct SKUs written), `duplicates_dropped`, `rejected`.

## Setup and running the checks

```bash
cd courses/python-engineering/modules/PY-M05/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs the published checks against starter/feedsync.py - they fail until you have written sync_feed
```

The checks use a fake clock and a fake `sleep`, so retries do not make them slow; real timeouts are used only where a test needs a slow server (a fraction of a second).

## What you hand in

1. `starter/feedsync.py`.
2. `notes.md`, one page: the order in which you made checks pass; the failure you consider most dangerous for a production job and what your code does about it; which rules of the specification you tested **yourself** beyond the published checks (and how); what your tests and the published checks do **not** prove.

## How it is graded

Two automated criteria are must-pass: the published checks, and the hidden suite (see the rubric for the threshold). A reviewer scores code clarity and error handling, and the honesty of `notes.md`, from 0 to 3 each. Finishing the lab without meeting the pass rule is not a completion claim.
