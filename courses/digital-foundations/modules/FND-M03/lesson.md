---
id: FND-M03
title: "Networking and HTTP basics"
course: COURSE-FND-DIGITAL
level: 0
audience: "Entry-level technical learners and support analysts"
prerequisites:
  - "FND-M01 file systems and permissions"
  - "FND-M02 command-line fundamentals (or equivalent)"
  - "Python 3.11+ for guided local lab"
estimated_time_hours: {lesson: 3.0, guided_lab: 1.5, independent_lab: 1.5, total: 6.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "Python 3.11+ standard library; local tests use installed interpreter", http: "HTTP/1.1 practice only", tls: "Conceptual only, no TLS exercised"}
last_verified: 2026-10-15
---

# FND-M03 — Networking and HTTP basics

## Learning outcomes

| Outcome | You can demonstrate... |
|---|---|
| **LO1** | The roles of DNS, IP addressing, TCP, TLS, and HTTP in a request pathway, including what is and is not observable in a trace. |
| **LO2** | An actual local HTTP/1.1 exchange over TCP, explaining request method, status, headers, and payload without confusing network and application errors. |
| **LO3** | Safe interpretation of synthetic DNS/TCP/TLS/HTTP failures, without representing fabricated stages as actual captured traffic. |
| **LO4** | A reproducible and privacy-preserving support handoff with concrete evidence, unresolved unknowns, and safe troubleshooting actions. |

The primary objective is reasoning about an authorized customer-support workflow. This module does not certify operational network administration or packet-forensics competence. The labs intentionally use either a controlled *live loopback* exchange or a labeled *synthetic* trace. Those two data types are not interchangeable. No actual DNS or TLS operations, cloud resources, company systems, or personal information are needed.

## 1. Names, addresses, and layered communication (LO1)

A customer tells a support technician that a web application is unreachable. The technician should not immediately assume that the server has crashed. The user's experience depends on several independently fallible operations. The device needs a network path to the destination. If the user starts from a hostname, a resolver typically needs a usable address. The client may establish a TCP connection to the chosen address and port. For an HTTPS URL, a TLS handshake then protects traffic on that connection. Finally, HTTP communicates an application request and response. Each layer answers a different question.

DNS is a naming system, not the same as HTTP. A DNS lookup for a hostname returns data used in addressing, often A or AAAA records, but DNS does not guarantee the destination application is healthy. The client may use cached DNS responses, operating-system name resolution, a configured enterprise resolver, or an encrypted DNS service. Consequently a successful HTTP request does not necessarily prove that a new DNS query happened during the observation window.

An IP address identifies a network-layer endpoint. Common examples include IPv4 and IPv6. A TCP port helps distinguish a listening service on that endpoint. A domain name and a TCP port are not interchangeable: multiple names can resolve to the same address, and one address can serve many applications. Private network configuration, firewalls, DNS caching, VPN routing, container networking and proxies influence what a specific workstation can reach. Never extrapolate your laptop's network view to all customer users without supporting measurements.

An important diagnostic distinction is **where an observation was made**. A browser reports a connection error; a server-side log reports a received request; an API gateway may report another stage. These observations can disagree for legitimate reasons. A missing server log may mean the request never reached the server, or it may mean a logging pipeline failed. Do not invent traffic to fill gaps. Mark unobserved stages as unverified.

The sample classifier distinguishes four stage labels only as an educational model:

```python run
stages = ["DNS", "TCP", "TLS", "HTTP"]
assert stages.index("DNS") < stages.index("HTTP")
assert len(set(stages)) == 4
```

These labels express a common HTTPS conceptual path, not a universal real-world order. For example HTTP/3 normally uses QUIC rather than TCP, TLS can be terminated at a proxy, and an HTTP request over local cleartext does not involve TLS. Our guided lab is the last case: HTTP/1.1 over TCP to 127.0.0.1, with **no DNS lookup** and **no TLS handshake**. Describing it as a full DNS-to-HTTPS trace would be incorrect.

## 2. TCP transport and connection behavior (LO1, LO2)

TCP establishes a connection-oriented byte stream with sequencing and reliability controls. Applications may write byte chunks that arrive in different sized reads: TCP does not preserve application message boundaries. This is why protocols such as HTTP need their own message framing. A TCP connection attempt may fail because the destination is unreachable, the port has no listener, a security device denies traffic, or the application stops accepting connections. A timeout by itself does not identify which explanation is correct.

The IP loopback address 127.0.0.1 points to the local IPv4 host. A program bound only to that address is normally reachable on the same host, not exposed as an internet-facing listener. Binding to 0.0.0.0 can broaden reachability across interfaces depending on firewall and network configuration and is intentionally avoided in this beginner exercise. Our reference server requests port 0 during binding, letting the operating system select a currently available local port, then reports the actual port to the client. Never hardcode a public address or existing production port for this lab.

Connections require lifecycle management. An HTTP test that leaves a server running can interfere with future test runs, even if every assertion once passed. A useful test validates both the successful interaction and cleanup. In our lab the server runs in a daemon thread while a context manager is active; on exit it is shut down, joined, and closed. The client has a bounded timeout. Such controls improve a teaching example but do not constitute availability monitoring or a production concurrency architecture.

```python run
from ipaddress import ip_address
loopback = ip_address("127.0.0.1")
assert loopback.is_loopback
assert not ip_address("203.0.113.10").is_loopback
```

The second address is a documentation-only example, not a target to connect to. An endpoint being public or private does not establish permission to scan it. Do not perform port scanning, packet interception, or unauthorized testing on customer networks in this course.

## 3. TLS and what a trace can actually prove (LO1, LO3)

Transport Layer Security protects HTTP contents in HTTPS, subject to the deployment and trust model. In a simplified case the client and server negotiate cryptographic parameters, authenticate a certificate chain, and establish keys used to protect subsequent traffic. A certificate warning can arise from an expired certificate, hostname mismatch, untrusted issuer, misconfigured clock, inspection proxy or other failure. A connection being encrypted does not, by itself, mean the application is secure or that the business transaction is authorized.

The guided lab does **not** perform TLS. The independent lab contains records labelled `TLS: OK` or `TLS: FAIL`, but those are learner-provided simulated records. They do not prove a real certificate, cipher suite or negotiated session was observed. This distinction is critical in SOC reports: fabricating a certificate subject, timestamp or handshake event because a response was successful would undermine credibility. A professional investigation separates a genuine packet capture, a client error, a simulated lab record and an inference.

If a browser presents a TLS-related error, a good first response is to preserve the sanitized code/message and determine which hostname, trust store, device time and authorized endpoint were involved. Never instruct a customer to permanently disable certificate validation or ignore browser security warnings simply to make a test pass. Doing so may conceal interception or expose sensitive traffic.

```python run
observed = {"tcp_exchange": True, "tls_handshake": False, "http_status": 200}
assert observed["tcp_exchange"]
assert not observed["tls_handshake"]
```

A support handoff should specify the actual observations and state the limitations. Do not describe a local HTTP request as HTTPS; do not state that DNS was resolved during the lab merely because a TCP connection to an address succeeded.

## 4. HTTP requests, response codes, and headers (LO2)

HTTP defines application semantics over a transport. In HTTP/1.1 a basic request includes a method and path, a Host header, and other optional headers. The server responds with a status code, response headers and often a body. The body is typically encoded content such as JSON, HTML, or an image. HTTP/1.1 also requires correct message framing, which may use a Content-Length header or chunked transfer encoding. Our reference is intentionally narrow and always returns bounded JSON with a Content-Length header.

A 200 response usually indicates success for that request. A 404 means the requested resource was not found. A 400 means the server considered the request invalid. A 503 often signals temporary unavailability of an application or intermediary. These are application-protocol observations, not definitive proof about root cause. Receiving 404 means a TCP stream and HTTP exchange worked enough to deliver that response. It cannot be accurately called a TCP connection failure.

Headers have meaning and limits. Content-Type helps a client know how to process a representation; Content-Length states the number of body bytes; Cache-Control influences caching; X-Content-Type-Options may instruct browsers not to reinterpret a declared MIME type. A response header does not guarantee every client or intermediary enforces a desired security outcome. Never infer full application security from a few header values.

```python run
statuses = {200: "ok", 400: "bad-request", 404: "not-found", 503: "service-unavailable"}
assert statuses[404] != statuses[200]
assert 200 <= 200 < 300
assert not (200 <= 503 < 300)
```

An HTTP method affects intended semantics. GET should retrieve a representation and should not be used to intentionally perform unsafe business state changes. Actual applications may violate these expectations, which is a security or design concern rather than permission to probe them. The lab only implements GET and only accepts two literal routes: `/health` and `/missing`. It doesn't fetch arbitrary URLs, crawl hosts or evaluate user-controlled code.

A JSON object is just structured data. A successfully parsed object cannot prove where it came from without independent provenance checks. When a client receives JSON saying `status: ok`, the exact meaning must be established by the service contract and measured health dependencies. Our `/health` route is a teaching fixture, not an enterprise health endpoint checking downstream databases or identity systems.

## 5. Actual controlled local HTTP trace (LO2, LO4)

The guided lab starts a genuine TCP listener bound to loopback, makes HTTP/1.1 requests and captures application-level results. It does not capture packets using Wireshark or tcpdump. Instead the Python HTTP client reports the response status, selected headers and parsed body, and the test harness checks consistency. This is a useful accessible first step before teaching deeper packet observation with proper permissions.

Students execute the [guided lab](lab-guided/README.md) and preserve the test output. Its positive cases verify 200 on `/health` and 404 on `/missing`. Negative tests reject an unapproved path, a full external URL, a traversal path, an invalid port and an excessive timeout. The server also returns 400 for an unknown route and closes after the context exits. Such fail-closed behavior is intentional: learners must not be encouraged to turn a safe demonstration into a general client for arbitrary hosts.

```python run
from urllib.parse import urlsplit
url = urlsplit("http://127.0.0.1:8080/health")
assert url.hostname == "127.0.0.1"
assert url.path == "/health"
assert url.scheme == "http"
```

This code only parses text; it does not issue the request or assert port 8080 is running. The actual test binds a random available port. The runbook must describe the port it used as ephemeral rather than promising it remains available later.

When collecting evidence, identify the source of each field. Our reference result's `transport: tcp-loopback` is a known implementation property. The status is observed from the local HTTP response. The `origin: synthetic-loopback` body value is an application-provided label, not external attestation. The learner should know what a field can prove and what it cannot.

## 6. Synthetic failure-chain interpretation (LO3, LO4)

The [independent exercise](lab-independent/README.md) asks learners to implement an offline classifier over synthetic four-stage traces. For this deliberately simplified HTTPS conceptual model, valid stages appear in order: DNS, TCP, TLS, HTTP. A failure terminates the trace. A complete successful chain ends in HTTP with a 2xx status. The classifier reports the first failed stage and the HTTP status if observed. Invalid order or unexpected fields must be rejected instead of guessed.

This classifier is not a packet parser, live network monitoring service or authoritative troubleshooting oracle. A fabricated `DNS FAIL` record can only establish what the synthetic input says. A real investigation would need source logs, clocks, packet observations and environmental context. Real operations can include retries, multiple addresses, proxies, redirects, QUIC, mTLS and independent DNS caching. The beginner model intentionally excludes those complications and says so explicitly.

Successful students predict how a DNS failure prevents a later TCP step in the simplified chain, how a TCP failure differs from a returned HTTP 503, and why a TLS error cannot be proven from a local cleartext HTTP request. They then implement exact validation, make public tests pass, document invalid traces and describe the limits. The original student starter raises a clear incomplete-task error. An initial failed check is appropriate evidence that the learner has not done the exercise; suppressing that failure would defeat the educational purpose.

## 7. Operator troubleshooting and safety (LO1, LO2, LO3, LO4)

Consider three fictional support tickets. Ticket A reports a browser error saying a hostname could not be resolved. Collect the precise affected hostname and the resolver behavior from an approved tool; avoid claiming the service failed, since no HTTP response was observed. Ticket B receives HTTP 404 for an authorized endpoint. That means the HTTP path was processed far enough to return a response; it suggests checking application routing or resource identity rather than changing DNS blindly. Ticket C receives HTTP 503 intermittently. Gather timestamps, service-side records and the scope of affected users, then coordinate safe troubleshooting. A 503 alone is insufficient for blaming a database or a specific engineer.

Do not install packet-capture drivers, disable TLS verification, scan public ports, inspect other tenants' traffic or collect personally identifying data without authorization. The course does not need any of those operations. When test infrastructure is unavailable, mark tests NOT_EXECUTED and record the actual failure. When a port fails to bind, another process or a local policy may be involved; do not automatically disable a firewall. Select a new authorized practice environment or escalate the limitation.

Quality evidence includes the runtime, operating system, exact commands, actual test counts, response observations and explicit unknowns. It also includes safe cleanup. A vague statement that the lab ran is not enough to establish a learner can distinguish transport and application behavior. A reviewer should check the learner's reasoning, not simply accept the presence of generated output.

## 8. Submission, knowledge check and next steps (LO1, LO2, LO3, LO4)

Complete the [eight-question knowledge check](assessment/quiz.md), execute the guided tests, and implement the independent trace classifier. The instructor's rubric separates executable evidence from a professional support report. Submit a sanitized operational handoff that contains a timeline of what you actually did, results, remaining uncertainty and suggestions for authorized next steps. Do not paste real hostnames, customer names, security credentials, or protected information.

A lesson and its local tests cannot establish complete professional networking competency. FND-M03 belongs to a six-module foundational pathway. Git workflows, introductory Python development and troubleshooting remain separate modules, and the full pathway still needs instructor review, learner pilots, a verified complete PDF edition and independent release approval before any commercial training or Academy deployment.
