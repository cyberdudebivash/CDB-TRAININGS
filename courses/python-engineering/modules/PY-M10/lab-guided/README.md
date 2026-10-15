# PY-M10 guided lab - A ticket API that says no for the right reasons

**Time:** about 4.5 hours  |  **Outcomes:** LO1-LO6  |  **Needs:** Python 3.11+ and the packages of `../../../labs/requirements.txt` (pytest, FastAPI, Starlette, httpx2, PyJWT, mypy, ruff). No network, no account, no paid service, **no open port**: every check calls the service in-process through Starlette's `TestClient`.

`starter/ticketapi.py` is a support-ticket service: readers open and follow their own tickets, agents work every ticket, admins may also delete. Callers present a bearer token (a signed JWT; in a real deployment an identity provider issues it, here `issue_token` plays that role). The starter has the shape of the finished service and every `raise NotImplementedError` is a part for you to write; the docstring above it is the specification and `checks/` holds the tests. You also get the parts that are plumbing rather than the lesson: the output models, the table definition, the error class, the bearer scheme and the wiring of `create_app`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M10/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - nearly everything fails at first
```

Edit only `starter/ticketapi.py`. Run one step with `python -m pytest checks/test_step03_repository.py` (steps `01_settings_and_tokens`, `02_models`, `03_repository`, `04_errors`, `05_auth`, `06_endpoints`, `07_hardening`, `08_injection`, `09_operations`, `10_quality`). `LAB_TARGET=solution python -m pytest` checks the public reference; read `solution/ticketapi.py` only after a step is green, and compare. A step you have not written is reported as a failed check, never as an error in the test set-up.

A few checks pass on the starter on purpose: they describe things the starter already does (types it declares, helpers it gives you). Do not trust a green check you did not turn green.

## Step 1 - Settings that fail closed, tokens checked by what they claim (LO2)

Write `Settings.__post_init__` and `Settings.from_env`, then `issue_token` and `verify_token`. The settings refuse a weak secret (fewer than 32 characters, or fewer than 12 different ones), a bad `token_ttl` and a bad `max_body`, and **never repeat the secret in a message**. `from_env` reads a mapping you pass in (so a test never touches the real environment) and refuses to start without `TICKETAPI_SECRET` and `TICKETAPI_DB`; it has no default secret, ever.

`verify_token` is where most real services go wrong. Read its docstring slowly: HS256 only (checked on the header *before* the library sees the token), no header that points at or carries a key, issuer and audience equal to the settings, the required claims present and whole numbers, an expiry at the exact second, an issue time at most 30 seconds in the future, a lifetime of at most an hour, a known role, a subject that is a plain name. Time comes from `settings.clock`, never from the machine, which is also what makes it testable.

In `notes.md`: why does `alg: none` need a check of its own when the library is told which algorithms to accept? What would an attacker gain from a `jku` header?

## Step 2 - Models: what the service accepts (LO1)

`TicketIn`, `TicketPatch` and `ListParams` start as bare lists of fields. Add the configuration and limits their docstrings describe: unknown fields refused, nothing coerced for a request body, text stripped and length-limited, control characters refused (but not tab, newline and carriage return in a body), text that cannot be stored refused, every anchored pattern. Write `_clean` and `TicketPatch.changes`.

Two traps are in this step on purpose. pydantic's `pattern` is a **search**, not a full match: `^...$` is yours to write. And a query string has no types, so `ListParams` must accept `"5"` where `TicketIn` must refuse `"5"`.

In `notes.md`: which of the models' limits protect the database, which protect the client, and which protect the service from a flood?

## Step 3 - The repository (LO4)

Write `TicketRepo.init`, `create`, `get`, `search`, `update`, `delete` and `_like`. Every value travels as a `?` parameter; the only text that becomes part of a statement is chosen by your code from a fixed table (`SORT_COLUMNS`, `ORDERS`, `UPDATABLE`). `get(..., requester=...)` puts the ownership rule **in the query**, so there is no code path that forgets it. `update(..., only_status=...)` makes the "still in this status" rule part of the same statement, so two requests cannot both pass a check made earlier. Every method opens, uses and closes its own connection: requests run in a thread pool and a connection must not be shared across threads.

In `notes.md`: the search text `100%` matches only `100%`. Which two lines make that true, and what would `%` alone return without them?

## Step 4 - Errors (LO5)

Write `request_id_of`, `problem` (an `application/problem+json` response, RFC 9457, with the request id and the security headers on every one), `_loc_part`, `field_errors`, `allowed_methods`, and the three handlers `_validation_error`, `_http_error`, `_unexpected`. FastAPI's default 422 **echoes the input it rejected**; yours says where and what kind, never what. A name the client typed is reported only when it is a plain identifier. A 405 lists the methods the path really has (Starlette's own header stops at the first route that matches). The `title` of each problem comes from `TITLES`, not from `http.HTTPStatus`, which renamed 413 and 422 in Python 3.13.

In `notes.md`: why is the 500 answer deliberately poor in information, and where does the information go instead?

## Step 5 - Who is calling, and what may they do (LO2, LO3)

Write `_unauthorised`, `current_principal`, `_visible` and `check_patch`. Three levels: **object** (a reader asking for another reader's ticket gets the same 404 as for a ticket that does not exist - never a 403), **function** (only an admin deletes, and the role is checked before the lookup so a missing ticket is not revealed), **field** (a reader edits only title, body and priority, only while the ticket is open; status moves only along `TRANSITIONS`; a closed ticket changes for nobody; a field sent as null is refused). The checks test the order of the rules, because the order decides what an attacker learns.

Every authentication failure gets the *same* answer; the reason goes to the audit log only. Neither a token nor the secret may ever reach a log line.

In `notes.md`: name one thing a 403 would tell an attacker that the 404 does not.

## Step 6 - The endpoints and the contract (LO1, LO3, LO5)

Write the five route bodies (`create_ticket`, `list_tickets`, `read_ticket`, `patch_ticket`, `delete_ticket`) and `_canonical_id`. The decorators, status codes, response models and documented errors are given: they are the contract, and the checks compare them with the OpenAPI description the application produces.

| Route | Does |
|---|---|
| `POST /tickets` | stores a ticket for **the caller** (never for the name in the body), answers 201 with the ticket and a `Location` header, audits `ticket.created` |
| `GET /tickets` | a reader sees their own tickets (asking for another `requester` is a 403); staff see all and may filter by `requester`; filters, sort, order, `limit`, `offset`; answers a `Page` |
| `GET /tickets/{id}` | one ticket through the object-level rule of step 5 |
| `PATCH /tickets/{id}` | refuses an empty patch (400), looks the ticket up through the object-level rule, applies `check_patch`, updates conditionally on the status it just read (409 `conflict` if it changed meanwhile), audits `ticket.updated` with the **names** of the fields |
| `DELETE /tickets/{id}` | admin only; 204 with no body; audits `ticket.deleted` |

Ids in a path are accepted only in their plain decimal form: `/tickets/01`, `/tickets/+1`, `/tickets/1_0` and `/tickets/1.0` all mean "1" to a lenient integer parser, which gives one ticket many addresses (and a cache, a log search or a rate limit keyed by path sees many tickets).

In `notes.md`: which of the five routes would you most want to rate-limit, and where (in this code or in front of it) would you do it?

## Step 7 - Hardening at the edge (LO6)

Write `pick_request_id` and `Guard._refusal`; `Guard` itself (a pure ASGI middleware, outermost layer) is given. A client's `X-Request-ID` is kept only if it is 1 to 64 of `A-Z a-z 0-9 . _ -` and was sent once - otherwise it is **replaced**, never cleaned up (what is left of a hostile string is still hostile). A declared body larger than `max_body` is a 413 before the application reads one byte, a `Content-Length` that is not plain digits or is sent twice is a 400, and a body with no length at all is a 411. Every response carries the request id and four security headers, replacing whatever the application set for them.

In `notes.md`: why does this limit look at `Content-Length` and not count bytes as they arrive, and what in front of the service should enforce the second?

## Step 8 - The injection and abuse suite (LO4, LO5)

Nothing to write: run it. `checks/test_step08_injection.py` throws about seventy hostile strings (SQL, markup, template, shell, path, header, Unicode, numbers) at **every** place a client can put data - body fields and field names, query values and names, path segments, request id, token claims, the authorization header - and at JSON that is malformed, enormous, nested or odd. After each, four things must hold: no 5xx, no database or framework text in an error, the table and its rows intact, and nobody sees a ticket that is not theirs.

Then add three payloads of your own to the corpus (`CORPUS` at the top of that file - the one place in this lab where you edit a check), run the suite, and write down in `notes.md` what each tests and what the service did. The suite is yours to keep: when you add a field or a parameter to a real service, add it here first.

## Step 9 - Operations (LO6)

Write `app_from_env`. The checks read the audit trail (events, actors, request ids; **never** the text of a ticket, a token or the secret), the readiness probe (503 until the lifespan has started and again after it stops), and the independence of two applications.

In `notes.md`: what would you alert on, from these audit events, in the first week of running this service?

## Step 10 - Typed and clean (LO6)

Nothing new to write; the checks run `mypy --strict` and `ruff` with the security rules (`S`) on your file and refuse blanket `# noqa` and unexplained `# type: ignore`. Linters flag f-string SQL (`S608`); two statements in the reference are built from constants and carry a reasoned `noqa`. If you find yourself adding one, ask whether a value, not a constant, is reaching the statement.

## When you are done

All checks pass and `notes.md` has your answers. Read `solution/ticketapi.py` and compare the three places where you and the reference differ most; the independent lab (`../lab-independent`) asks you to build a different API from a specification, with a hidden suite that tries to break it.

## What the checks do not tell you

They test behaviour, structure and a corpus of known attacks, not whether the design suits your organisation, not performance under load, not transport security (TLS belongs to what runs in front of the service), not rate limiting, and not secret management in a real deployment (a secret in an environment variable is the minimum, not the goal). A passing run is an automated check, not a security review, and the module has not been reviewed by a subject-matter expert or piloted with learners.
