---
id: PY-M05
title: "Files, structured data and HTTP clients"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M01 to PY-M04 and now write programs that read files and call web APIs, and who need those programs to survive slow, broken and hostile inputs"
prerequisites:
  - "PY-M01 (language core), PY-M02 (functions, errors and pytest) and PY-M04 (virtual environments and pinned dependencies)"
  - "Python 3.11 or newer (`tomllib` is in the standard library from 3.11); the labs were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "httpx 0.28.1, requests 2.34.2, pydantic 2.14.1 and pytest 9.1.1 from labs/requirements.txt; no account, no paid service and no network access beyond your own computer"
estimated_time_hours: {lesson: 3.0, guided_lab: 2.5, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005)", httpx: "0.28.1 (PyPI snapshot 2026-10-14: latest stable, released 2024-12-06; a 1.0.dev6 pre-release exists; R-045, R-088)", requests: "2.34.2 (PyPI snapshot; R-087)", pydantic: "2.14.1 (PyPI snapshot; R-090)", pytest: "9.1.1"}
last_verified: 2026-10-14
---

# PY-M05 - Files, structured data and HTTP clients

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Read and write files and configuration safely: explicit encodings, context managers, TOML and JSON, and writes that either complete or leave the old file untouched. |
| **LO2** | Validate decoded JSON against a schema (a pydantic model), choose strict or lenient checking on purpose, and report what is wrong and where. |
| **LO3** | Call an HTTP API with one shared client, an explicit timeout on every request, and checks of the status, the content type and the decoded value. |
| **LO4** | Retry only transient failures of safe requests, with bounded exponential backoff that honours `Retry-After`, and test the timing without sleeping. |
| **LO5** | Consume a paginated API completely and safely (cursors, loop and size limits, same-origin links) and publish the result all-or-nothing. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Files and network calls are where a program meets the world, and the world misbehaves: a disk fills up, a server answers in a minute instead of a second, an API returns an HTML error page with status 200, a list of results has an endless next link. The 2025 handbook shows the happy path in a few lines
(`requests.get(url)`, then `res.json()`; `json.dump(data, open("file.json", "w"))`). Those lines work until the first bad day, and then they hang forever, crash on the wrong exception, or leave half a file on disk (F-PYH-009). This module keeps the handbook's goal, "automate with files and APIs", and teaches the
habits that make such automation safe to leave running: limits on time and size, validation of everything that comes from outside, and writes that cannot half-succeed. Every example below runs on your own computer against small servers that are started for the occasion.

## 2. Files you can trust (LO1)

A file handle left to the garbage collector is closed *eventually*; on a long-running program, or on a platform without reference counting, "eventually" is too late, and Python tells you so with a `ResourceWarning`. Use `pathlib.Path` with `read_text`/`write_text` (which open and close for you) or a `with` block, and always pass `encoding="utf-8"` (lesson PY-M01, section 6).

```python run
import gc
import json
import tempfile
import warnings
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "data.json"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        json.dump({"a": 1}, open(path, "w"))            # the handbook's form (p. 83): the handle is never closed on purpose
        gc.collect()
    assert any(issubclass(w.category, ResourceWarning) for w in caught)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        path.write_text(json.dumps({"a": 1}), encoding="utf-8")        # opens, writes, closes
        assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
        gc.collect()
    assert not caught
```

**Configuration belongs in a format with types and comments.** Since Python 3.11 the standard library reads TOML (`tomllib`); it asks for a file opened in *binary* mode and decodes UTF-8 itself. JSON is the exchange format for data; JSON Lines (one JSON object per line) suits logs and streams because a reader can process it line by line.
Never load `pickle` or unsafe YAML from a file you do not control (PY-M07).

**Moving and replacing files destroys data when done carelessly.** The handbook's bulk rename (p. 91) renames every entry of the current folder, including the script itself, and on Linux and macOS `os.rename` silently replaces an existing target. Plan first, check for collisions, then act:

```python run
import os
import tempfile
from pathlib import Path


def plan_renames(folder: Path) -> list[tuple[Path, Path]]:
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".txt")
    plan = [(old, folder / f"file_{i}.txt") for i, old in enumerate(files)]
    clashes = sorted(new.name for old, new in plan if new.exists() and new != old)      # a target that already exists would be replaced
    if clashes:
        raise FileExistsError(f"would overwrite: {clashes}")
    return plan


with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    for name, text in {"a.txt": "A", "b.txt": "B", "file_1.txt": "precious"}.items():
        (folder / name).write_text(text, encoding="utf-8")

    try:
        plan_renames(folder)
    except FileExistsError as error:
        assert "file_1.txt" in str(error)
    else:
        raise AssertionError("the plan must notice that file_1.txt would be overwritten")
    assert (folder / "file_1.txt").read_text(encoding="utf-8") == "precious"      # nothing was touched

    if os.name == "posix":                                      # what the handbook's loop does on Linux and macOS
        for i, old in enumerate(sorted(folder.glob("*.txt"))):
            os.rename(old, folder / f"file_{i}.txt")
        assert "precious" not in {p.read_text(encoding="utf-8") for p in folder.glob("*.txt")}      # silently destroyed
```

**A write must either complete or change nothing.** If your program dies while writing `report.json`, the next reader finds half a file. The pattern is: serialise first (so a bad value cannot touch the disk), write a temporary file *in the same folder*, then `os.replace` it over the target. `os.replace` is atomic on the same file system:
readers see the old file or the new one, never a mixture. Clean up the temporary file when anything goes wrong.

```python run
import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path: Path, data: object) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"       # fails here, before any file exists, if data is not serialisable
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "report.json"
    write_json_atomic(target, {"total": 3})
    try:
        write_json_atomic(target, {"total": {1, 2, 3}})                 # a set is not JSON
    except TypeError:
        pass
    else:
        raise AssertionError("a set must not be serialisable")
    assert json.loads(target.read_text(encoding="utf-8")) == {"total": 3}          # the old report survived
    assert [p.name for p in Path(tmp).iterdir()] == ["report.json"]               # and no temporary file is left
```

## 3. Data you can trust: schemas (LO2)

Decoding JSON only tells you the *syntax* was right. `json.loads` happily returns a string where you expected a number, a missing key, `NaN` (which standard JSON does not allow) or a list of ten million items. **Validate at the boundary**: describe the data you accept once, check every value against it, and let everything after the boundary rely on the checked types.
A pydantic model is such a description. It is also documentation, and the same idea scales to FastAPI requests in PY-M10.

Two choices matter. **Lax or strict:** by default pydantic *coerces* when it can (the text `"5"` becomes the integer 5, and `True` becomes 1); strict mode (per model, per field or per call) refuses (R-090, executed: R-092). Coercion is convenient for form input and risky for machine-to-machine data, where a type change usually signals a bug on the other side.
**Unknown fields:** ignoring them keeps you working when the vendor adds a field; forbidding them catches typos in your own configuration. Choose per model and say why. Constrain what the type cannot say: ranges, lengths, patterns, allowed values.

```python run
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class Lenient(BaseModel):
    id: int
    name: str


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")        # exact types; tolerate fields we do not use
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    currency: Literal["USD", "EUR"]
    ratio: float = Field(allow_inf_nan=False)


assert Lenient.model_validate({"id": "5", "name": "n"}).id == 5          # lax mode coerces the text "5"
assert Lenient.model_validate({"id": True, "name": "n"}).id == 1         # and even a boolean
assert Lenient.model_validate({"id": 1, "name": "n", "extra": 1}).model_dump() == {"id": 1, "name": "n"}      # unknown fields are dropped

good = {"id": 5, "name": "n", "currency": "EUR", "ratio": 0.5, "warehouse": "north"}
assert Strict.model_validate(good).id == 5

for bad, where, kind in [({**good, "id": "5"}, "id", "int_type"), ({**good, "id": 0}, "id", "greater_than_equal"), ({**good, "currency": "JPY"}, "currency", "literal_error"),
                         ({**good, "name": ""}, "name", "string_too_short"), ({k: v for k, v in good.items() if k != "name"}, "name", "missing")]:
    try:
        Strict.model_validate(bad)
    except ValidationError as error:
        first = error.errors()[0]
        assert (first["loc"][0], first["type"]) == (where, kind)            # what is wrong, and where
    else:
        raise AssertionError(f"{bad} must be rejected")

assert str(json.loads('{"x": NaN}')["x"]) == "nan"                          # Python's json accepts NaN; so must your schema reject it on purpose
try:
    Strict.model_validate({**good, "ratio": float("nan")})
except ValidationError as error:
    assert error.errors()[0]["type"] == "finite_number"

items = TypeAdapter(list[Strict]).validate_python([good, {**good, "id": 6}])        # a whole list at once
assert [item.id for item in items] == [5, 6]
```

Money deserves a note: JSON numbers are usually read as `float`, which cannot represent most decimals exactly (PY-M01, section 3). When an API sends prices as text (`"12.50"`) keep them as text or `Decimal`; when it sends integer cents, validate them as integers.

## 4. Talking to an API: requests, responses and clients (LO3)

An HTTP exchange is a request (method, URL, headers, optional body) and a response (status, headers, body). Status classes tell you who is at fault and what to do: 2xx success, 3xx redirection, 4xx *you* sent something wrong (retrying will not help), 5xx the server failed (retrying might). The `Content-Type` header says how to read the body.
Two rules save most of the trouble: **check the status before you decode, and check the decoded value before you use it**. A successful `.json()` does not mean the request succeeded (R-087): servers send JSON error bodies, and some send HTML with status 200.

**Use one client.** A `Client` keeps connections open and reuses them, holds your timeout and header settings in one place, and is easy to replace in tests. A bare `httpx.get(url)` or `requests.get(url)` builds a new connection each time. The examples use this tiny server (it is a module block, so later blocks import it):

```python module=tinyserver
"""A tiny loopback server for the examples: app(method, path, request_number) returns (status, headers, body) or None to close the connection."""
import http.server
import threading


def start(app):
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _serve(self):
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            seen.append((self.command, self.path, self.client_address[1]))
            answer = app(self.command, self.path, len(seen))
            if answer is None:
                self.close_connection = True
                return
            status, headers, body = answer
            body = body.encode() if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _serve

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", seen, server.shutdown
```

```python run
import json
import os

import httpx

from tinyserver import start

os.environ["NO_PROXY"] = "127.0.0.1"                   # bare httpx.get() reads proxy settings from the environment; keep this traffic local


def app(method, path, number):
    if path == "/ok":
        return 200, {"Content-Type": "application/json"}, json.dumps({"n": number})
    if path == "/error-page":
        return 200, {"Content-Type": "text/html"}, "<html>maintenance window</html>"
    if path == "/missing":
        return 404, {"Content-Type": "application/json"}, json.dumps({"error": "no such thing"})
    return 500, {}, "boom"


base, seen, stop = start(app)
with httpx.Client(base_url=base, timeout=5.0, trust_env=False) as client:
    for _ in range(3):
        assert client.get("/ok").json()["n"] >= 1
    assert len({port for _, _, port in seen}) == 1                         # one client: one connection, reused three times

    page = client.get("/error-page")
    assert page.status_code == 200 and page.headers["content-type"] == "text/html"
    try:
        page.json()
    except ValueError:
        pass                                                                # status 200 and still not JSON: always check the content type
    else:
        raise AssertionError("HTML is not JSON")

    missing = client.get("/missing")
    assert missing.status_code == 404 and missing.json() == {"error": "no such thing"}      # JSON in an error response is still an error
    try:
        missing.raise_for_status()
    except httpx.HTTPStatusError as error:
        assert error.response.status_code == 404

seen.clear()
for _ in range(3):
    httpx.get(base + "/ok", timeout=5.0)
assert len({port for _, _, port in seen}) == 3                             # bare calls: three connections
stop()
```

Redirects deserve a decision too. `requests` follows them by default (for every method except HEAD, R-087); `httpx` does not (R-088, executed: R-091). A redirect can send your request to another host, so the safe default is "do not follow, and say so", unless you have a reason.

## 5. Timeouts: the most expensive missing argument (LO3)

A network call that never returns is worse than one that fails. The `requests` documentation says that "nearly all production code should use" the `timeout` parameter, that failing to do so "can cause your program to hang indefinitely", and that without one "requests do not time out" (R-087). `httpx` has a default of 5 seconds for each of four timeouts: **connect** (establish the connection),
**read** (wait for the next piece of data), **write** and **pool** (wait for a free connection) (R-088). The handbook's `requests.get(url)` examples (pp. 91, 125, 126, 135 and others) pass none: in the extracted text 37 of 38 `requests` and `httpx` calls have no explicit timeout (F-PYH-009). The next block reproduces this against a server that accepts connections and never answers:

```python run
import os
import socket
import threading
import time

import httpx
import requests

os.environ["NO_PROXY"] = "127.0.0.1"                   # both libraries read proxy settings from the environment; keep this traffic local
silent = socket.socket()
silent.bind(("127.0.0.1", 0))
silent.listen(5)
held = []
threading.Thread(target=lambda: [held.append(silent.accept()[0]) for _ in range(20)], daemon=True).start()
url = "http://127.0.0.1:%d/" % silent.getsockname()[1]

outcome = {}


def call():
    try:
        requests.get(url)                                    # no timeout: what the handbook shows
        outcome["result"] = "returned"
    except Exception as error:
        outcome["result"] = type(error).__name__


worker = threading.Thread(target=call, daemon=True)
worker.start()
worker.join(1.0)
assert worker.is_alive(), "requests.get without a timeout is still waiting"

started = time.monotonic()
try:
    requests.get(url, timeout=0.3)
except requests.exceptions.Timeout:
    assert time.monotonic() - started < 1.0
else:
    raise AssertionError("expected a timeout")

try:
    httpx.get(url, timeout=httpx.Timeout(5.0, read=0.3))        # connect and write 5 s, read 0.3 s
except httpx.ReadTimeout:
    pass
else:
    raise AssertionError("expected ReadTimeout")

assert httpx.Client().timeout == httpx.Timeout(5.0)             # the default, without being asked

refused = socket.socket()
refused.bind(("127.0.0.1", 0))
closed_port = refused.getsockname()[1]
refused.close()                                                   # nobody listens here any more
try:
    httpx.get(f"http://127.0.0.1:{closed_port}/", timeout=1.0)
except httpx.ConnectError:
    pass                                                          # a refused connection fails at once and is not a timeout
else:
    raise AssertionError("expected ConnectError")
```

**A read timeout is not a deadline.** It limits the wait for the *next* bytes, not the whole transfer. A server that sends one byte every 0.2 seconds never trips a 0.5-second read timeout and can keep you busy for an hour. For a limit on the whole operation, measure it yourself while you read (and put a limit on the size too, section 9):

```python run
import socket
import threading
import time

import httpx

server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen(5)


def trickle():
    conn, _ = server.accept()
    conn.recv(65536)
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\n\r\n")
    for _ in range(10):
        time.sleep(0.15)
        conn.sendall(b"2\r\nab\r\n")
    conn.sendall(b"0\r\n\r\n")
    conn.close()


threading.Thread(target=trickle, daemon=True).start()
started = time.monotonic()
received = 0
with httpx.Client(timeout=httpx.Timeout(0.5)) as client:                  # every gap between chunks is far below the read timeout
    with client.stream("GET", "http://127.0.0.1:%d/" % server.getsockname()[1]) as response:
        for chunk in response.iter_bytes():
            received += len(chunk)
            if time.monotonic() - started > 0.5:                          # our own whole-operation deadline
                break
assert 0.5 <= time.monotonic() - started < 1.2 and received < 20
```

## 6. Retries: when, how often, how long (LO4)

Retrying turns a short outage into a non-event, and a bad retry loop turns a short outage into a long one. Four rules.

1. **Retry only what is transient.** Timeouts, dropped connections and the statuses 429 (too many requests), 502, 503 and 504 often pass by themselves. A 404 or a 401 will still be a 404 or a 401, and a body that is not JSON will still not be JSON.
2. **Retry only what is safe to repeat.** RFC 9110 defines PUT, DELETE and the read-only methods as idempotent (repeating them has the same effect as doing them once) and says a client "SHOULD NOT automatically retry a request with a non-idempotent method" such as POST unless it knows the request is effectively idempotent or was not applied (R-089).
   The reason is a timeout *after* the server did the work: the client cannot tell the difference. The next block shows a retried POST creating the same record twice. APIs that need safe POST retries accept an idempotency key that the server uses to recognise a repeat.
3. **Wait, with a limit.** Exponential backoff (0.5 s, 1 s, 2 s, ... up to a cap) gives the server room to recover. Add random jitter in production so that thousands of clients do not retry in lockstep. Obey `Retry-After` when the server sends it: it is either a number of seconds or an HTTP date (R-089), and a cap protects you from a server that asks for an hour.
4. **Bound the effort.** A maximum number of attempts per request and a deadline for the whole job, after which you fail loudly. Retrying forever is a hang with extra steps.

```python run
import email.utils
import random
import threading
import time
from datetime import datetime, timezone

import httpx

from tinyserver import start


def delay_for(attempt: int, retry_after: str | None = None, *, now: datetime | None = None, jitter=lambda seconds: seconds) -> float:
    backoff = min(8.0, 0.5 * 2 ** (attempt - 1))
    asked = None
    if retry_after is not None:
        text = retry_after.strip()
        if text.isascii() and text.isdigit():
            asked = float(int(text))
        else:
            try:
                when = email.utils.parsedate_to_datetime(text)
            except (TypeError, ValueError):
                when = None
            if when is not None:
                asked = max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds())
    return jitter(backoff if asked is None else min(max(backoff, asked), 30.0))


assert [delay_for(n) for n in range(1, 8)] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0, 8.0]
assert delay_for(1, "5") == 5.0 and delay_for(1, "5000") == 30.0 and delay_for(1, "soon") == 0.5 and delay_for(1, "-1") == 0.5
assert delay_for(1, "Wed, 14 Oct 2026 12:00:07 GMT", now=datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)) == 7.0
rng = random.Random(7)
spread = [delay_for(3, jitter=lambda seconds: rng.uniform(0, seconds)) for _ in range(200)]      # "full jitter": anywhere between 0 and the backoff
assert all(0 <= s <= 2.0 for s in spread) and len({round(s, 3) for s in spread}) > 100

created = []


def app(method, path, number):
    if method == "POST":
        created.append(number)                    # the server does the work ...
        time.sleep(0.5)                           # ... and answers too late for the client
    return 200, {"Content-Type": "application/json"}, "{}"


base, seen, stop = start(app)
with httpx.Client(base_url=base, timeout=0.2, trust_env=False) as client:
    for attempt in range(2):                      # a naive "retry on timeout" loop around a POST
        try:
            client.post("/orders", json={"item": "book"})
            break
        except httpx.TimeoutException:
            continue
assert len(created) == 2, "the same order was created twice because the first answer was lost"
stop()
```

**Test the timing without waiting.** Pass `sleep` (and, for deadlines, a clock) as arguments with the real functions as defaults. A test then supplies a recorder and checks the *sequence* of waits in microseconds. `httpx.MockTransport` replaces the network entirely for unit tests; the local-server approach of the labs also exercises real sockets, timeouts and dropped connections.
The next two blocks are a module and its pytest tests, which the lesson test-suite runs:

```python module=resilient
import httpx

RETRY_STATUS = {429, 502, 503, 504}


def get_json(client, url, *, attempts=3, sleep):
    last = "no attempt made"
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
        except httpx.TransportError as error:
            last = type(error).__name__
        else:
            if response.status_code in RETRY_STATUS:
                last = f"HTTP {response.status_code}"
            elif response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}")
            else:
                return response.json()
        if attempt < attempts:
            sleep(0.5 * 2 ** (attempt - 1))
    raise RuntimeError(f"gave up after {attempts} attempts: {last}")
```

```python test
import httpx
import pytest

from resilient import get_json


def client_with(*answers):
    queue = list(answers)

    def handler(request):
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://example.test"), queue


def test_a_transient_failure_is_retried_and_the_waits_are_recorded():
    client, queue = client_with(httpx.Response(503), httpx.ConnectTimeout("slow"), httpx.Response(200, json={"ok": True}))
    waits = []
    assert get_json(client, "/x", sleep=waits.append) == {"ok": True}
    assert waits == [0.5, 1.0] and queue == []


def test_a_client_error_is_not_retried():
    client, queue = client_with(httpx.Response(404), httpx.Response(200, json={}))
    waits = []
    with pytest.raises(RuntimeError, match="404"):
        get_json(client, "/x", sleep=waits.append)
    assert waits == [] and len(queue) == 1


def test_giving_up_does_not_sleep_after_the_last_attempt():
    client, _ = client_with(*[httpx.Response(502)] * 3)
    waits = []
    with pytest.raises(RuntimeError, match="gave up after 3 attempts"):
        get_json(client, "/x", sleep=waits.append)
    assert waits == [0.5, 1.0]
```

## 7. Pagination: reading everything without running away (LO5)

An API returns large collections a page at a time. **Offset pagination** (`?offset=20&limit=10`) is simple and breaks when the data changes between your requests: an item inserted at the front pushes everything down, and the next page repeats an item you already saw (deleting one makes you skip an item).
**Cursor pagination** (`?cursor=abc`) asks for "everything after this position" and is stable. The same data, read both ways:

```python run
def by_offset(data, offset, limit):
    return data[offset:offset + limit]


def by_cursor(data, after_id, limit):                        # "items with id greater than after_id"
    return [item for item in data if item["id"] > after_id][:limit]


def collection():
    return [{"id": i} for i in range(1, 7)]                 # the server's collection


data = collection()
first = by_offset(data, 0, 3)
data.insert(0, {"id": 0})                                    # something new arrives while we read ...
second = by_offset(data, 3, 3)
assert [i["id"] for i in first + second] == [1, 2, 3, 3, 4, 5]        # ... and item 3 is delivered twice

data = collection()
first = by_offset(data, 0, 3)
del data[0]                                                  # something is removed while we read ...
second = by_offset(data, 3, 3)
assert [i["id"] for i in first + second] == [1, 2, 3, 5, 6]           # ... and item 4 is never delivered

data = collection()
first = by_cursor(data, 0, 3)
data.insert(0, {"id": 0})
del data[1]                                                  # both changes at once
second = by_cursor(data, first[-1]["id"], 3)
assert [i["id"] for i in first + second] == [1, 2, 3, 4, 5, 6]        # the cursor asks "after item 3": stable

```

Your loop must also survive a server that is wrong or hostile:

- **A cursor that repeats** (or a `next` link that points back to an earlier page) makes `while next_page:` run forever. Remember the cursors you have seen and fail on a repeat.
- **A listing without end** (every page returns a new cursor and nothing else) needs a maximum page count.
- **A `next` link is untrusted input.** If you follow it blindly, a compromised or malicious response can send your client (and its `Authorization` header or its position inside your network) to another host. Resolve relative links against the current URL, then require the **same scheme, host and port** as the API you were configured for, and refuse before sending anything.
  Compare parsed URLs, never strings: `http://127.0.0.1@evil.test/` begins with the allowed host and is a request to `evil.test`.
- **Duplicates and bad items happen.** Decide the policy up front: keep the latest version of an item, set invalid items aside with their position and reason, and fail the whole run when too many are invalid.

```python run
import httpx


def same_origin(url: httpx.URL, base: httpx.URL) -> bool:
    default = {"http": 80, "https": 443}
    return (url.scheme, url.host, url.port or default.get(url.scheme)) == (base.scheme, base.host, base.port or default.get(base.scheme))


base = httpx.URL("http://127.0.0.1:8000/v2/prices?page_size=50")
assert same_origin(base.join("/v2/prices?page_token=2"), base)                    # a relative link resolves against the current URL
assert same_origin(base.join("http://127.0.0.1:8000/v2/prices?page_token=2"), base)
for hostile in ["http://localhost:8000/v2/prices", "http://127.0.0.1:9/v2/prices", "https://127.0.0.1:8000/v2/prices", "//evil.test/v2/prices",
                "http://127.0.0.1@evil.test/v2/prices", "ftp://127.0.0.1:8000/v2/prices"]:
    assert not same_origin(base.join(hostile), base), hostile

userinfo_trick = httpx.URL("http://127.0.0.1@evil.test/x")
assert userinfo_trick.host == "evil.test" and "127.0.0.1" in str(userinfo_trick)      # the string looks right; the host is not


def pages(fetch, max_pages=5):
    """Yield page after page; stop on a repeated cursor or when max_pages is reached."""
    cursor, seen = None, set()
    for _ in range(max_pages):
        data, cursor = fetch(cursor)
        yield data
        if cursor is None:
            return
        if cursor in seen:
            raise RuntimeError("pagination loop")
        seen.add(cursor)
    raise RuntimeError(f"more than {max_pages} pages")


assert list(pages(lambda c: ([1], None))) == [[1]]
for broken, message in [(lambda c: ([1], "a" if c is None else "a"), "pagination loop"), (lambda c: ([1], (c or "") + "x"), "more than 5 pages")]:
    try:
        list(pages(broken))
    except RuntimeError as error:
        assert message in str(error)
    else:
        raise AssertionError("a runaway listing must stop")
```

Finally, publish **all or nothing**: collect and validate everything first, then replace the result file once (section 2). A reader then sees yesterday's complete file or today's complete file, never a file that grows page by page and may stop at page 3.

## 8. Putting it together

The two labs combine these pieces. The guided lab builds the parts one at a time (settings file, atomic write, client, delay function, request with retries, paginated generator, synchronisation) against a scripted local catalogue API. The independent lab asks for the whole job from a written specification against a vendor feed, with limits on time, size and pages,
a policy for invalid and duplicate items, and a hidden suite that tries hostile servers. Both run entirely on your computer.

## 9. Security and operations notes

- **TLS verification stays on.** `verify=False` (handbook p. 427-428; F-PYH-002) turns HTTPS into an unauthenticated connection. If you must trust a private certificate authority, give the client that authority's bundle (`verify="/path/to/ca.pem"`) rather than disabling checks (PY-M07).
- **Secrets never go in URLs or logs.** A token in a query string ends up in server logs, proxies and your own tracebacks. Send it in a header; note that `httpx` shows `authorization` headers as `[secure]` when you print them (executed below), and `requests` removes an `Authorization` header when a redirect leaves the host (R-087).
- **Limit the size you read.** A response that never ends fills your memory. Read in chunks and stop at a limit, as below; refuse early when `Content-Length` already exceeds it.
- **Never build requests to URLs a stranger chose** without an allow-list of hosts (server-side request forgery); the same-origin rule above is the minimal version of that idea.
- **Behind a proxy**, `httpx` and `requests` read the proxy settings from environment variables. For tests on your own computer use `trust_env=False` so that traffic to `127.0.0.1` is never sent to a proxy.

```python run
import httpx

from tinyserver import start

assert "secret-token" not in repr(httpx.Headers({"Authorization": "Bearer secret-token", "Accept": "application/json"}))      # shown as [secure]


def app(method, path, number):
    return 200, {"Content-Type": "application/octet-stream"}, b"x" * 100_000


base, seen, stop = start(app)
LIMIT = 10_000
with httpx.Client(timeout=5.0, trust_env=False) as client:
    with client.stream("GET", base + "/big") as response:
        assert int(response.headers["content-length"]) > LIMIT                  # a polite server announces the size: refuse before reading
        body = b""
        for chunk in response.iter_bytes(chunk_size=4096):
            body += chunk
            if len(body) > LIMIT:
                break                                                            # an impolite one: stop reading at the limit
assert LIMIT < len(body) <= LIMIT + 2 * 4096
stop()
```

## 10. What changed since the 2025 handbook

Verified on 2026-10-14 (executed in this lesson or recorded in the register):

| 2025 handbook | Now |
|---|---|
| `requests.get(url)` with no timeout (pp. 91, 125, 126, 135; 37 of 38 extracted calls) | `requests` still applies no timeout (R-087; executed: R-091). `httpx` defaults to 5 s (R-088). Always pass an explicit timeout. |
| `res.json()` without a status check | A successful `.json()` does not mean a successful request (R-087); check status, content type and the decoded value. |
| `async with httpx.AsyncClient()` created inside the function that fetches one URL (p. 129) | One shared client; asynchronous clients are taught in PY-M06. |
| `json.dump(data, open("file.json", "w"))` (p. 83) | `Path.write_text(..., encoding="utf-8")` or a `with` block; atomic replace for results others read. |
| Bulk rename with `os.rename` in a loop (p. 91) | Plan, check for collisions, then rename; `os.rename` replaces silently on POSIX. |
| `pickle` for saving objects (p. 83) | Not for data you do not control; JSON with a schema (PY-M07 for the pickle risks). |
| Web scraping with BeautifulSoup (pp. 126-127) | Not covered here: scraping needs a legal and ethical policy (terms of use, robots rules) that this course has not defined. |
| Library versions unstated | `requests` 2.34.2, `httpx` 0.28.1 (the last stable release dates from 2024-12-06; a 1.0 pre-release was published 2026-08-31), `pydantic` 2.14.1, `tomllib` in the standard library since Python 3.11. Pin them (PY-M04) and re-test when `httpx` 1.0 is released. |

## 11. Common misconceptions

| Misconception | Reality |
|---|---|
| "The library has a sensible default timeout." | `requests` has none; `httpx` has 5 s. Do not rely on either; set it. |
| "A read timeout limits the whole request." | It limits the wait for the next bytes; a slow trickle never trips it. Keep a deadline of your own. |
| "If it fails, just retry." | Only transient failures of safe requests, with a limit; a retried POST can do the work twice. |
| "Status 200 means I have my data." | It means the server answered; check the content type and validate the data. |
| "Validation is only for user forms." | Everything that crosses a boundary (files, APIs, queues) can be wrong; a vendor's change is as dangerous as an attacker's. |
| "`next` links are the server's business." | They are input; follow them only inside the origin you configured, with loop and page limits. |

## 12. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Implement seven functions in `syncer.py` until the provided checks pass: settings, atomic write, client, backoff, request with retries, paginated generator, synchronisation | `lab-guided/README.md` |
| Independent lab (LO1-LO5) | Implement `sync_feed` from a written specification; instructors run a larger hidden suite with hostile servers | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 13. Summary

- Close files, name the encoding, and replace results atomically; a half-written file is a bug waiting for a reader.
- Validate everything that comes from outside against a schema, and choose strict or lenient on purpose.
- One client, an explicit timeout on every request, a check of status, content type and decoded value.
- Retry only transient failures of safe requests, with backoff, a cap, `Retry-After` and a deadline; test the waits without sleeping.
- A paginated listing needs loop, size and page limits and a same-origin rule for next links; publish all or nothing.

## References

- Requests, *Quickstart* (R-087); HTTPX, *Timeouts* and *Requests compatibility* (R-088); RFC 9110, sections 9.2.2 and 10.2.3 (R-089); Pydantic, *Strict Mode* (R-090); registry snapshot of 2026-10-14 (R-045).
- Executed evidence: probes `http-client-defaults` (R-091) and `pydantic-lax-and-strict-validation` (R-092); every block of this lesson is executed by the repository tests on CPython 3.11-3.15.
- Findings and change records addressed: F-PYH-009 (no timeouts or status checks, unclosed handles, destructive rename), F-PYH-004 (listings not executed), F-PYH-007 (assessment by recall questions only), MC-PYH-19.
