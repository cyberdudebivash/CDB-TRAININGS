# FND-M03 guided lab — Controlled live HTTP over TCP loopback

**Learning outcomes:** LO1, LO2, LO3, LO4. **Estimated time:** 90 minutes. **Prerequisites:** FND-M01, FND-M02, Python 3.11+, standard library only. **Environment:** student's own workstation with permission to bind to `127.0.0.1`. No outside network, DNS resolution, packet capture or administrator access is required.

## Step 1 — Establish scope and terminology (LO1)

The reference creates a temporary TCP listener on `127.0.0.1`, then an HTTP/1.1 client on the same host. The TCP port is assigned by the OS (`port=0` at bind). The exercise does **not** make a DNS query, contact the public internet or run a TLS handshake. Record your OS and Python version and do not use customer data.

## Step 2 — Execute a real local HTTP exchange (LO2)

From repository root run:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M03/lab-guided/checks -p test_http_trace.py -v
```

In a short Python scratch program, import `trace_request` from `lab-guided/solution/http_trace.py`, print its `/health` result, then its `/missing` result. Observe the explicit 200 and 404 HTTP statuses, response body and `Content-Type`. A 404 shows that HTTP transported an application error successfully; it does **not** prove TCP failed.

## Step 3 — Failure injection and boundary tests (LO3)

Run the published test suite as written. Explain why paths like `/../../secrets`, full URLs and query strings are rejected **by our narrowly scoped client contract**. Observe the server's 400 response for an unknown route. Record the cleanup test demonstrating the loopback server no longer accepts connections after its context exits. Do not change the tests to hide failures.

## Step 4 — Request/response evidence (LO4)

Write a sanitized runbook containing: scope and date, interpreter version, exact test command, count of checks, observed status codes, response Content-Type, transport address, and known limitations. Classify `DNS: NOT_OBSERVED`, `TCP: CONTROLLED_LIVE`, `TLS: NOT_USED`, `HTTP: CONTROLLED_LIVE`. Do not label replayed or inferred protocol steps as captured traffic.

## Explicit security and operational limits

The server is loopback-only, the client cannot select an arbitrary host, and routes are allowlisted. No customer endpoints, live enterprise credentials or attack payloads are involved. This lab lacks TLS, DNS query capture, proxy behavior, HTTP/2/3, production reliability and real business identity checks. It is an educational exercise; mandatory SME review and clean cross-platform checks remain pending.
