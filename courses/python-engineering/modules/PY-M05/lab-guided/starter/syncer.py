"""syncer - read settings, fetch a paginated catalogue with timeouts and retries, validate every item, write the result atomically.

PY-M05 guided lab starter: the schemas, errors and constants are given; implement the functions below.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

RETRY_STATUS = frozenset({429, 502, 503, 504})   # transient failures worth another attempt
BACKOFF_BASE = 0.5                               # seconds before the second attempt
BACKOFF_CAP = 8.0                                # the backoff never grows beyond this
MAX_WAIT = 30.0                                  # nor does a server's Retry-After request


# ----------------------------------------------------------------------------------------------- errors
class SettingsError(Exception):
    """The settings file is missing a value, has a bad value, or is not valid TOML."""


class ApiError(Exception):
    """The API answered, but not in a way this client accepts (and retrying would not help)."""


class RetriesExhausted(ApiError):
    def __init__(self, attempts: int, last: str) -> None:
        super().__init__(f"gave up after {attempts} attempts; last failure: {last}")
        self.attempts = attempts


class SchemaError(ApiError):
    def __init__(self, page: int, index: int | None, detail: str) -> None:
        where = f"page {page}" if index is None else f"page {page}, item {index}"
        super().__init__(f"{where}: {detail}")
        self.page = page
        self.index = index


# ----------------------------------------------------------------------------------------------- schemas
class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    base_url: str
    page_size: int = Field(default=50, ge=1, le=100)
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_attempts: int = Field(default=4, ge=1, le=6)

    @field_validator("base_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return value.rstrip("/")


class Product(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")      # exact types for what we use, tolerance for fields we do not

    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    price_cents: int = Field(ge=0)
    currency: Literal["USD", "EUR", "GBP"]
    tags: list[str] = Field(default_factory=list)


class Page(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    items: list[dict[str, Any]]
    next_cursor: str | None            # required: the key must be present, null ends the listing


def summarise(error: ValidationError) -> str:
    """'field: message; other.field: message' - what is wrong and where."""
    return "; ".join(f"{'.'.join(str(part) for part in e['loc']) or '(root)'}: {e['msg']}" for e in error.errors())


# ----------------------------------------------------------------------------------------------- files
def read_settings(path: Path) -> Settings:
    """Read a TOML settings file and validate it with `Settings`.
    Invalid TOML raises SettingsError('invalid TOML in <file name>: ...'); a value the schema rejects raises SettingsError(summarise(error));
    a missing file raises FileNotFoundError (do not hide it)."""
    raise NotImplementedError("step A: read_settings")


def write_json_atomic(path: Path, data: object) -> None:
    """Replace `path` with the JSON form of `data` (UTF-8, indent 2, non-ASCII letters written as themselves, a final newline).
    If anything fails - serialisation, writing or the replacement - the existing file is left exactly as it was and no temporary file remains."""
    raise NotImplementedError("step B: write_json_atomic")


# ----------------------------------------------------------------------------------------------- http
def make_client(settings: Settings, *, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """One shared client: base_url from the settings; timeouts read/write/pool = settings.timeout_seconds and connect = the smaller of that and 3 seconds;
    redirects not followed; header User-Agent: catalogsync/1.0; `transport` passed through (tests use it)."""
    raise NotImplementedError("step C: make_client")


def delay_for(attempt: int, retry_after: str | None = None, *, now: datetime | None = None) -> float:
    """Seconds to wait after failed attempt number `attempt` (1 for the first).
    Backoff: BACKOFF_BASE * 2 ** (attempt - 1), never more than BACKOFF_CAP. A valid Retry-After value (whole seconds, or an HTTP date measured from `now`,
    which defaults to the current UTC time) wins when it is longer than the backoff, but the result is never more than MAX_WAIT.
    A missing, negative, fractional or unparsable Retry-After is ignored. A date in the past means 'no extra wait'."""
    raise NotImplementedError("step D: delay_for")


def fetch_json(client: httpx.Client, url: str, *, params: dict[str, Any] | None = None, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """GET `url` and return the decoded JSON object.
    Retry (up to `attempts` tries in total, calling sleep(delay_for(...)) between tries but not after the last) when the request raises httpx.TransportError
    or the status is in RETRY_STATUS, passing the Retry-After header to delay_for. After the last failed try raise RetriesExhausted(attempts, description of the last failure).
    Do not retry other problems - raise ApiError at once for any other status of 300 or more, for a content type other than application/json,
    for a body that is not valid JSON and for JSON that is not an object. attempts < 1 raises ValueError('attempts must be at least 1')."""
    raise NotImplementedError("step E: fetch_json")


def iter_products(client: httpx.Client, *, page_size: int = 50, max_pages: int = 100, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> Iterator[Product]:
    """Yield every product of the catalogue (GET /products?limit=<page_size>[&cursor=<cursor>]), one page at a time and lazily.
    Validate each page with `Page` and each item with `Product`; a failure raises SchemaError(page number from 1, item index or None for the page itself, summarise(error)).
    Use fetch_json for the requests. A next_cursor of None ends the listing. A cursor that was already seen raises ApiError('pagination loop: ...');
    asking for page max_pages + 1 raises ApiError('more than <max_pages> pages')."""
    raise NotImplementedError("step F: iter_products")


def sync(client: httpx.Client, out_path: Path, *, page_size: int = 50, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> int:
    """Fetch the whole catalogue and write it, sorted by id as a list of dictionaries (Product.model_dump()), to `out_path` with write_json_atomic.
    The file is replaced only if everything succeeded. Returns the number of products written."""
    raise NotImplementedError("step G: sync")
