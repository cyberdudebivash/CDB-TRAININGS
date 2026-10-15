---
id: PY-M10
title: "API development: typed, tested and secure HTTP services"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M02 (functions, errors and pytest), PY-M03 (types) and PY-M07 (secure coding), and ideally PY-M08 (databases), and now have to build an HTTP service that other people's software will call: validate every input, authenticate callers, decide what each caller may do, keep hostile input away from the database, describe the contract, and run it."
prerequisites:
  - "PY-M02, PY-M03 and PY-M07; PY-M08 (parameterised SQL, transactions) and PY-M05 (HTTP clients) help"
  - "Python 3.11 or newer; the labs and every code block of this lesson were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "fastapi 0.143.1, starlette 1.8.0, pydantic 2.14.1, PyJWT 2.15.1, httpx2 2.13.1, pytest 9.1.1, mypy 2.4.0 and ruff 0.17.0 from labs/requirements.txt; no network, no account, no paid service, no open port"
estimated_time_hours: {lesson: 2.5, guided_lab: 4.5, independent_lab: 3.0, total: 10.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); behaviour of http.HTTPStatus, datetime.utcnow and integer parsing by version executed in this lesson (R-100)", fastapi: "0.143.1", starlette: "1.8.0", pydantic: "2.14.1", pyjwt: "2.15.1", httpx2: "2.13.1"}
last_verified: 2026-10-15
---

# PY-M10 - API development: typed, tested and secure HTTP services

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Validate every input of an HTTP API with types and limits (body, query, path, headers): refuse unknown fields, refuse coercion where a body is concerned, anchor patterns, and know which defaults of the framework echo input back or accept more than you meant. |
| **LO2** | Authenticate callers with a signed token or an API key: pin the algorithm, check issuer, audience, expiry and issue time against an injectable clock, compare secrets in constant time, give every failure the same answer and keep the reason in the audit log. |
| **LO3** | Authorise at three levels - the object (ownership enforced in the query), the function (role before lookup) and the field (who may change what, in which state) - and choose between 403 and 404 for what an attacker should not learn. |
| **LO4** | Keep data and statements apart (bound parameters, fixed tables for names and directions, escaped wildcards) and keep client text out of paths, headers and logs; prove it with an injection suite. |
| **LO5** | State the contract (OpenAPI, problem details, status codes, headers) and test it: contract tests, negative tests, and a corpus of hostile input that runs on every change. |
| **LO6** | Operate the service: configuration that fails closed, request ids, an audit trail without secrets or content, readiness and liveness, body limits and security headers at the edge, and code that is typed (`mypy --strict`) and lint-clean. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

An API is a promise made to software you do not control. The caller may be a browser, a script, a partner's server, a scanner or an attacker, and your service cannot tell them apart except by what they send. Everything outside the function body is therefore security-relevant: what the framework does with a malformed body, how long a token stays valid, which of two nearly identical addresses reaches a record, what an error message repeats.

The 2025 handbook builds web services in its third module (PDF pages 215 to 311): a Flask contact system and a SaaS back end in FastAPI with JWT. It is a lively introduction to the moving parts, and it teaches several patterns that fail in production. Each finding below was read in the page text and is demonstrated, not asserted, later in this lesson:

- the task API (pages 259 and 260) has four routes - create, read all, update, delete - and **none of them authenticates or validates anything**; an update or delete of an id that does not exist fails with an exception (an HTTP 500), not a 404;
- secrets are literals in the source: the token secret `"CYBERDUDEBIVASH_SECRET"` (page 269), the Flask session key `"DUDExBIVASH"` (page 274), a database URL with a user name and password (page 268), an admin seeded with `password123` (page 252), and `app.run(debug=True)` in the first application (pages 222 and 228);
- `create_token` (page 270) builds the expiry with `datetime.utcnow()`, which is deprecated since Python 3.12, and **changes the dictionary it is given**; the refresh token (page 290) is signed with the same secret and has the same claims as an access token, so nothing says which is which;
- the upload route (page 258) saves a file under the **name the client chose**; the search route (page 261) passes the raw query parameter to `contains()`;
- the page of security reminders (281) lists "SQL injection protection", "CSRF protection" and "validate all request inputs" as bullets, with no code and no test for any of them;
- the multi-tenant section (pages 284 and 285) declares a `tenant_id` column and a `require_role` helper but shows no query that filters by tenant.

This module replaces the Flask-centred chapter by a service you build and attack: a ticket API (guided lab) and a multi-tenant asset inventory (independent lab), both FastAPI, both tested through the in-process `TestClient`, so **nothing opens a port and nothing leaves your machine**. Flask itself is not taught; its pattern (a blueprint of routes) maps directly to FastAPI's `APIRouter`, and what changes between frameworks is the list of defaults - which this lesson is about.

## 2. A first API, and the defaults that matter (LO1, LO5)

FastAPI turns type hints into validation and documentation. The smallest useful service is a model and a route; the `TestClient` calls it in-process, with no server and no network.

```python run
from typing import Literal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

app = FastAPI()


class NewTicket(BaseModel):
    title: str = Field(min_length=3, max_length=40)
    priority: Literal["low", "high"] = "low"


@app.post("/tickets", status_code=201)
def create(ticket: NewTicket) -> dict[str, str]:
    return {"title": ticket.title, "priority": ticket.priority}


client = TestClient(app)
ok = client.post("/tickets", json={"title": "Printer on fire"})
assert ok.status_code == 201 and ok.json() == {"title": "Printer on fire", "priority": "low"}

bad = client.post("/tickets", json={"title": "Printer", "priority": "my-api-key-1234"})
assert bad.status_code == 422
entry = bad.json()["detail"][0]
assert entry["loc"] == ["body", "priority"] and entry["input"] == "my-api-key-1234"          # the default answer repeats what it rejected
```

The framework did the useful part: the type and the limits were checked, and the client got a 422 that says where. It also did something that is wrong for a service that receives secrets: the answer **contains the rejected value**. A client that sent its API key in the wrong field has just had it echoed into a response, a proxy log and possibly an error tracker. Section 4 replaces the answer; the principle is that **an error says where and what kind, never what**.

Three more defaults are worth knowing before you rely on them. A model accepts and silently drops fields it does not know. A route that raises an exception nobody handled answers 500 with the framework's text in development mode. And documentation pages (`/docs`, `/redoc`, `/openapi.json`) are on unless you turn them off:

```python run
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class Ticket(BaseModel):
    title: str


app = FastAPI()


@app.post("/tickets")
def create(ticket: Ticket) -> dict[str, str]:
    return {"title": ticket.title}


client = TestClient(app)
r = client.post("/tickets", json={"title": "abc", "requester": "someone-else", "is_admin": True})
assert r.status_code == 200                              # unknown fields are dropped without a word, so a client believes they were used
assert client.get("/openapi.json").status_code == 200    # the description of every route is public by default
assert client.get("/docs").status_code == 200

hardened = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
assert TestClient(hardened).get("/openapi.json").status_code == 404
```

A silently dropped `is_admin` is harmless here and a disaster in a handler that does `User(**payload)` - the *mass assignment* of the next sections.

## 3. Validation: types, limits and the traps in both (LO1)

pydantic validates in one of two modes. **Lax** mode (the default) converts what it can; **strict** mode converts nothing. For a JSON body, strict is almost always right: a client that sends `"5"` where a number is expected has a bug, and quiet repair hides it. For a query string it is wrong, because every value in a URL is text.

```python run
from pydantic import BaseModel, ConfigDict, ValidationError


class Lax(BaseModel):
    qty: int
    title: str


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    qty: int
    title: str


assert Lax(qty="5", title="x").qty == 5 and Lax(qty=True, title="x").qty == 1        # "5" and True are quietly turned into integers
for kwargs in ({"qty": "5", "title": "x"}, {"qty": True, "title": "x"}, {"qty": 5, "title": 7}, {"qty": 5, "title": "x", "extra": 1}):
    try:
        Strict(**kwargs)
    except ValidationError as exc:
        assert exc.error_count() == 1
    else:
        raise AssertionError(kwargs)
assert Strict.model_validate_json('{"qty": 5, "title": "x"}').qty == 5
```

The second trap is the regular expression. A `pattern` in pydantic is a **search**, not a full match, so a pattern for "three lower-case letters" accepts `abc!!!`. Anchoring it with `^` and `$` fixes that - and the anchors of pydantic and of Python's `re` module differ in one more detail: Python's `$` also matches just before a final newline.

```python run
import re
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError


class Unanchored(BaseModel):
    code: Annotated[str, Field(pattern=r"[a-z]{3}")]


class Anchored(BaseModel):
    code: Annotated[str, Field(pattern=r"^[a-z]{3}$")]


assert Unanchored(code="abc!!!").code == "abc!!!"            # a search: the first three characters satisfy it
for text in ("abc!!!", "abcd", "ab", "abc\n", " abc"):
    try:
        Anchored(code=text)
    except ValidationError:
        pass
    else:
        raise AssertionError(text)
assert Anchored(code="abc").code == "abc"

assert re.match(r"^[a-z]{3}$", "abc\n")                      # Python's $ accepts a trailing newline ...
assert not re.fullmatch(r"[a-z]{3}", "abc\n")                # ... fullmatch does not. In your own code use fullmatch.
```

The third trap is text that is valid JSON and cannot be stored. JSON allows the escape `\ud800`, a *lone surrogate*; Python happily creates the string, and the first thing that encodes it as UTF-8 raises `UnicodeEncodeError` - in a database driver, a logger or a response, as a 500. Control characters (a NUL, an escape, a line break in a title) are the same family: legal text, illegal in a header, a log line or a file name. Refuse both in the model, where the error is a clean 422:

```python run
import json
import re

from pydantic import BaseModel, ValidationError, field_validator

CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class Title(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def printable_and_storable(cls, value: str) -> str:
        if CONTROL.search(value):
            raise ValueError("control characters")
        value.encode("utf-8")                          # a lone surrogate raises UnicodeEncodeError, a ValueError subclass
        return value


lone = json.loads('{"text": "ab\\ud800cd"}')["text"]
assert lone == "ab\ud800cd"                            # legal JSON, a real Python string ...
try:
    lone.encode("utf-8")
except UnicodeEncodeError:
    pass                                               # ... that cannot be written anywhere
else:
    raise AssertionError("expected an encoding error")
for bad in (lone, "line\nbreak", "nul\x00byte", "esc\x1b[31m"):
    try:
        Title(text=bad)
    except ValidationError:
        pass
    else:
        raise AssertionError(bad)
assert Title(text="café 日本語 😀").text == "café 日本語 😀"
```

Last, **identifiers**. `/tickets/1` is one ticket. If the framework converts the path segment with Python's lenient `int()`, then `/tickets/01`, `/tickets/+1`, `/tickets/1_0` (which is 10!) and `/tickets/%201` also reach tickets - one record with many addresses, and a cache, a log search or a rate limit keyed by path sees many records. Accept only the plain form:

```python run
import re

PLAIN_ID = re.compile(r"[1-9][0-9]{0,9}")
for text, lenient in (("01", 1), ("+1", 1), ("1_0", 10), (" 1 ", 1), ("١٢", 12)):          # the last one is two Arabic-Indic digits
    assert int(text) == lenient
    assert PLAIN_ID.fullmatch(text) is None
assert PLAIN_ID.fullmatch("10") and not PLAIN_ID.fullmatch("0") and not PLAIN_ID.fullmatch("1" * 11)
```

The guided lab (step 6) puts this rule in front of every `{ticket_id}`; the checks request a dozen spellings of "1".

## 4. Errors: one shape, no echo, no internals (LO5)

RFC 9457 defines *problem details* for HTTP APIs: a JSON object with `type`, `title`, `status`, `detail` and any extra members you need, served as `application/problem+json`. One shape for every failure means one parser on the client and one place to audit. Add two members of your own: a machine-readable `code` and the `request_id` (section 9). A validation problem lists `loc` and the kind of error and nothing else.

```python run
import sys
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel

TITLES = {404: "Not Found", 413: "Content Too Large", 422: "Unprocessable Content", 500: "Internal Server Error"}


def problem(status: int, code: str, detail: str, **extra) -> JSONResponse:
    body = {"type": "about:blank", "title": TITLES[status], "status": status, "code": code, "detail": detail, **extra}
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc: RequestValidationError):
    errors = [{"loc": [str(p) if isinstance(p, str) else p for p in e["loc"]], "code": e["type"]} for e in exc.errors()]
    return problem(422, "validation_error", "The request is not valid.", errors=errors)


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    return problem(500, "internal_error", "Something went wrong.")        # the text of `exc` goes to the log, never to the client


class Login(BaseModel):
    pin: int


@app.post("/login")
def login(data: Login) -> dict[str, bool]:
    return {"ok": True}


@app.get("/boom")
def boom():
    raise RuntimeError("password=hunter2 is wrong for /srv/app/db.py")


client = TestClient(app, raise_server_exceptions=False)
r = client.post("/login", json={"pin": "my-secret-pin"})
assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")
assert "my-secret-pin" not in r.text and r.json()["errors"] == [{"loc": ["body", "pin"], "code": "int_parsing"}]
r = client.get("/boom")
assert r.status_code == 500 and "hunter2" not in r.text and r.json()["code"] == "internal_error"

# the standard library's wording is not part of your contract: two statuses were renamed in Python 3.13
expected = ("Request Entity Too Large", "Unprocessable Entity") if sys.version_info < (3, 13) else ("Content Too Large", "Unprocessable Content")
assert (HTTPStatus(413).phrase, HTTPStatus(422).phrase) == expected
assert TITLES[413] == "Content Too Large"
```

The last four lines are a small lesson of their own. `http.HTTPStatus(422).phrase` is "Unprocessable Entity" on Python 3.11 and 3.12 and "Unprocessable Content" from 3.13, because RFC 9110 renamed the status. A service that builds its `title` from the standard library therefore changes its answer when the interpreter is upgraded, and a contract test pinned to one wording fails on another. Write the titles down.

Two smaller points. A **404 for a path that does not exist and a 405 for a method that does not fit** are framework errors, not yours; register a handler for the framework's `HTTPException` too, or they arrive in a different shape. And the 405 must carry an `Allow` header listing the methods the path really has - which Starlette computes from the *first* route with that path, so a path with a GET route and a POST route answers `Allow: POST` to a PUT. The guided lab asks you to recompute it.

## 5. Authentication: who is calling? (LO2)

A bearer token is a signed statement: "this caller is `alice`, a reader, until 12:15". Verification is mostly a list of things to refuse.

The handbook's token code (pages 269 and 270) shows the usual start. Run it, and read the three defects it carries:

```python run
import warnings
from datetime import datetime, timedelta

import jwt

SECRET = "CYBERDUDEBIVASH_SECRET"                    # page 269: a literal in the source
ALGORITHM = "HS256"


def create_token(data: dict, expires=60):
    data.update({"exp": datetime.utcnow() + timedelta(minutes=expires)})             # page 270
    return jwt.encode(data, SECRET, algorithm=ALGORITHM)


def verify_token(token):
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])


claims = {"id": 7}
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    token = create_token(claims)
assert "exp" in claims                                # defect 1: the caller's dictionary was modified
import sys
assert any(w.category is DeprecationWarning for w in caught) == (sys.version_info >= (3, 12))      # defect 2: utcnow() is deprecated from 3.12
assert verify_token(token)["id"] == 7
assert verify_token(create_token({"id": 8}, expires=60 * 24 * 30))["id"] == 8        # defect 3 (page 290): a 30-day token is the same kind of token as a 1-hour one
```

What to do instead, point by point (each one is a check in the guided lab).

**The secret is configuration, not code.** Read it from the environment (or a secret manager) at start-up and refuse to start without a strong one: at least 32 characters, at least 12 different. There is no default, ever; a default is a published password.

**Pin the algorithm - twice.** PyJWT requires the `algorithms` argument and the handbook passes it, which is right. Add your own check of the header's `alg` *before* decoding, so that the answer is a clean "bad algorithm" and not a library exception, and refuse headers that point at or carry a key (`jku`, `jwk`, `x5u`, `x5c`).

```python run
import base64
import hashlib
import hmac
import json

import jwt

KEY = "k" * 40


def b64(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def forge(claims: dict, alg: str = "HS256", key: str = KEY, header: dict | None = None) -> str:
    head = {"alg": alg, "typ": "JWT", **(header or {})}
    signing_input = b64(json.dumps(head).encode()) + b"." + b64(json.dumps(claims).encode())
    digest = {"HS256": hashlib.sha256, "HS512": hashlib.sha512}.get(alg)
    return (signing_input + b"." + (b64(hmac.new(key.encode(), signing_input, digest).digest()) if digest else b"")).decode()


claims = {"sub": "alice", "role": "reader", "exp": 4_000_000_000}
good = forge(claims)
assert jwt.decode(good, KEY, algorithms=["HS256"])["sub"] == "alice"

try:
    jwt.decode(good, KEY)
except jwt.DecodeError as exc:
    assert "algorithms" in str(exc)                                      # the library insists that you say which algorithms you accept
for token in (forge(claims, alg="none"), forge(claims, alg="HS512")):
    try:
        jwt.decode(token, KEY, algorithms=["HS256"])
    except jwt.InvalidAlgorithmError:
        pass
    else:
        raise AssertionError("another algorithm was accepted")
head, payload, signature = good.split(".")
evil_payload = b64(json.dumps({**claims, "role": "admin"}).encode()).decode()
try:
    jwt.decode(f"{head}.{evil_payload}.{signature}", KEY, algorithms=["HS256"])
except jwt.InvalidSignatureError:
    pass
else:
    raise AssertionError("a changed payload was accepted")
assert jwt.get_unverified_header(forge(claims, header={"jku": "https://evil.example/keys.json"}))["jku"].startswith("https://evil")
```

**Time is an input.** `jwt.decode` checks `exp` against the machine's clock, which a test cannot move. Verify the signature with the library, switch its time checks off, and do the arithmetic yourself against a clock you pass in: a token is expired *at* its `exp` second, an issue time more than 30 seconds in the future is refused, a lifetime longer than an hour is refused, and every time claim must be a whole number (a boolean is an integer in Python, and `exp: true` is the year 1970).

```python run
import jwt

KEY = "k" * 40
LEEWAY, MAX_LIFETIME = 30, 3600


def check(token: str, now: float) -> str:
    claims = jwt.decode(token, KEY, algorithms=["HS256"], options={"require": ["exp", "iat"], "verify_exp": False, "verify_iat": False})
    exp, iat = claims["exp"], claims["iat"]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (exp, iat)) or exp <= iat or exp - iat > MAX_LIFETIME:
        return "bad_claims"
    if now >= exp:
        return "expired"
    if iat > now + LEEWAY:
        return "not_yet_valid"
    return "ok"


t0 = 1_791_979_200
token = jwt.encode({"exp": t0 + 900, "iat": t0}, KEY, algorithm="HS256")
assert [check(token, t0 + s) for s in (0, 899, 900, 5000)] == ["ok", "ok", "expired", "expired"]          # no sleeping: the clock is a parameter
assert check(jwt.encode({"exp": t0 + 900, "iat": t0 + 30}, KEY, algorithm="HS256"), t0) == "ok"
assert check(jwt.encode({"exp": t0 + 900, "iat": t0 + 31}, KEY, algorithm="HS256"), t0) == "not_yet_valid"
assert check(jwt.encode({"exp": t0 + 3601, "iat": t0}, KEY, algorithm="HS256"), t0) == "bad_claims"
assert check(jwt.encode({"exp": True, "iat": t0}, KEY, algorithm="HS256"), t0) == "bad_claims"
```

**One kind of token, one purpose.** The handbook's refresh token is the same JWT as its access token. Either put a claim that says what the token is for and demand it in the one place that needs it, or do not issue refresh tokens at all. This module's labs issue short access tokens only: refreshing is the identity provider's job, not the resource server's.

**Every failure gets the same answer.** A missing header, an expired token and a forged signature all produce one 401 with the same body and `WWW-Authenticate: Bearer realm="..."`. The reason (`expired`, `bad_signature`) goes to the audit log. If the answers differ, the difference is an oracle for whoever is probing.

**API keys** (the independent lab) follow the same rules with different mechanics: store only a hash of each secret; compare hashes with `hmac.compare_digest`, which takes the same time wherever the strings differ; and do the same work for an unknown key identifier as for a wrong secret, or the response time tells an attacker which identifiers exist.

```python run
import hashlib
import hmac
import secrets

store = {}


def add(key_id: str, secret: str) -> None:
    store[key_id] = hashlib.sha256(secret.encode()).hexdigest()


DUMMY = hashlib.sha256(secrets.token_bytes(16)).hexdigest()


def check(key_id: str, secret: str) -> bool:
    expected = store.get(key_id, DUMMY)                              # an unknown id still costs one hash and one comparison
    ok = hmac.compare_digest(hashlib.sha256(secret.encode()).hexdigest(), expected)
    return ok and key_id in store


add("acmewrite1", "s" * 24)
assert check("acmewrite1", "s" * 24)
assert not check("acmewrite1", "t" * 24) and not check("nosuchkey1", "s" * 24)
assert "s" * 24 not in repr(store)                                   # nothing in memory (or in a backup) is a usable secret
```

## 6. Authorisation: what may this caller do? (LO3)

Authentication answers "who". Authorisation answers "may they do *this*, to *that*". It fails at three levels, and the OWASP API Security list names all three: *broken object level authorisation* (the caller reaches an object that is not theirs), *broken function level authorisation* (the caller reaches an operation that is not theirs) and *broken object property level authorisation* (the caller changes a field that is not theirs). The handbook's multi-tenant pages (284 and 285) declare a `tenant_id` and a `require_role` helper and show no query that uses the first or a route that calls the second.

**Object level.** The check "is this ticket yours" belongs *in the lookup*, not after it. A function `get_ticket(id)` that returns any ticket and a caller that is supposed to compare the owner is one forgotten comparison from a leak; `get_ticket(id, owner=...)` that cannot return someone else's ticket has no such mistake to make. When the lookup fails, answer **404, not 403**: a 403 says "it exists, it is not yours", and a loop over the ids turns that into a list of every ticket in the system.

```python run
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

TICKETS = {1: {"id": 1, "owner": "alice", "title": "Printer"}, 2: {"id": 2, "owner": "bob", "title": "VPN"}}
app = FastAPI()


def caller(x_user: str = Header()) -> str:                    # stands in for the authentication of section 5
    return x_user


@app.get("/naive/{ticket_id}")
def naive(ticket_id: int, who: str = Depends(caller)):
    ticket = TICKETS.get(ticket_id)
    if ticket is None:
        raise HTTPException(404, "No such ticket.")
    return ticket                                               # authenticated - and nobody asks whose ticket it is


def lookup(ticket_id: int, owner: str):
    ticket = TICKETS.get(ticket_id)
    return ticket if ticket and ticket["owner"] == owner else None          # a foreign ticket and a missing one are the same result


@app.get("/scoped/{ticket_id}")
def scoped(ticket_id: int, who: str = Depends(caller)):
    ticket = lookup(ticket_id, who)
    if ticket is None:
        raise HTTPException(404, "No such ticket.")
    return ticket


@app.get("/leaky/{ticket_id}")
def leaky(ticket_id: int, who: str = Depends(caller)):
    ticket = TICKETS.get(ticket_id)
    if ticket is None:
        raise HTTPException(404, "No such ticket.")
    if ticket["owner"] != who:
        raise HTTPException(403, "Not yours.")
    return ticket


client = TestClient(app)
bob = {"x-user": "bob"}
assert client.get("/naive/1", headers=bob).json()["title"] == "Printer"           # bob reads alice's ticket
assert client.get("/scoped/1", headers=bob).status_code == 404
assert client.get("/scoped/1", headers=bob).json() == client.get("/scoped/99", headers=bob).json()          # foreign and missing look alike
codes = {i: client.get(f"/leaky/{i}", headers=bob).status_code for i in range(1, 6)}
assert codes == {1: 403, 2: 200, 3: 404, 4: 404, 5: 404}            # the 403 marks exactly the ids that exist: an enumeration oracle
```

**Function level.** Some operations are for some roles only. Decide the role *before* the lookup, so that a missing ticket is not revealed to a caller who could not have deleted it anyway: an agent who asks to delete ticket 9999 gets "forbidden", the same as for ticket 1.

**Field level.** The same operation may change some fields for some callers in some states. This is where tables beat conditions: a transition table says which status may follow which, one function applies it, and one test walks every pair.

```python run
TRANSITIONS = {
    "open": {"pending", "resolved", "closed"},
    "pending": {"open", "resolved", "closed"},
    "resolved": {"open", "closed"},
    "closed": set(),
}
STAFF_ONLY = {"status", "assignee"}


def check_patch(role: str, status: str, changes: dict) -> str | None:
    """None if the change is allowed, otherwise the reason. The order of the rules decides what a caller learns."""
    if any(value is None for value in changes.values()):
        return "null_not_allowed"
    if status == "closed":
        return "ticket_closed"                                           # nobody edits a closed ticket, not even an admin
    if role == "reader":
        if STAFF_ONLY & set(changes):
            return "forbidden"                                           # a reader asking for a staff field is refused whole, never partly applied
        if status != "open":
            return "ticket_not_open"
    new = changes.get("status")
    if new is not None and new != status and new not in TRANSITIONS[status]:
        return "invalid_transition"
    return None


assert check_patch("reader", "open", {"title": "New title"}) is None
assert check_patch("reader", "open", {"title": "New title", "status": "resolved"}) == "forbidden"
assert check_patch("reader", "pending", {"title": "Late"}) == "ticket_not_open"
assert check_patch("agent", "resolved", {"status": "pending"}) == "invalid_transition"
assert check_patch("admin", "closed", {"title": "Reopen by edit"}) == "ticket_closed"
assert check_patch("agent", "open", {"assignee": None}) == "null_not_allowed"
```

A table-driven rule needs a test that does **not** compute its expectation from the table: if the test derives the allowed pairs from `TRANSITIONS`, a wrong entry in the table passes. Write the expected set out.

```python run
TRANSITIONS = {"open": {"pending", "resolved", "closed"}, "pending": {"open", "resolved", "closed"}, "resolved": {"open", "closed"}, "closed": set()}


def allowed(old: str, new: str) -> bool:
    return old != "closed" and (new == old or new in TRANSITIONS[old])


expected = {("open", "open"), ("open", "pending"), ("open", "resolved"), ("open", "closed"), ("pending", "open"), ("pending", "pending"), ("pending", "resolved"), ("pending", "closed"),
            ("resolved", "open"), ("resolved", "resolved"), ("resolved", "closed")}
assert {(a, b) for a in TRANSITIONS for b in TRANSITIONS if allowed(a, b)} == expected          # 11 pairs, written out, so that a change to the table must change the test
```

**Mass assignment** is the field-level failure at its simplest: the handler copies what the client sent into the object (`User(**payload)`, `task.update(**data)`). The defence is the model of section 3: a body model with `extra="forbid"` lists the fields a client may send, and the repository's update takes only names from a fixed tuple. The client's `requester`, `status` or `is_admin` are then a 422, not a quiet success.

## 7. Injection and abuse: keeping data away from code (LO4)

An injection is client text that reaches an interpreter - SQL, a shell, a template, a file system path, a log reader - as *instructions*. The rule is the same everywhere: **client text is a value, and values travel in the channel made for values**.

**SQL.** Build a statement by pasting text into it and the client writes part of the statement; bind the value instead and it cannot. Two limits catch learners who think binding solves everything: only *values* can be bound (a column name or a sort direction cannot), and `LIKE` has wildcards of its own.

```python run
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, owner TEXT, title TEXT)")
conn.executemany("INSERT INTO t (owner, title) VALUES (?, ?)", [("alice", "Disk 100% full"), ("alice", "a_b"), ("bob", "secret of bob"), ("bob", "x")])


def naive(owner: str):
    return conn.execute(f"SELECT title FROM t WHERE owner = '{owner}' ORDER BY id").fetchall()          # the client chooses part of the statement


def bound(owner: str):
    return conn.execute("SELECT title FROM t WHERE owner = ? ORDER BY id", (owner,)).fetchall()


evil = "nobody' OR '1'='1"
assert len(naive(evil)) == 4 and bound(evil) == []                          # the first returns every row of every owner

# a sort direction is not a value: binding it does nothing, so it must come from a fixed table
assert [r[0] for r in conn.execute("SELECT id FROM t ORDER BY ?", ("id DESC",))] == [1, 2, 3, 4]
SORT = {"id": "id", "title": "title"}
DIRECTION = {"asc": "ASC", "desc": "DESC"}


def ordered(column: str, direction: str):
    sql = f"SELECT id FROM t ORDER BY {SORT[column]} {DIRECTION[direction]}"          # KeyError, not injection, for anything else
    return [r[0] for r in conn.execute(sql)]


assert ordered("id", "desc") == [4, 3, 2, 1]
for column, direction in (("id; DROP TABLE t", "asc"), ("id", "desc, id")):
    try:
        ordered(column, direction)
    except KeyError:
        pass
    else:
        raise AssertionError((column, direction))

# LIKE has wildcards: a search for "%" must find a literal percent sign, not every row
assert len(conn.execute("SELECT title FROM t WHERE title LIKE ?", ("%%%",)).fetchall()) == 4


def like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


rows = conn.execute("SELECT title FROM t WHERE title LIKE ? ESCAPE '\\'", (like("%"),)).fetchall()
assert rows == [("Disk 100% full",)]
assert conn.execute("SELECT title FROM t WHERE title LIKE ? ESCAPE '\\'", (like("_"),)).fetchall() == [("a_b",)]
```

Better: put the *ownership* in the statement as well - `WHERE id = ? AND owner = ?` - so that the object-level rule of section 6 cannot be forgotten by a caller of the repository.

**File names and paths.** The handbook's upload route saves a file under `file.filename` (page 258). The name is the client's. `os.path.join(base, name)` returns `name` alone when it is absolute, and a `..` walks out of the folder:

```python run
import os
import tempfile
import uuid
from pathlib import Path

base = Path(tempfile.mkdtemp())
assert os.name != "posix" or os.path.join(base, "/etc/passwd") == "/etc/passwd"          # an absolute second part discards the first
target = (base / "../escaped.txt").resolve()
assert not target.is_relative_to(base.resolve())                                         # '..' leaves the folder


def storage_path(extension: str) -> Path:
    name = f"{uuid.uuid4().hex}{extension if extension in {'.png', '.jpg'} else ''}"      # the server chooses the name; the client only supplies a kind
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("outside the upload folder")
    return path


assert storage_path(".png").parent == base.resolve() and storage_path("../../x").name.count(".") == 0
```

**Logs and headers.** Text with a line break in it forges log lines (`"bad\nINFO ticket deleted by admin"` becomes two records), and in a response header it splits the response. Never copy client text into either; log identifiers you generated or validated, and when you must echo something, **replace** it - a cleaned version of a hostile string is still the client's string.

```python run
import io
import logging
import re

stream = io.StringIO()
handler = logging.StreamHandler(stream)
handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
log = logging.getLogger("lesson.injection")
log.setLevel(logging.INFO)
log.addHandler(handler)

client_text = "alice\nINFO ticket 7 deleted by admin"
log.info("login failed for %s", client_text)                          # one event, two lines in the file: a forged record
assert stream.getvalue().count("\n") == 2
stream.truncate(0)
stream.seek(0)
log.info("login failed for %r", client_text)                          # repr escapes the newline
assert stream.getvalue().count("\n") == 1

REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def request_id(supplied: str | None) -> str:
    import uuid
    return supplied if supplied is not None and REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex


assert request_id("abc-123") == "abc-123"
assert re.fullmatch(r"[0-9a-f]{32}", request_id("abc\r\nSet-Cookie: x=1")) and re.fullmatch(r"[0-9a-f]{32}", request_id(None))
```

**Hostile structure.** Valid JSON can still be an attack on the parser: a hundred thousand opening brackets, a number with four hundred digits, the same key twice. The parser's recursion limit protects the process, but the exception must become a 4xx and the size of the body must be limited **before** it is read - at the proxy, and again in the application from the declared `Content-Length`, as the guided lab does.

```python run
import json

try:
    json.loads("[" * 100_000)
except RecursionError:
    pass                                   # an exception, not a crash: the service must turn it into a 4xx instead of a 500
else:
    raise AssertionError("expected a RecursionError")
assert json.loads('{"a": 1, "a": 2}') == {"a": 2}                           # the last duplicate wins, silently: validate the result, not the text
assert len(str(json.loads("9" * 400))) == 400                                # Python integers have no upper bound; bound them in the model
```

## 8. The contract, and tests that hold it (LO5)

FastAPI generates an OpenAPI description from your routes and models. That description is not documentation to be admired; it is the **contract**, and what is documented and not enforced (or enforced and not documented) is a defect. A contract test builds the application, reads `app.openapi()` and checks the parts that matter: which routes and methods exist, which statuses each can answer, that every protected operation declares its security scheme, that bodies refuse unknown fields, that error responses are problem documents.

```python run
from typing import Annotated

from fastapi import FastAPI, Path
from pydantic import BaseModel, ConfigDict, Field


class NewTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, Field(min_length=3, max_length=40)]


class Problem(BaseModel):
    status: int
    code: str


app = FastAPI(title="Tickets", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/tickets", status_code=201, responses={422: {"model": Problem}})
def create(ticket: NewTicket) -> dict[str, str]:
    return {"title": ticket.title}


@app.get("/tickets/{ticket_id}", responses={404: {"model": Problem}})
def read(ticket_id: Annotated[int, Path(ge=1, le=2**31 - 1)]) -> dict[str, int]:
    return {"id": ticket_id}


spec = app.openapi()                                                      # works even though the route that serves it is off
assert {(p, m) for p, item in spec["paths"].items() for m in item} == {("/tickets", "post"), ("/tickets/{ticket_id}", "get")}
assert set(spec["paths"]["/tickets"]["post"]["responses"]) == {"201", "422"}
assert spec["components"]["schemas"]["NewTicket"]["additionalProperties"] is False
title = spec["components"]["schemas"]["NewTicket"]["properties"]["title"]
assert (title["minLength"], title["maxLength"]) == (3, 40)
param = spec["paths"]["/tickets/{ticket_id}"]["get"]["parameters"][0]
assert (param["schema"]["minimum"], param["schema"]["maximum"]) == (1, 2**31 - 1)
```

The description says the error responses are `application/json`, because that is the default media type of the route. If your service answers `application/problem+json`, either change the description (the guided lab post-processes it) or accept that the contract is slightly wrong; a contract test then also checks the *runtime* content type.

Tests of an API are **negative tests first**. For every rule, one request that must be refused, with the status and the code. Parametrise: a list of hostile and awkward inputs is the cheapest security test there is.

```python module=ticketapp
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

TICKETS: dict[int, dict] = {}
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class NewTicket(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: Annotated[str, Field(min_length=3, max_length=40)]


def caller(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization != "Bearer alice-token":
        raise HTTPException(401, "Authentication is required.", headers={"WWW-Authenticate": 'Bearer realm="tickets"'})
    return "alice"


@app.post("/tickets", status_code=201)
def create(ticket: NewTicket, who: Annotated[str, Depends(caller)]) -> dict:
    TICKETS[len(TICKETS) + 1] = {"owner": who, "title": ticket.title}
    return {"id": len(TICKETS)}
```

```python test
import pytest
from fastapi.testclient import TestClient

import ticketapp

client = TestClient(ticketapp.app)
AUTH = {"Authorization": "Bearer alice-token"}


@pytest.fixture(autouse=True)
def empty():
    ticketapp.TICKETS.clear()


def test_a_valid_ticket_is_created():
    r = client.post("/tickets", json={"title": "Printer"}, headers=AUTH)
    assert r.status_code == 201 and len(ticketapp.TICKETS) == 1


@pytest.mark.parametrize("body", [{}, {"title": "ab"}, {"title": "x" * 41}, {"title": 123}, {"title": "abc", "status": "closed"}, [], None, "text"])
def test_an_invalid_body_is_a_422_and_nothing_is_stored(body):
    assert client.post("/tickets", json=body, headers=AUTH).status_code == 422
    assert ticketapp.TICKETS == {}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer other"}, {"Authorization": "alice-token"}, {"Authorization": "bearer alice-token"}])
def test_a_missing_or_wrong_credential_is_a_401_with_a_challenge(headers):
    r = client.post("/tickets", json={"title": "Printer"}, headers=headers)
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Bearer")
    assert ticketapp.TICKETS == {}


def test_authentication_comes_before_validation():
    assert client.post("/tickets", json={"title": "x"}).status_code == 401
```

## 9. Operating the service (LO6)

**Configuration fails closed.** A service that cannot find its secret must not start with a default one. The settings object validates everything at construction and never repeats the secret in a message; the entry point reads the environment through it. Tests build settings from a dictionary, never from the real environment.

```python run
from collections.abc import Mapping
from dataclasses import dataclass, field


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    secret: str = field(repr=False)
    db_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.secret, str) or len(self.secret) < 32 or len(set(self.secret)) < 12:
            raise SettingsError("secret must be a random string of at least 32 characters (at least 12 different ones)")
        if not self.db_path:
            raise SettingsError("db_path must not be empty")

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Settings":
        secret, db_path = environ.get("APP_SECRET"), environ.get("APP_DB")
        if not secret:
            raise SettingsError("APP_SECRET is not set")
        if not db_path:
            raise SettingsError("APP_DB is not set")
        return cls(secret=secret, db_path=db_path)


good = "correct-horse-battery-staple-9f2c7d1e4a"
assert Settings.from_env({"APP_SECRET": good, "APP_DB": "t.db"}).db_path == "t.db"
assert good not in repr(Settings.from_env({"APP_SECRET": good, "APP_DB": "t.db"}))
for env in ({}, {"APP_SECRET": good}, {"APP_SECRET": "changeme", "APP_DB": "t.db"}, {"APP_SECRET": "a" * 40, "APP_DB": "t.db"}):
    try:
        Settings.from_env(env)
    except SettingsError as exc:
        assert good not in str(exc)
    else:
        raise AssertionError(env)
```

A secret that satisfies this rule is not necessarily a *good* secret (`password` followed by digits passes). The rule is a floor; the real remedy is to generate secrets (`secrets.token_urlsafe(32)`), keep them out of the repository (a pattern check in CI is cheap) and rotate them.

**Start-up and shut-down: lifespan, not `on_event`.** The handbook's era taught `@app.on_event("startup")`; FastAPI 0.143.1 still runs it and warns. The replacement is one context manager that owns the resource for the life of the application, and it is also the natural home of a readiness flag:

```python run
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    old = FastAPI()
    started = []

    @old.on_event("startup")
    def go() -> None:
        started.append(1)

    with TestClient(old):
        pass
assert started == [1] and any(w.category is DeprecationWarning and "lifespan" in str(w.message) for w in caught)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False


app = FastAPI(lifespan=lifespan)
app.state.ready = False


@app.get("/healthz")                                   # liveness: the process runs
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")                                    # readiness: it may receive traffic
def readyz() -> dict[str, str]:
    from fastapi import HTTPException
    if not app.state.ready:
        raise HTTPException(503, "starting")
    return {"status": "ready"}


client = TestClient(app)
assert client.get("/healthz").status_code == 200 and client.get("/readyz").status_code == 503
with client:                                           # entering the context runs the lifespan
    assert client.get("/readyz").status_code == 200
assert client.get("/readyz").status_code == 503
```

The handbook's health check (page 294) has one route for liveness and uses it as the readiness probe too; a service that is alive and not yet ready (migrating, warming a cache) then receives traffic it cannot serve.

**An audit trail says who did what, not what they wrote.** Log the event name, the actor's identifier, the object's identifier and the request id, as structured fields on the log record. Never the body of a ticket, a token, a header, an address or anything else a user typed: logs are copied to places with weaker access control than the database. A test reads the records and looks for a marker string you put into the input:

```python run
import logging

audit = logging.getLogger("lesson.audit")
audit.setLevel(logging.INFO)


class Collect(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


handler = Collect()
audit.addHandler(handler)


def create_ticket(actor: str, title: str, request_id: str) -> int:
    ticket_id = 7
    audit.info("ticket created", extra={"event": "ticket.created", "ticket": ticket_id, "actor": actor, "request_id": request_id})
    return ticket_id


create_ticket("alice", "Unmistakable-title-8841 password=hunter2", "req-1")
record = handler.records[0]
assert (record.event, record.ticket, record.actor, record.request_id) == ("ticket.created", 7, "alice", "req-1")
text = record.getMessage() + str(sorted(record.__dict__.items()))
assert "Unmistakable" not in text and "hunter2" not in text
```

**The edge belongs to the application too.** Three controls sit in front of the routes and are cheap to write as one outermost ASGI layer: a request id (the client's if it is clean, a fresh one otherwise, on every response and in every problem), four security headers on every response (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and a `Content-Security-Policy` that allows nothing), and a limit on the declared body size. The guided lab's step 7 builds it and its checks walk through the cases (a length sent twice, a length that is not a number, a body with no length at all). A proxy in front of the service should enforce the same limits first; the application's copy is there because proxies are reconfigured.

**Rate limits** protect the service from a caller who is allowed in but should not be allowed to do everything at once. They belong in front of the application, and an application-level limit is still useful when it counts per *key* and not per address (the independent lab). Count only authenticated requests - a limit that counts bad keys lets an attacker lock a victim out by spamming the victim's key identifier - and keep the counters of the current window only.

## 10. What differs between Python versions (executed)

The service is the same on 3.11 to 3.15; four things it touches are not. They are the reason the checks run on all five.

```python run
import gc
import sqlite3
import sys
import warnings
from datetime import datetime
from http import HTTPStatus

# 1. the standard library renamed two statuses in 3.13 (RFC 9110)
names = (HTTPStatus(413).phrase, HTTPStatus(422).phrase)
assert names == (("Request Entity Too Large", "Unprocessable Entity") if sys.version_info < (3, 13) else ("Content Too Large", "Unprocessable Content"))

# 2. datetime.utcnow() warns from 3.12
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    datetime.utcnow()
assert bool(caught) == (sys.version_info >= (3, 12))

# 3. an sqlite3 connection that is never closed is reported (ResourceWarning) from 3.13
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    conn = sqlite3.connect(":memory:")
    del conn
    gc.collect()
assert any(w.category is ResourceWarning for w in caught) == (sys.version_info >= (3, 13))

# 4. Starlette 1.x builds its test client on httpx2
from starlette.testclient import TestClient
import httpx2

assert issubclass(TestClient, httpx2.Client)
```

The third difference is why the guided checks do not wait for a warning: a check that *spies on `sqlite3.connect`* and asserts that every connection it handed out is closed passes and fails identically on every interpreter. The fourth is a supply-chain note, not a Python one: Starlette's test client moved from `httpx` to `httpx2` (a separate package maintained by the same authors); PY-M05's `httpx` examples are unaffected, and the lab requirements pin both.

## 11. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 215 to 221 | Part 1: web basics, "Flask vs Django vs FastAPI", first Flask app | section 1 and 2: HTTP is the contract; FastAPI is the one framework taught, and the defaults that matter are executed |
| 222, 228 | `app.run(debug=True)` in the first application | section 9: a debug server must never be reachable; the labs open no port and start nothing but `TestClient` |
| 226 to 233 | Flask project structure, blueprints, templates, middleware (before/after request) | not carried: server-side templates belong to a front-end course; middleware becomes the pure ASGI layer of section 9 |
| 234 | File uploads | section 7: the server chooses the name; the client supplies a kind |
| 236 to 252 | The contact-management system: models, admin login, dashboard templates, a seeded `password123` admin | not carried as a project; the lessons are in sections 5 and 6 (authentication, authorisation) and in the labs |
| 252 | Seed admin user with `generate_password_hash("password123")` | section 5: credentials come from configuration; hashing is the right idea with the wrong password |
| 258 to 260 | Upload route; the task CRUD API with no authentication and no validation | sections 3, 6 and 7; the guided lab is a CRUD API whose every route is authenticated, authorised and validated |
| 261 | Pagination and search with `contains(q)` | section 7 (wildcards) and the guided lab's `search`; pagination becomes a bounded `limit`/`offset` (guided) and a cursor (independent) |
| 264 to 273 | A "SaaS back end": FastAPI plus python-jose, passlib, a literal `SECRET`, `utcnow()` expiry, register/login routes with email OTP | section 5 and the guided lab (PyJWT, a configured secret, an injectable clock); password storage is PY-M07's topic |
| 274 | Flask dashboard with `SECRET_KEY = "DUDExBIVASH"` | section 9: configuration fails closed |
| 281 | A bullet list of security measures | section 7 and the injection suite: every bullet that can be tested is a test |
| 284 to 288 | Multi-tenant models, RBAC helper, Stripe billing and webhooks | the tenant rules are the independent lab; billing integrations are a topic for a commercial-systems course and need secrets the course does not hold |
| 289 to 291 | Background tasks, refresh tokens, rate limiting with `slowapi` | sections 5 and 9: one purpose per token; per-key rate limits (independent lab) |
| 294 | A single `/health` route for liveness and readiness | section 9: two routes |
| 296 to 298 | React front end with the token in `localStorage` | not carried: a browser-side storage decision for the front-end course (script on the page can read `localStorage`) |
| 307 to 310 | Exam-style questions on Flask and FastAPI | replaced by the quiz and the rubric of this module |
| 351, 394 | A "C2 API" example, an exploit template | not carried: offensive tooling, outside this course (finding F-PYH-004) |
| 452 | Auto-instrumenting a Flask application | PA-M07 (observability) |

## 12. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| trusting the framework's default 422 | rejected secrets echoed into responses and logs | a handler that reports `loc` and the kind of error only |
| `pattern` without `^...$` | `abc!!!` passes a "three letters" rule | anchor it; use `re.fullmatch` in your own code |
| lax parsing of a body | `"5"`, `true` and `1.0` become numbers | `strict=True` for bodies, lax for query strings |
| `extra` left at its default | unknown fields silently dropped | `extra="forbid"`: a 422 tells the client |
| the identifier accepted in many spellings | `/tickets/01`, `/tickets/+1`, `/tickets/1_0` | accept only `[1-9][0-9]*` |
| the owner compared after the lookup | one forgotten comparison is a data leak | ownership in the query |
| 403 for a foreign object | an enumeration oracle | 404, the same body as for a missing one |
| the role checked after the lookup | a missing object is revealed to a caller who could not act on it | role first |
| `jwt.decode` without pinning, or `utcnow()`, or a secret in the source | forged tokens, deprecation warnings, a published secret | pin; an injectable clock; configuration |
| one token for access and refresh | a 30-day token is also a 15-minute token | one purpose per token, or none |
| the 401 reason in the response | the reason is an oracle | one answer; the reason in the audit log |
| `==` on secrets or hashes | timing differences | `hmac.compare_digest`, the same work for unknown identifiers |
| f-string SQL, or a bound sort direction | injection, or an order that never changes | bound values; fixed tables for names and directions |
| `os.path.join(base, client_name)` | files written anywhere | server-chosen names and a containment check |
| client text in a log line or a header | forged records, split responses | log identifiers; replace, do not clean |
| logging what the user wrote | secrets in the log store | event, actor, object, request id - nothing else |
| `on_event` | a deprecation warning today, a removal later | `lifespan` |
| the interpreter's wording in the contract | an answer that changes with the Python version | write the titles down |
| tests that cannot fail | a green suite and a hole | negative tests, explicit expected sets, a mutation check |

## 13. Check yourself

1. A request arrives for `/tickets/7` from a caller who owns ticket 3 only. What status do you answer, what body, and why is "403 Forbidden" the more dangerous answer?
2. `Settings(secret="password" + "1234567890123456789012")` is accepted by the rule in section 9. What does the rule guarantee, what does it not, and what would you add?
3. Why do you check the token's `alg` yourself when you already pass `algorithms=["HS256"]` to the library? Name a second header you refuse and why.
4. A search endpoint binds the user's text as a parameter and still returns every row for `%`. Why, and what is the fix?
5. Your contract test pins `"Unprocessable Entity"` and passes. A colleague upgrades Python and it fails. Which side is wrong, and how do you stop it happening?
6. Give two reasons the audit log must not contain the ticket text.

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 14. Sources and verification trail

- Every assertion in this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 with fastapi 0.143.1, starlette 1.8.0, pydantic 2.14.1, PyJWT 2.15.1 and httpx2 2.13.1 (R-100; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). Reference documentation: <https://fastapi.tiangolo.com/> (request bodies, handling errors, lifespan events, testing), <https://docs.pydantic.dev/> (strict mode, `pattern`), <https://pyjwt.readthedocs.io/> (the `algorithms` argument, `options`), <https://www.rfc-editor.org/rfc/rfc9457> (problem details), <https://www.rfc-editor.org/rfc/rfc9110> (HTTP semantics; the renamed statuses), <https://owasp.org/API-Security/> (the API Security Top 10: object, function and property level authorisation, unrestricted resource consumption, security misconfiguration).
- Handbook corrections: finding F-PYH-015 (a CRUD API without authentication or validation, secrets and a database password in source, a token helper that modifies its argument and uses a deprecated clock, one token for two purposes, an upload under a client-chosen name, security measures listed without a test).
- Not verified here and therefore not claimed: behaviour behind a real reverse proxy or a real ASGI server (the labs use the in-process test client only); OAuth 2.0 and OpenID Connect flows (the labs consume tokens, they do not issue them); TLS configuration; the security of Flask, Django or python-jose (not exercised); the Stripe and e-mail integrations of the handbook (no secrets or network in this course); performance under load.
