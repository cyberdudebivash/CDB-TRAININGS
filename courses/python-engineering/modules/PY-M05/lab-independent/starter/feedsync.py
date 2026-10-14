"""feedsync - synchronise a vendor price feed (PY-M05 independent lab). Implement sync_feed to the specification in ../README.md.

The exception classes, the Summary record and the constants are given so that every solution exposes the same names.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

RETRY_STATUS = frozenset({429, 502, 503, 504})
BACKOFF_BASE, BACKOFF_CAP, MAX_WAIT = 0.5, 8.0, 30.0       # seconds: first backoff, backoff ceiling, ceiling for a server's Retry-After
MAX_PAGES = 200
MAX_BODY_BYTES = 1_048_576
REJECT_LIMIT = 0.2                                          # more than this share of invalid items fails the whole run


class FeedError(Exception):
    """The feed could not be synchronised; nothing in the output folder was changed."""


class RejectThresholdExceeded(FeedError):
    def __init__(self, rejected: int, total: int) -> None:
        super().__init__(f"{rejected} of {total} items were invalid (limit {REJECT_LIMIT:.0%})")
        self.rejected = rejected
        self.total = total


@dataclass
class Summary:
    pages: int = 0                  # pages successfully read
    requests: int = 0               # HTTP requests sent, including retries
    retries: int = 0                # times the client waited and tried again
    items_seen: int = 0             # items on all pages, valid or not
    accepted: int = 0               # distinct SKUs written to prices.json
    duplicates_dropped: int = 0     # items dropped because a later or earlier item had the same SKU
    rejected: int = 0               # items that failed validation


def sync_feed(client: httpx.Client, out_dir: Path, *, page_size: int = 100, attempts: int = 5, deadline_seconds: float = 60.0,
              clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep) -> Summary:
    """Download the whole feed from GET /v2/prices and write prices.json, rejects.jsonl and summary.json into `out_dir` (see the README)."""
    raise NotImplementedError
