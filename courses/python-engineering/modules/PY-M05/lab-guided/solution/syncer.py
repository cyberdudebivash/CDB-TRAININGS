"""syncer - read settings, fetch a paginated catalogue with timeouts and retries, validate every item, write the result atomically.

PY-M05 guided lab, correct reference version.
"""
from __future__ import annotations

import email.utils
import json
import os
import time
import tomllib
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
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
    """Read a TOML settings file and validate it; FileNotFoundError is not hidden."""
    try:
        with Path(path).open("rb") as handle:                    # tomllib reads bytes and decodes UTF-8 itself
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise SettingsError(f"invalid TOML in {Path(path).name}: {error}") from None
    try:
        return Settings.model_validate(raw)
    except ValidationError as error:
        raise SettingsError(summarise(error)) from None


def write_json_atomic(path: Path, data: object) -> None:
    """Replace `path` with the JSON form of `data`, or leave it exactly as it was."""
    path = Path(path)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"      # serialise first: a bad value must not touch the disk
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


# ----------------------------------------------------------------------------------------------- http
def make_client(settings: Settings, *, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """One shared client: explicit timeouts, no automatic redirects, a User-Agent that names this tool."""
    timeout = httpx.Timeout(settings.timeout_seconds, connect=min(settings.timeout_seconds, 3.0))
    return httpx.Client(base_url=settings.base_url, timeout=timeout, follow_redirects=False, headers={"User-Agent": "catalogsync/1.0"}, transport=transport)


def _retry_after_seconds(value: str | None, now: datetime | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        return float(int(value))
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds())


def delay_for(attempt: int, retry_after: str | None = None, *, now: datetime | None = None) -> float:
    """Seconds to wait after failed attempt number `attempt` (1 for the first)."""
    backoff = min(BACKOFF_CAP, BACKOFF_BASE * 2 ** (attempt - 1))
    asked = _retry_after_seconds(retry_after, now)
    return backoff if asked is None else min(max(backoff, asked), MAX_WAIT)


def _decode_object(response: httpx.Response, url: str) -> dict[str, Any]:
    media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise ApiError(f"expected JSON from {url} but got {media_type or 'no content type'}")
    try:
        payload = json.loads(response.content)
    except ValueError:
        raise ApiError(f"invalid JSON from {url}") from None
    if not isinstance(payload, dict):
        raise ApiError(f"expected a JSON object from {url}")
    return payload


def fetch_json(client: httpx.Client, url: str, *, params: dict[str, Any] | None = None, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """GET `url` and return the decoded JSON object, retrying transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    last = "no attempt made"
    for attempt in range(1, attempts + 1):
        retry_after = None
        try:
            response = client.get(url, params=params)
        except httpx.TransportError as error:                      # timeouts, refused or dropped connections, protocol errors
            last = type(error).__name__
        else:
            if response.status_code in RETRY_STATUS:
                last, retry_after = f"HTTP {response.status_code}", response.headers.get("Retry-After")
            elif response.status_code >= 300:
                raise ApiError(f"HTTP {response.status_code} for {url}")
            else:
                return _decode_object(response, url)
        if attempt < attempts:
            sleep(delay_for(attempt, retry_after))
    raise RetriesExhausted(attempts, last)


def iter_products(client: httpx.Client, *, page_size: int = 50, max_pages: int = 100, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> Iterator[Product]:
    """Yield every product of the catalogue, one page at a time, validating the page and each item."""
    cursor: str | None = None
    seen: set[str] = set()
    page_number = 0
    while True:
        page_number += 1
        if page_number > max_pages:
            raise ApiError(f"more than {max_pages} pages")
        params: dict[str, Any] = {"limit": page_size}
        if cursor is not None:
            params["cursor"] = cursor
        payload = fetch_json(client, "/products", params=params, attempts=attempts, sleep=sleep)
        try:
            page = Page.model_validate(payload)
        except ValidationError as error:
            raise SchemaError(page_number, None, summarise(error)) from None
        for index, raw in enumerate(page.items):
            try:
                product = Product.model_validate(raw)
            except ValidationError as error:
                raise SchemaError(page_number, index, summarise(error)) from None
            yield product
        if page.next_cursor is None:
            return
        if page.next_cursor == cursor or page.next_cursor in seen:
            raise ApiError(f"pagination loop: cursor {page.next_cursor!r} repeated")
        seen.add(page.next_cursor)
        cursor = page.next_cursor


def sync(client: httpx.Client, out_path: Path, *, page_size: int = 50, attempts: int = 4, sleep: Callable[[float], None] = time.sleep) -> int:
    """Fetch the whole catalogue and write it, sorted by id, to `out_path`; the file is replaced only if everything succeeded."""
    products = sorted(iter_products(client, page_size=page_size, attempts=attempts, sleep=sleep), key=lambda p: p.id)
    write_json_atomic(out_path, [p.model_dump() for p in products])
    return len(products)
