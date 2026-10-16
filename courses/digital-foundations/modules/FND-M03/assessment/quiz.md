# FND-M03 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | Which stage converts a hostname into addressing information? | A) TLS. B) DNS. C) HTTP status. D) TCP port scanning. |
| Q2 | LO1 | What does a successful HTTP exchange on 127.0.0.1 prove about DNS? | A) An authoritative DNS lookup was performed. B) Public DNS servers are healthy. C) The HTTPS certificate is valid. D) It does not prove that a DNS lookup occurred. |
| Q3 | LO2 | The controlled local server responds HTTP 404. What is accurate? | A) An HTTP response was received; this is not itself a TCP failure. B) The host was unreachable. C) TLS negotiated TLS 1.3. D) A real customer outage is confirmed. |
| Q4 | LO2 | Why is Content-Length relevant to HTTP/1.1? | A) It proves server identity. B) It sets TTL for DNS. C) It supplies body-message length in bytes. D) It always prevents truncation. |
| Q5 | LO3 | What is the first failed stage in the synthetic trace DNS OK, TCP FAIL? | A) DNS. B) TCP. C) TLS. D) HTTP. |
| Q6 | LO3 | Why must a boolean value be rejected as an HTTP status in the independent lab? | A) Python bools are mathematically floats. B) HTTPS forbids zero-length responses. C) It triggers an actual DNS request. D) The contract requires a real integer HTTP status, not True/False. |
| Q7 | LO4 | What is the correct label for the guided lab TCP exchange? | A) Confirmed remote production telemetry. B) Packet-captured internet TLS session. C) Controlled live loopback. D) Simulated DNS query. |
| Q8 | LO4 | Which incident handoff is defensible? | A) Recorded test results, stated missing DNS/TLS observation and limitations. B) Unobserved DNS resolution marked verified. C) HTTP 503 attributed to a specific engineer without evidence. D) Collected customer tokens to prove lab success. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
