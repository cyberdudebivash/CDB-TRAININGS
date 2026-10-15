"""ticketapi - a small, typed, authenticated HTTP service for support tickets (PY-M10 guided lab, public reference solution).

Resource: /tickets. Callers present a bearer token (a signed JWT issued by an identity provider; here `issue_token` plays that role in tests). Three roles:
reader (creates and sees only their own tickets), agent (sees every ticket, changes status and assignee), admin (everything, including delete).

Layers: `Settings` (configuration, fail closed) -> tokens (`issue_token`, `verify_token`) -> `TicketRepo` (parameterised SQL, ownership enforced in the query)
-> `create_app` (routes, validation, authorisation, problem+json errors, hardening middleware). Standard library, FastAPI, pydantic and PyJWT only.
"""
from __future__ import annotations

import logging
import re
import secrets
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast

import jwt
from jwt.exceptions import InvalidJTIError, InvalidSubjectError
from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

audit = logging.getLogger("ticketapi.audit")

Role = Literal["reader", "agent", "admin"]
Priority = Literal["low", "normal", "high", "urgent"]
Status = Literal["open", "pending", "resolved", "closed"]
ROLES: tuple[str, ...] = ("reader", "agent", "admin")
STAFF: frozenset[str] = frozenset({"agent", "admin"})
MAX_TICKET_ID = 2**31 - 1                                  # SQLite integers are 64 bit, but an id this large is never legitimate (and sqlite3 raises OverflowError above 2**63 - 1)
_SUBJECT = r"[A-Za-z0-9_.@-]{1,64}"
SUBJECT = re.compile(_SUBJECT)                                  # used with fullmatch
SUBJECT_FIELD = f"^{_SUBJECT}$"                                 # pydantic's `pattern` is a SEARCH: without the anchors "bad name" would match through its first three letters
REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
MAX_LIFETIME = 3600                                        # seconds between iat and exp that a token may claim
IAT_LEEWAY = 30                                            # seconds of clock difference tolerated for iat
UNSAFE_HEADERS = frozenset({"jku", "jwk", "x5u", "x5c"})   # an attacker-supplied place to fetch or embed the verification key (PyJWT itself refuses an unknown `crit` header)
TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"pending", "resolved", "closed"}),
    "pending": frozenset({"open", "resolved", "closed"}),
    "resolved": frozenset({"open", "closed"}),
    "closed": frozenset(),
}


# ------------------------------------------------------------------------------------------------------------------------------------- step 1: settings
class SettingsError(ValueError):
    """The configuration is unusable. The message never contains the secret."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration. `secret` signs and verifies tokens: at least 32 characters, at least 12 different ones. `clock` returns seconds since the epoch (replaced in tests)."""

    secret: str = field(repr=False)
    db_path: str
    issuer: str = "ticketapi"
    audience: str = "ticketapi-clients"
    token_ttl: int = 900
    max_body: int = 16_384
    expose_schema: bool = False
    clock: Callable[[], float] = time.time

    def __post_init__(self) -> None:
        """Refuse unusable settings with SettingsError, and never quote the secret in the message: a `secret` that is not a str of at least 32 characters with at least 12 different
        ones; an empty `db_path`; a `token_ttl` that is not an int (a bool is not one) from 1 to MAX_LIFETIME (3600); a `max_body` that is not an int from 1 to 1000000."""
        if not isinstance(self.secret, str) or len(self.secret) < 32 or len(set(self.secret)) < 12:
            raise SettingsError("secret must be a random string of at least 32 characters (at least 12 different ones)")
        if not self.db_path:
            raise SettingsError("db_path must not be empty")
        if isinstance(self.token_ttl, bool) or not isinstance(self.token_ttl, int) or not 1 <= self.token_ttl <= MAX_LIFETIME:
            raise SettingsError(f"token_ttl must be an int from 1 to {MAX_LIFETIME}")
        if isinstance(self.max_body, bool) or not isinstance(self.max_body, int) or not 1 <= self.max_body <= 1_000_000:
            raise SettingsError("max_body must be an int from 1 to 1000000")

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Settings:
        """Settings from TICKETAPI_SECRET (required), TICKETAPI_DB (required) and optionally TICKETAPI_TOKEN_TTL. A missing or invalid value raises SettingsError: the service
        refuses to start instead of falling back to a default secret."""
        secret = environ.get("TICKETAPI_SECRET")
        db_path = environ.get("TICKETAPI_DB")
        if not secret:
            raise SettingsError("TICKETAPI_SECRET is not set")
        if not db_path:
            raise SettingsError("TICKETAPI_DB is not set")
        try:
            ttl = int(environ.get("TICKETAPI_TOKEN_TTL", "900"))
        except ValueError:
            raise SettingsError("TICKETAPI_TOKEN_TTL must be an integer") from None
        return cls(secret=secret, db_path=db_path, token_ttl=ttl)


# ------------------------------------------------------------------------------------------------------------------------------------- step 1: tokens
class AuthError(Exception):
    """A token was refused. `code` says why; it goes to the audit log, never to the client."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: str

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF


def issue_token(settings: Settings, subject: str, role: str) -> str:
    """A signed HS256 token for `subject` with `role`: claims iss, aud, sub, role, iat, exp (now + token_ttl) and a random jti. ValueError for an unknown role or a subject
    that does not match [A-Za-z0-9_.@-]{1,64}."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    if not isinstance(subject, str) or not SUBJECT.fullmatch(subject):
        raise ValueError("subject must match [A-Za-z0-9_.@-]{1,64}")
    now = int(settings.clock())
    claims = {
        "iss": settings.issuer,
        "aud": settings.audience,
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + settings.token_ttl,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(claims, settings.secret, algorithm="HS256")


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def verify_token(settings: Settings, token: str) -> Principal:
    """The Principal a valid token stands for, or AuthError(code).

    Accepted only when: the header says alg HS256 and carries none of UNSAFE_HEADERS; the HMAC signature matches; iss and aud equal the settings; sub, role, iat and exp are
    present; exp and iat (and nbf, when present) are whole numbers; the clock is before exp (a token is expired AT exp) and not before nbf; iat is not more than IAT_LEEWAY seconds
    in the future; exp - iat is at most MAX_LIFETIME; the role is a known role and the subject matches SUBJECT. Codes: malformed, bad_algorithm, unsafe_header, bad_signature,
    wrong_issuer, wrong_audience, bad_claims, expired, not_yet_valid. Time is read from `settings.clock`, never from the token's own idea of now.
    """
    if not isinstance(token, str) or not token or len(token) > 4096:
        raise AuthError("malformed")
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise AuthError("malformed") from None
    if header.get("alg") != "HS256":
        raise AuthError("bad_algorithm")
    if UNSAFE_HEADERS & set(header):
        raise AuthError("unsafe_header")
    try:
        claims = jwt.decode(
            token,
            settings.secret,
            algorithms=["HS256"],
            audience=settings.audience,
            issuer=settings.issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"], "verify_exp": False, "verify_iat": False, "verify_nbf": False},
        )
    except jwt.InvalidSignatureError:
        raise AuthError("bad_signature") from None
    except jwt.InvalidIssuerError:
        raise AuthError("wrong_issuer") from None
    except jwt.InvalidAudienceError:
        raise AuthError("wrong_audience") from None
    except (jwt.MissingRequiredClaimError, InvalidSubjectError, InvalidJTIError):
        raise AuthError("bad_claims") from None
    except jwt.PyJWTError:
        raise AuthError("malformed") from None
    exp, iat, subject, role = claims["exp"], claims["iat"], claims["sub"], claims.get("role")
    if not (_whole(exp) and _whole(iat)) or not isinstance(subject, str) or not SUBJECT.fullmatch(subject) or role not in ROLES:
        raise AuthError("bad_claims")
    if exp - iat > MAX_LIFETIME or exp <= iat:
        raise AuthError("bad_claims")
    nbf = claims.get("nbf")
    if nbf is not None and not _whole(nbf):
        raise AuthError("bad_claims")
    now = settings.clock()
    if now >= exp:
        raise AuthError("expired")
    if iat > now + IAT_LEEWAY or (nbf is not None and now < nbf):
        raise AuthError("not_yet_valid")
    return Principal(subject, role)


# ------------------------------------------------------------------------------------------------------------------------------------- step 2: models
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")     # control characters other than tab, newline and carriage return (text typed on Windows has \r\n)
_CONTROL_ANY = re.compile(r"[\x00-\x1f\x7f]")


def _clean(value: str, *, multiline: bool) -> str:
    """Refuse control characters and text that cannot be stored: a lone surrogate (U+D800) parses as JSON but cannot be encoded as UTF-8, and would otherwise surface as a 500."""
    if (_CONTROL if multiline else _CONTROL_ANY).search(value):
        raise ValueError("contains control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("is not valid Unicode text") from None
    return value


class TicketIn(BaseModel):
    """The body of POST /tickets.

    title: text of 3 to 120 characters after stripping, no control character at all. body: 1 to 4000 characters after stripping; tab, newline and carriage return are allowed, other
    control characters are not. Text that cannot be stored (a lone surrogate such as U+D800) is refused. priority: one of low, normal, high, urgent (default normal). Leading and
    trailing white space of the text is stripped. Unknown fields are refused, not ignored (a client cannot set `requester`, `status` or `id`), and nothing is coerced: 123 is not a title,
    1 is not a priority, "True" is not a boolean. Length is counted in characters, not bytes.
    """

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    title: Annotated[str, Field(min_length=3, max_length=120)]
    body: Annotated[str, Field(min_length=1, max_length=4000)]
    priority: Priority = "normal"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _clean(value, multiline=False)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _clean(value, multiline=True)


class TicketPatch(BaseModel):
    """The body of PATCH /tickets/{id}: any subset of the fields. Who may change which field is decided in the route, not here.

    title, body and priority have the limits of a new ticket. status is one of open, pending, resolved, closed. assignee is a subject: 1 to 64 of A-Z a-z 0-9 . _ @ - (pydantic's
    `pattern` is a SEARCH, so anchor it with ^ and $). Unknown fields are refused and nothing is coerced. `changes()` lists the fields the client SENT, including a field sent as null.
    """

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    title: Annotated[str, Field(min_length=3, max_length=120)] | None = None
    body: Annotated[str, Field(min_length=1, max_length=4000)] | None = None
    priority: Priority | None = None
    status: Status | None = None
    assignee: Annotated[str, Field(pattern=SUBJECT_FIELD)] | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return None if value is None else _clean(value, multiline=False)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str | None) -> str | None:
        return None if value is None else _clean(value, multiline=True)

    def changes(self) -> dict[str, Any]:
        """The fields the client actually sent (an explicit null counts as sent and is refused later), in the order the model declares them (a set has no order of its own)."""
        return {name: getattr(self, name) for name in type(self).model_fields if name in self.model_fields_set}


class ListParams(BaseModel):
    """Query parameters of GET /tickets. Unknown parameters are refused rather than ignored.

    status, priority: the values of the ticket fields. requester: a subject (anchored pattern, as above). q: 1 to 50 characters. sort: created, updated or id (default created).
    order: asc or desc (default desc). limit: 1 to 100 (default 20). offset: 0 to 10000 (default 0). A query string has no types, so "5" is accepted for an integer (no `strict`).
    """

    model_config = ConfigDict(extra="forbid")

    status: Status | None = None
    priority: Priority | None = None
    requester: Annotated[str, Field(pattern=SUBJECT_FIELD)] | None = None
    q: Annotated[str, StringConstraints(min_length=1, max_length=50)] | None = None
    sort: Literal["created", "updated", "id"] = "created"
    order: Literal["asc", "desc"] = "desc"
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    offset: Annotated[int, Field(ge=0, le=10_000)] = 0


class TicketOut(BaseModel):
    id: int
    requester: str
    title: str
    body: str
    priority: Priority
    status: Status
    assignee: str | None
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[TicketOut]
    total: int
    limit: int
    offset: int


class FieldError(BaseModel):
    loc: list[str | int]
    code: str


class Problem(BaseModel):
    """RFC 9457 problem details (media type application/problem+json) with two extension members: `code` and `request_id`."""

    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str
    request_id: str
    errors: list[FieldError] | None = None


@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    requester: str
    title: str
    body: str
    priority: Priority
    status: Status
    assignee: str | None
    created_at: int
    updated_at: int

    def to_out(self) -> TicketOut:
        return TicketOut(
            id=self.id,
            requester=self.requester,
            title=self.title,
            body=self.body,
            priority=self.priority,
            status=self.status,
            assignee=self.assignee,
            created_at=datetime.fromtimestamp(self.created_at, UTC),
            updated_at=datetime.fromtimestamp(self.updated_at, UTC),
        )


# ------------------------------------------------------------------------------------------------------------------------------------- step 3: repository
SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    requester  TEXT    NOT NULL,
    title      TEXT    NOT NULL CHECK (length(title) BETWEEN 3 AND 120),
    body       TEXT    NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
    priority   TEXT    NOT NULL CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status     TEXT    NOT NULL CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
    assignee   TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_requester ON tickets (requester, id);
"""
COLUMNS = "id, requester, title, body, priority, status, assignee, created_at, updated_at"
SELECT = f"SELECT {COLUMNS} FROM tickets"  # noqa: S608 - COLUMNS is the constant above; no caller-supplied text reaches a statement except as a `?` parameter
COUNT = "SELECT COUNT(*) FROM tickets"
UPDATABLE = ("title", "body", "priority", "status", "assignee")
SORT_COLUMNS = {"created": "created_at", "updated": "updated_at", "id": "id"}
ORDERS = {"asc": "ASC", "desc": "DESC"}


def _like(text: str) -> str:
    """`text` as a LIKE pattern that matches it literally anywhere: the wildcards % and _ and the escape character itself are escaped (ESCAPE '\\')."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _ticket(row: sqlite3.Row) -> Ticket:
    return Ticket(*(row[name] for name in ("id", "requester", "title", "body", "priority", "status", "assignee", "created_at", "updated_at")))


class TicketRepo:
    """Tickets in a SQLite file. Every method opens its own short-lived connection (requests run in a thread pool; a connection must not be shared between threads), all
    values travel as `?` parameters, and anything that becomes part of the SQL text (column names, sort direction) comes from a fixed table, never from the caller."""

    def __init__(self, path: str) -> None:
        self._path = path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        """Create the table and index when missing. Safe to call any number of times."""
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def create(self, requester: str, data: TicketIn, now: int) -> Ticket:
        """Store a new open ticket and return it."""
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO tickets (requester, title, body, priority, status, assignee, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', NULL, ?, ?)",
                (requester, data.title, data.body, data.priority, now, now),
            )
            row = conn.execute(SELECT + " WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _ticket(row)

    def get(self, ticket_id: int, *, requester: str | None = None) -> Ticket | None:
        """The ticket, or None when it does not exist or, with `requester`, belongs to someone else (the two cases are indistinguishable by design)."""
        sql = SELECT + " WHERE id = ?"
        args: list[Any] = [ticket_id]
        if requester is not None:
            sql += " AND requester = ?"
            args.append(requester)
        with closing(self._connect()) as conn:
            row = conn.execute(sql, args).fetchone()
        return None if row is None else _ticket(row)

    def search(
        self,
        *,
        requester: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        q: str | None = None,
        sort: str = "created",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Ticket], int]:
        """(one page of tickets, total number of matches). Filters combine with AND; `q` is a literal substring of the title or body. Ordered by `sort` and `order`, ties
        by id in the same direction, so paging is stable. ValueError for a `sort` or `order` that is not in the fixed tables."""
        if sort not in SORT_COLUMNS or order not in ORDERS:
            raise ValueError("unknown sort or order")
        where: list[str] = []
        args: list[Any] = []
        for column, value in (("requester", requester), ("status", status), ("priority", priority)):
            if value is not None:
                where.append(f"{column} = ?")
                args.append(value)
        if q is not None:
            where.append("(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')")
            args.extend([_like(q), _like(q)])
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        direction = ORDERS[order]
        with closing(self._connect()) as conn:
            total = conn.execute(COUNT + clause, args).fetchone()[0]
            rows = conn.execute(
                f"{SELECT}{clause} ORDER BY {SORT_COLUMNS[sort]} {direction}, id {direction} LIMIT ? OFFSET ?",
                [*args, limit, offset],
            ).fetchall()
        return [_ticket(r) for r in rows], total

    def update(self, ticket_id: int, changes: Mapping[str, Any], now: int, *, only_status: str | None = None) -> Ticket | None:
        """Apply `changes` (keys from UPDATABLE) and set updated_at to `now`; with `only_status` the ticket must still have that status, checked in the same statement so
        two requests cannot both pass a check made earlier. Returns the new ticket, or None when no row matched. ValueError for an empty `changes` or an unknown key."""
        if not changes or set(changes) - set(UPDATABLE):
            raise ValueError("changes must be a non-empty subset of the updatable columns")
        assignments = ", ".join(f"{name} = ?" for name in UPDATABLE if name in changes)
        args: list[Any] = [changes[name] for name in UPDATABLE if name in changes]
        sql = f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?"  # noqa: S608 - `assignments` is built from the constant UPDATABLE, never from the keys the caller sent
        args.extend([now, ticket_id])
        if only_status is not None:
            sql += " AND status = ?"
            args.append(only_status)
        with closing(self._connect()) as conn, conn:
            if conn.execute(sql, args).rowcount == 0:
                return None
            row = conn.execute(SELECT + " WHERE id = ?", (ticket_id,)).fetchone()
        return _ticket(row)

    def delete(self, ticket_id: int) -> bool:
        """True when a ticket was deleted."""
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,)).rowcount == 1


# ------------------------------------------------------------------------------------------------------------------------------------- step 4: errors
SECURITY_HEADERS = (
    (b"cache-control", b"no-store"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
)
_OWNED = {name for name, _ in SECURITY_HEADERS} | {b"x-request-id"}


class ApiError(Exception):
    """An expected failure with the status, machine-readable code and message the client receives."""

    def __init__(self, status: int, code: str, detail: str, *, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(f"{status} {code}")
        self.status = status
        self.code = code
        self.detail = detail
        self.headers = dict(headers or {})


def request_id_of(request: Request | Scope) -> str:
    scope = request.scope if isinstance(request, Request) else request
    return str(scope.get("state", {}).get("request_id", "-"))


TITLES = {
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict", 411: "Length Required",
    413: "Content Too Large", 422: "Unprocessable Content", 500: "Internal Server Error", 503: "Service Unavailable",
}      # written out: http.HTTPStatus renamed 413 and 422 in Python 3.13, and an API contract must not change with the interpreter


def hardening_headers(request_id: str) -> dict[str, str]:
    return {"X-Request-ID": request_id, **{name.decode(): value.decode() for name, value in SECURITY_HEADERS}}


def problem(request: Request | Scope, status: int, code: str, detail: str, *, errors: list[dict[str, Any]] | None = None, headers: Mapping[str, str] | None = None) -> JSONResponse:
    """An application/problem+json response with the RFC 9457 members title (from TITLES), status, detail and type, plus `code`, `request_id` and (for validation) `errors`. It
    carries the request id and the security headers itself, because a response built by a layer outside the middleware (a 500) never passes through the middleware."""
    rid = request_id_of(request)
    body: dict[str, Any] = {"type": "about:blank", "title": TITLES.get(status, "Error"), "status": status, "code": code, "detail": detail, "request_id": rid}
    if errors is not None:
        body["errors"] = errors
    merged = {name.lower(): value for name, value in hardening_headers(rid).items()}
    merged.update({name.lower(): value for name, value in (headers or {}).items()})          # header names are case-insensitive: one entry per name, the caller's value wins
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=merged)


_IDENTIFIER = re.compile(r"[A-Za-z0-9_]{1,40}")


def _loc_part(part: Any) -> str | int:
    """A position (a list index) as it is; a name only when it is a plain identifier. The name of an unknown field is something the client typed: echoing it would hand a hostile client
    a free reflection of arbitrary text (a log-injection or a phishing string in our answer). A typo such as `owner` is still reported."""
    if isinstance(part, int):
        return part
    text = str(part)
    return text if _IDENTIFIER.fullmatch(text) else "?"


def field_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Where each validation error is (`loc`, see _loc_part) and what kind it is (`code`): never the value the client sent, never pydantic's message (which can quote it)."""
    return [{"loc": [_loc_part(part) for part in error["loc"]], "code": str(error["type"])} for error in exc.errors()]


async def _api_error(request: Request, exc: Exception) -> Response:
    error = cast(ApiError, exc)
    return problem(request, error.status, error.code, error.detail, headers=error.headers)


async def _validation_error(request: Request, exc: Exception) -> Response:
    """The 422 problem for a request that failed validation: code `validation_error`, detail "The request is not valid.", errors from field_errors()."""
    return problem(request, 422, "validation_error", "The request is not valid.", errors=field_errors(cast(RequestValidationError, exc)))


_PHRASES = {404: ("not_found", "No such resource."), 405: ("method_not_allowed", "That method is not allowed here.")}


def allowed_methods(request: Request) -> str:
    """The methods the application has for the path of `request`, sorted and joined by ', ' (the value of the Allow header of a 405). Starlette's own Allow header lists only the
    methods of the FIRST route that matches the path, which for a path with a GET and a POST route is wrong; so the routes are asked again."""
    methods: set[str] = set()
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match != Match.NONE:
            methods.update(getattr(route, "methods", None) or ())
    return ", ".join(sorted(methods))


async def _http_error(request: Request, exc: Exception) -> Response:
    """The problem for an HTTP error raised by the framework (an unknown route, a method that is not allowed): the exception's status; code and detail from _PHRASES, or `http_error`
    and the title of the status; the exception's own headers; and, for a 405, the Allow header from allowed_methods()."""
    error = cast(StarletteHTTPException, exc)
    code, detail = _PHRASES.get(error.status_code, ("http_error", TITLES.get(error.status_code, "Error")))
    headers = dict(error.headers or {})
    if error.status_code == 405:
        headers["Allow"] = allowed_methods(request)
    return problem(request, error.status_code, code, detail, headers=headers)


async def _unexpected(request: Request, exc: Exception) -> Response:
    """The answer to an exception nobody expected: a 500 problem with code `internal_error` and a generic detail. The audit log gets one ERROR record (event `error`, the request id,
    and the TYPE of the exception in the message, never the exception's own text, which may quote data); the client gets no detail at all."""
    audit.error("unhandled %s", type(exc).__name__, extra={"event": "error", "request_id": request_id_of(request)})
    return problem(request, 500, "internal_error", "Something went wrong. Quote the request id when you report it.")


# ------------------------------------------------------------------------------------------------------------------------------------- step 7: hardening at the edge


def header_values(scope: Scope, name: bytes) -> list[bytes]:
    """Every value of the request header `name` (lower case, as ASGI delivers names), in order; a header sent twice gives two values."""
    return [value for key, value in scope["headers"] if key.lower() == name]


def pick_request_id(supplied: str | None) -> str:
    """The request id to use: `supplied` (the client's X-Request-ID) when it is exactly 1 to 64 of the characters A-Z a-z 0-9 . _ - ; otherwise, and when there was none, a fresh random
    one (32 lower-case hexadecimal characters). A bad id is replaced, never cleaned up: whatever is left after cleaning would still be the client's text in our headers and logs."""
    if supplied is not None and REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


class Guard:
    """Pure ASGI middleware, outermost layer. For every HTTP request it: settles a request id (the client's X-Request-ID when it matches REQUEST_ID and is sent once, else a fresh
    one), answers 413 when the declared body is larger than `max_body`, 411 for a body with no Content-Length, 400 for a Content-Length that is not a plain number or is sent twice,
    and adds the request id and SECURITY_HEADERS to every response, replacing any value the application set for them."""

    def __init__(self, app: ASGIApp, *, max_body: int) -> None:
        self.app = app
        self.max_body = max_body

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ids = header_values(scope, b"x-request-id")
        rid = pick_request_id(ids[0].decode("latin-1") if len(ids) == 1 else None)
        scope.setdefault("state", {})["request_id"] = rid

        async def guarded_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                kept = [(k, v) for k, v in message["headers"] if k.lower() not in _OWNED]
                message["headers"] = [*kept, (b"x-request-id", rid.encode("ascii")), *SECURITY_HEADERS]
            await send(message)

        refusal = self._refusal(scope)
        if refusal is not None:
            status, code, detail = refusal
            await problem(scope, status, code, detail)(scope, receive, guarded_send)
            return
        await self.app(scope, receive, guarded_send)

    def _refusal(self, scope: Scope) -> tuple[int, str, str] | None:
        """None to let the request through, else (status, code, detail) of the refusal: 400 `bad_content_length` for a Content-Length that is not 1 to 12 ASCII digits or that is sent
        more than once; 413 `body_too_large` when the declared length is above `max_body` (equal is fine); 411 `length_required` for POST, PUT or PATCH with a Transfer-Encoding header
        and no Content-Length. Nothing else is refused here."""
        lengths = header_values(scope, b"content-length")
        if lengths:
            length = lengths[0]
            if len(lengths) > 1 or not length.isdigit() or len(length) > 12:
                return 400, "bad_content_length", "Content-Length must be a plain number, sent once."
            if int(length) > self.max_body:
                return 413, "body_too_large", f"The request body is larger than {self.max_body} bytes."
        elif scope["method"] in ("POST", "PUT", "PATCH") and header_values(scope, b"transfer-encoding"):
            return 411, "length_required", "Send a Content-Length header."
        return None


# ------------------------------------------------------------------------------------------------------------------------------------- step 5: authentication and authorisation
bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth", bearerFormat="JWT", description="A token issued by the identity provider.")


def _unauthorised() -> ApiError:
    """The 401 that every authentication failure gets, whatever the reason: ApiError(401, "unauthorised", "Authentication is required.") with the header
    `WWW-Authenticate: Bearer realm="ticketapi"`. The same answer for a missing, an expired and a forged token tells an attacker nothing."""
    return ApiError(401, "unauthorised", "Authentication is required.", headers={"WWW-Authenticate": 'Bearer realm="ticketapi"'})


def current_principal(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal:
    """Authenticate the request or answer 401 with `WWW-Authenticate: Bearer realm="ticketapi"`. The refusal reason is audited, not returned."""
    rid = request_id_of(request)
    if credentials is None:
        audit.warning("auth refused: missing", extra={"event": "auth.refused", "reason": "missing", "request_id": rid})
        raise _unauthorised()
    try:
        principal = verify_token(request.app.state.settings, credentials.credentials)
    except AuthError as exc:
        audit.warning("auth refused: %s", exc.code, extra={"event": "auth.refused", "reason": exc.code, "request_id": rid})
        raise _unauthorised() from None
    request.state.principal = principal
    return principal


CurrentUser = Annotated[Principal, Depends(current_principal)]


def get_repo(request: Request) -> TicketRepo:
    repo: TicketRepo = request.app.state.repo
    return repo


Repo = Annotated[TicketRepo, Depends(get_repo)]
_CANONICAL_ID = re.compile(r"[1-9][0-9]{0,9}")


def _canonical_id(value: Any) -> Any:
    """`value` unchanged, unless it is a str that is not a plain decimal number (1 to 10 digits, no sign, no leading zero, no separator, no space): then ValueError. pydantic reads
    '01', '+1', '1_0', ' 1' and '1.0' as integers, so one ticket would answer on many addresses, and a cache, a log search or a rate limit keyed by path would see many tickets."""
    if isinstance(value, str) and not _CANONICAL_ID.fullmatch(value):
        raise ValueError("not a plain decimal number")
    return value


TicketId = Annotated[int, Path(ge=1, le=MAX_TICKET_ID, description="Ticket id."), BeforeValidator(_canonical_id)]          # the bounds stay in the schema because they come first


def _forbidden(detail: str = "You may not do that.") -> ApiError:
    return ApiError(403, "forbidden", detail)


def _not_found() -> ApiError:
    return ApiError(404, "not_found", "No such ticket.")


def _now(request: Request) -> int:
    return int(request.app.state.settings.clock())


def _visible(repo: TicketRepo, principal: Principal, ticket_id: int) -> Ticket:
    """The ticket if the caller may see it, else the same 404 as for a ticket that does not exist (object-level authorisation, enforced in the query)."""
    ticket = repo.get(ticket_id, requester=None if principal.is_staff else principal.subject)
    if ticket is None:
        raise _not_found()
    return ticket


def check_patch(principal: Principal, ticket: Ticket, changes: Mapping[str, Any]) -> None:
    """Field-level rules for PATCH, raising ApiError, checked in this order: an explicit null is 400 `null_not_allowed`; a closed ticket accepts no change from anyone (409
    `ticket_closed`); a reader may change only title, body and priority (403 for another field) and only while the ticket is open (409 `ticket_not_open`); `status` and
    `assignee` are for staff; a status change to another status must be a step in TRANSITIONS (409 `invalid_transition`)."""
    if any(value is None for value in changes.values()):
        raise ApiError(400, "null_not_allowed", "A field cannot be set to null.")
    if ticket.status == "closed":
        raise ApiError(409, "ticket_closed", "A closed ticket cannot be changed.")
    if not principal.is_staff:
        if set(changes) - {"title", "body", "priority"}:
            raise _forbidden("Only staff may change status or assignee.")
        if ticket.status != "open":
            raise ApiError(409, "ticket_not_open", "Only an open ticket can be edited by its requester.")
    new_status = changes.get("status")
    if new_status is not None and new_status != ticket.status and new_status not in TRANSITIONS[ticket.status]:
        raise ApiError(409, "invalid_transition", f"A {ticket.status} ticket cannot become {new_status}.")


# ------------------------------------------------------------------------------------------------------------------------------------- step 6: the endpoints
COMMON_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": Problem, "description": "No valid bearer token."},
    422: {"model": Problem, "description": "The request is not valid."},
}


def create_app(settings: Settings) -> FastAPI:
    """Build the application: routes, handlers, middleware and the database table. Nothing global: two apps with two settings never share state."""
    repo = TicketRepo(settings.db_path)
    repo.init()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.ready = True
        audit.info("started", extra={"event": "lifecycle.start"})
        try:
            yield
        finally:
            app.state.ready = False
            audit.info("stopped", extra={"event": "lifecycle.stop"})

    app = FastAPI(
        title="Ticket API",
        version="1.0.0",
        summary="Support tickets with role-based access.",
        lifespan=lifespan,
        redirect_slashes=False,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.expose_schema else None,
    )
    app.state.settings = settings
    app.state.repo = repo
    app.state.ready = False
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected)

    @app.get("/healthz", tags=["ops"], summary="Liveness")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["ops"], summary="Readiness", responses={503: {"model": Problem, "description": "Not started or shutting down."}})
    def readyz(request: Request) -> Response:
        if not request.app.state.ready:
            return problem(request, 503, "not_ready", "The service is not ready.")
        return JSONResponse({"status": "ready"})

    @app.post("/tickets", status_code=201, response_model=TicketOut, tags=["tickets"], summary="Open a ticket", responses={**COMMON_ERRORS})
    def create_ticket(data: TicketIn, response: Response, request: Request, user: CurrentUser, store: Repo) -> TicketOut:
        ticket = store.create(user.subject, data, _now(request))
        response.headers["Location"] = f"/tickets/{ticket.id}"
        audit.info("ticket created", extra={"event": "ticket.created", "ticket": ticket.id, "actor": user.subject, "request_id": request_id_of(request)})
        return ticket.to_out()

    @app.get("/tickets", response_model=Page, tags=["tickets"], summary="List tickets", responses={**COMMON_ERRORS, 403: {"model": Problem, "description": "Not allowed."}})
    def list_tickets(params: Annotated[ListParams, Query()], user: CurrentUser, store: Repo) -> Page:
        if user.is_staff:
            requester = params.requester
        elif params.requester is not None and params.requester != user.subject:
            raise _forbidden("Readers see only their own tickets.")
        else:
            requester = user.subject
        items, total = store.search(
            requester=requester, status=params.status, priority=params.priority, q=params.q, sort=params.sort, order=params.order, limit=params.limit, offset=params.offset
        )
        return Page(items=[t.to_out() for t in items], total=total, limit=params.limit, offset=params.offset)

    @app.get("/tickets/{ticket_id}", response_model=TicketOut, tags=["tickets"], summary="Read a ticket", responses={**COMMON_ERRORS, 404: {"model": Problem, "description": "No such ticket."}})
    def read_ticket(ticket_id: TicketId, user: CurrentUser, store: Repo) -> TicketOut:
        return _visible(store, user, ticket_id).to_out()

    @app.patch(
        "/tickets/{ticket_id}",
        response_model=TicketOut,
        tags=["tickets"],
        summary="Change a ticket",
        responses={**COMMON_ERRORS, 400: {"model": Problem}, 403: {"model": Problem}, 404: {"model": Problem}, 409: {"model": Problem}},
    )
    def patch_ticket(ticket_id: TicketId, patch: TicketPatch, request: Request, user: CurrentUser, store: Repo) -> TicketOut:
        changes = patch.changes()
        if not changes:
            raise ApiError(400, "empty_patch", "Send at least one field.")
        ticket = _visible(store, user, ticket_id)
        check_patch(user, ticket, changes)
        updated = store.update(ticket_id, changes, _now(request), only_status=ticket.status)
        if updated is None:
            raise ApiError(409, "conflict", "The ticket changed while you were editing it; read it again.")
        audit.info("ticket updated", extra={"event": "ticket.updated", "ticket": ticket_id, "actor": user.subject, "fields": sorted(changes), "request_id": request_id_of(request)})
        return updated.to_out()

    @app.delete("/tickets/{ticket_id}", status_code=204, tags=["tickets"], summary="Delete a ticket", responses={**COMMON_ERRORS, 403: {"model": Problem}, 404: {"model": Problem}})
    def delete_ticket(ticket_id: TicketId, request: Request, user: CurrentUser, store: Repo) -> Response:
        if user.role != "admin":
            raise _forbidden("Only an admin may delete tickets.")
        if not store.delete(ticket_id):
            raise _not_found()
        audit.info("ticket deleted", extra={"event": "ticket.deleted", "ticket": ticket_id, "actor": user.subject, "request_id": request_id_of(request)})
        return Response(status_code=204)

    def contract() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, summary=app.summary, routes=app.routes)
            for path in schema["paths"].values():
                for operation in path.values():
                    for status, response in operation["responses"].items():
                        if status.isdigit() and int(status) >= 400 and "application/json" in response.get("content", {}):
                            response["content"] = {"application/problem+json": response["content"]["application/json"]}
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = contract  # type: ignore[method-assign]
    app.add_middleware(Guard, max_body=settings.max_body)
    return app


def app_from_env() -> Any:
    """Factory for an ASGI server (`uvicorn --factory ticketapi:app_from_env`): settings from the environment, refusing to start without a real secret."""
    import os

    return create_app(Settings.from_env(os.environ))
