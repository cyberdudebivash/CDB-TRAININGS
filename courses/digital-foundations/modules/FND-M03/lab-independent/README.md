# FND-M03 independent lab — Synthetic DNS/TCP/TLS/HTTP session diagnosis

**Learning outcomes:** LO1, LO3, LO4. **Estimated time:** 90 minutes. This is an offline reasoning and programming exercise. **No network operations are performed** by the learner's trace classifier.

## Step 1 — Predict stage behavior (LO1)

You are given a fictional ordered list of protocol stages: `DNS`, `TCP`, `TLS`, `HTTP`. Each entry has `stage` and `state` (`OK` or `FAIL`); an HTTP `OK` stage also has an integer `status` in 100..599. A healthy session requires all four `OK` stages and HTTP status in 200..299. A 404 or 503 is a transported HTTP response but not a healthy application result in this introductory contract.

A failure ends the trace; the next stage must not be present. Before writing code, predict what happens when DNS fails, TCP fails, TLS fails, and a server returns HTTP 503. These are simulated observations, **not proof of real DNS resolution or a TLS handshake**.

## Step 2 — Implement the student contract (LO3)

Complete `starter/trace_model.py::diagnose(events)`. Validate input is a nonempty list of at most 100 exact-schema dictionaries, with stages strictly following the defined order. Reject unknown fields, duplicate/out-of-order stages, invalid state, missing required HTTP status, boolean `status`, and HTTP numeric values outside 100..599. The successful result must be `{ 'healthy': bool, 'failed_stage': str | None, 'http_status': int | None }`. If an `HTTP` state is `FAIL`, do not require a status. A non-2xx HTTP status is an HTTP-stage failure with the status preserved.

Start with:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M03/lab-independent/checks -p test_trace_model.py -v
```

The initial starter *intentionally fails*: it is the learner's unfinished task. Your goal is to pass the provided public tests; a hidden instructor suite and real human grading have not been delivered.

## Step 3 — Incident triage handoff (LO4)

Submit a concise synthetic investigation report listing the first failed stage, the observed HTTP status if present, and what the exercise cannot establish (actual root cause, device failures, live source of truth or attribution). Explain why seeing HTTP 503 means a network connection succeeded far enough to receive an HTTP response, yet the application may be unavailable. Never equate this toy trace to a full packet capture or customer monitoring product.
