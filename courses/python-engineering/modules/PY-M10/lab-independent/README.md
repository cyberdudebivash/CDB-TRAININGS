# PY-M10 independent lab - An asset inventory API for several customers

**Time:** about 3 hours  |  **Outcomes:** LO1-LO6  |  **Needs:** Python 3.11+ and the packages of `../../../labs/requirements.txt`; no network, account, paid service or open port. **Prerequisite:** the lesson and the guided lab (you may reuse anything you built there).

A security team keeps an inventory of the hosts of several customers ("tenants"). You build the HTTP service from the specification below. `starter/inventory.py` gives you the three names the tests call (`Settings`, `KeyStore`, `create_app`) and nothing else; the design is yours. Ten published checks (sixteen test cases; `python -m pytest`) show the shape of the answers; an instructors' suite of several hundred checks, which you do not have, tests every sentence of this specification, hostile input, concurrency and the order of the rules. **A service that passes only the published checks is not finished.**

## Setup

```bash
cd courses/python-engineering/modules/PY-M10/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/inventory.py - all fail at first
```

Edit `starter/inventory.py` (standard library, FastAPI, Starlette and pydantic only) and add `notes.md`.

## The interface the tests call

```text
Settings(db_path, rate_limit=60, max_body=8192, clock=time.time)   # SettingsError (a ValueError) for: empty db_path; rate_limit or max_body that is not an int (a bool is not) from 1 to 10000 / 1 to 1000000
KeyStore().add(key_id, secret, tenant, scope)                      # ValueError for a bad value or a key id already registered
KeyStore().check(key_id, secret) -> (tenant, scope) | None
create_app(settings, keys) -> FastAPI                              # a ready application; the table is created when it is built
```

`key_id` is `[a-z0-9]{8,32}`, `secret` is `[A-Za-z0-9_-]{24,128}`, `tenant` is `[a-z0-9-]{1,32}`, `scope` is `read` or `write` (`write` also reads). The key store keeps **only a hash** of each secret, compares in constant time, and does the same work for an unknown key id as for a wrong secret. `clock` returns seconds since the epoch and is the only source of time (rate limit windows, timestamps).

## The service

A caller sends `X-API-Key: <key id>.<secret>`, exactly once. A missing, malformed or wrong key is **one and the same** `401` (with `WWW-Authenticate: ApiKey realm="inventory"`). Every other rule below applies in this order: authentication (401) - rate limit (429) - scope (403) - validation (422) - existence and preconditions (404, 412). Only requests with a valid key count against the rate limit.

| Method and path | Scope | Does |
|---|---|---|
| `GET /healthz` | none | `{"status": "ok"}`; no key, no rate limit |
| `PUT /assets/{hostname}` | write | create or replace; **idempotent** |
| `GET /assets/{hostname}` | read | one asset |
| `GET /assets` | read | list with filters and a cursor |
| `DELETE /assets/{hostname}` | write | delete; 204, no body |

**Tenants.** Every asset belongs to the tenant of the key that wrote it. A key sees, changes and deletes only its own tenant's assets; another tenant's asset is a `404`, with exactly the answer of an asset that does not exist (no `ETag`, no hint). The same hostname may exist in two tenants as two different assets.

**Hostnames** (the path segment, in its one canonical spelling): lower-case letters, digits, hyphen and dot; 1 to 253 characters; labels of 1 to 63 characters that begin and end with a letter or digit; no leading, trailing or doubled dot; and the **last label is not all digits** (so `10.0.0.1` is not a hostname). Anything else is `422`.

**The body of a PUT** is a JSON object with exactly: `address` (a string: an IPv4 or IPv6 address in plain text - no scope id `%`, no surrounding space, no IPv4-mapped IPv6, not unspecified, not multicast; stored and returned in canonical form, so `2001:DB8:0::1` becomes `2001:db8::1`), `criticality` (a whole number 1 to 5; `"3"`, `3.0` and `true` are refused), and optionally `tags` (up to 10 *different* strings of `[a-z0-9][a-z0-9:_-]{0,31}`; stored and returned sorted; default empty). Unknown fields, wrong types and every other content type are `422`.

**An asset** is returned as `{hostname, address, criticality, tags, version, created_at, updated_at}`; times are UTC ISO-8601 with `Z`; `version` starts at 1.

**PUT is idempotent.** The body replaces the whole asset. First PUT: `201`, `Location: /assets/{hostname}`, `ETag: "1"`. A PUT whose canonical content equals the stored one changes **nothing** (same `version`, same `updated_at`) and answers `200` with the same `ETag`. Any other PUT answers `200`, increases `version` by one, sets `updated_at` and keeps `created_at`. `ETag` is the version in double quotes.

**Preconditions on PUT.** `If-Match: "<version>"` or `If-Match: *`: the write happens only if the asset exists and (for a version) has that version; otherwise `412 precondition_failed`, nothing changes, and - only when the caller's own asset exists - the response carries its current `ETag`. `If-None-Match: *` makes the PUT create-only: if the asset exists (even with identical content) the answer is `412`. Any other form (a weak `W/"1"`, an unquoted number, a list, `If-None-Match: "1"`, both headers together, the same header twice) is `400 bad_precondition`. The check and the write are **one atomic step**: of twelve concurrent writers with the same `If-Match`, exactly one wins.

**GET of one asset** answers `200` with an `ETag`; `If-None-Match` equal to the current `ETag` (or `*`) answers `304` with no body and the `ETag`.

**The list** is ordered by hostname and answers `{"items": [...], "next_cursor": string | null}`. Parameters (anything else is `422`): `limit` 1 to 100 (default 25); `cursor`; `tag` (one tag; matches whole tags); `min_criticality` 1 to 5; `network` (CIDR text such as `10.0.0.0/24` or `2001:db8::/32`, host bits zero, refuses `10.0.0.5`, `10.0.0.1/24` and anything with `%`; an asset matches when its address lies inside the network, edges included, and IPv4 networks never match IPv6 addresses). Filters combine with AND. The cursor is opaque URL-safe text that marks the last item of the page; the next page starts after it, so inserts and deletes between two requests neither repeat nor skip items that were already there. `next_cursor` is `null` exactly when there is nothing more. A cursor that is not one the service would issue (bad text, bad characters, not decodable to a hostname) is `422`; a cursor never gives access to another tenant's data.

**Rate limit.** At most `rate_limit` valid-key requests per key in each fixed window of 60 seconds aligned to the clock (window = `floor(now / 60)`). Request number `rate_limit + 1` and later in the window: `429 rate_limited` with `Retry-After` (whole seconds until the window ends, rounded up, at least 1). The next window starts at zero. Counters of past windows are forgotten. The limit must hold when requests arrive concurrently.

**Errors.** Every failure is `application/problem+json` with `type` (`about:blank`), `title`, `status`, `code`, `detail`, `request_id` (and for a 422, `errors`: a list of `{loc, code}` - where and what kind, never the value; a field *name* appears only if it is a plain identifier - `[A-Za-z0-9_]{1,40}` - otherwise `?`). Codes: `unauthorised` 401, `forbidden` 403, `not_found` 404, `method_not_allowed` 405 (with the right `Allow`), `precondition_failed` 412, `bad_precondition` 400, `validation_error` 422, `rate_limited` 429, `body_too_large` 413, `length_required` 411, `bad_content_length` 400, `internal_error` 500 (generic: no detail, no exception text). The `title` is written out, not taken from `http.HTTPStatus` (its wording changed between Python releases): 400 `Bad Request`, 401 `Unauthorized`, 403 `Forbidden`, 404 `Not Found`, 405 `Method Not Allowed`, 411 `Length Required`, 412 `Precondition Failed`, 413 `Content Too Large`, 422 `Unprocessable Content`, 429 `Too Many Requests`, 500 `Internal Server Error`.

**The edge.** Reuse your guided-lab work: every response carries `X-Request-ID` (the client's if it is 1 to 64 of `A-Za-z0-9._-` and was sent once, else a fresh 32-character hex id) and the four security headers (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`); a declared body larger than `max_body` is `413` before it is read; a `Content-Length` that is not plain digits or is sent twice is `400`; a body with no length is `411`; no trailing-slash redirects, no interactive docs, no schema served.

**Audit.** Logger `inventory.audit`, one record per event with attributes `event`, `tenant`, `key` (the key **id**), `hostname` and `request_id`: `asset.created`, `asset.replaced`, `asset.unchanged`, `asset.deleted`, `auth.refused` (a `reason`, never the key), `rate.limited`. Never the secret, the key header, an address, a tag or any other content.

**Quality.** `mypy --strict` and `ruff` (rules `F,E,W,B,S,UP,SIM`, line length 200) are clean; no blanket `noqa`; no secret in the source.

## What you hand in

1. `starter/inventory.py`.
2. `notes.md` (one page): a threat table - for each of the ten risks below, the sentence of your design that handles it and the check (yours or a published one) that would notice if someone removed it: cross-tenant read, cross-tenant write, SQL injection through a filter, key guessing, key enumeration by timing or message, lost update, replay of a create, cursor tampering, request flood, secret in a log.

## Hints that are not solutions

- A key that is stored as a hash can still be compared wrongly. Compare the hashes, with a constant-time function, for every key id including unknown ones.
- "Check, then write" is two requests' worth of time. One `BEGIN IMMEDIATE` transaction is one.
- A network filter is a range. Think about how to store an IPv6 address so that "inside the network" is a range query in SQL (and why a Python loop over all rows is wrong when the page must be full).
- The window of a rate limit is a number you can compute from the clock; the dictionary of counters does not have to remember the past.
