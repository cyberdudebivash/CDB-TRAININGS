"""wordjob - count the words of many remote documents. PY-M06 independent lab: implement count_words (async) to the specification in ../README.md.

The result record, the path helper and a sequential baseline are given. The baseline defines what a correct result looks like; your version must return the same
counts and errors for the same server, only faster, and must also handle the situations that the baseline does not (deadline, cancellation, bounded concurrency).
"""
from __future__ import annotations

import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field

import httpx


@dataclass
class JobResult:
    counts: dict[str, int] = field(default_factory=dict)      # document id -> number of words
    errors: dict[str, str] = field(default_factory=dict)      # document id -> reason: "timeout", "connection error", "bad encoding", "HTTP <status>" or "deadline"
    requests: int = 0                                          # HTTP requests started
    elapsed_s: float = 0.0                                     # wall-clock seconds from the call to the return


def doc_path(doc_id: str) -> str:
    """The URL path of a document. The id is opaque text: every character other than an ASCII letter or digit is percent-encoded, so an id can never change the path
    (a plain quote() leaves dots alone, and the ids '.' and '..' would then be resolved away by the URL machinery and reach another path)."""
    return "/docs/" + re.sub(r"[^A-Za-z0-9]", lambda m: "".join(f"%{b:02X}" for b in m.group().encode("utf-8")), str(doc_id))


def count_words_sequential(client: httpx.Client, doc_ids: Iterable[str], *, timeout: float = 2.0) -> JobResult:
    """The baseline: one document after another with a synchronous client. A word is a maximal run of non-whitespace characters (str.split)."""
    started = time.perf_counter()
    result = JobResult()
    for doc_id in dict.fromkeys(str(d) for d in doc_ids):          # each distinct id once
        result.requests += 1
        try:
            response = client.get(doc_path(doc_id), timeout=timeout)
        except httpx.TimeoutException:
            result.errors[doc_id] = "timeout"
            continue
        except httpx.TransportError:
            result.errors[doc_id] = "connection error"
            continue
        if response.status_code != 200:
            result.errors[doc_id] = f"HTTP {response.status_code}"
            continue
        try:
            text = response.content.decode("utf-8")
        except UnicodeDecodeError:
            result.errors[doc_id] = "bad encoding"
            continue
        result.counts[doc_id] = len(text.split())
    result.elapsed_s = time.perf_counter() - started
    return result


async def count_words(client: httpx.AsyncClient, doc_ids: Iterable[str], *, limit: int = 8, timeout: float = 2.0, deadline: float = 30.0) -> JobResult:
    """Fetch every distinct document and count its words, concurrently. See the README for the full specification."""
    raise NotImplementedError
