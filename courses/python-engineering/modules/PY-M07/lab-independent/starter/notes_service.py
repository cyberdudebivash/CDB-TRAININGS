"""notes_service - token handling and rendering for a small notes web service (PY-M07 independent lab).

Read the specification in ../README.md. The module works for friendly input; it does not meet the specification for hostile input.
"""
from __future__ import annotations

import logging
import tempfile
import time

import jwt

SECRET = "change-me"
log = logging.getLogger("notes")


def issue_token(user: str, ttl: int = 3600, now: int | None = None) -> str:
    """Signed session token for `user` that expires `ttl` seconds after `now` (default: the current time)."""
    issued = int(time.time()) if now is None else now
    return jwt.encode({"sub": user, "exp": issued + ttl}, SECRET, algorithm="HS256")


def verify_token(token: str) -> str:
    """Return the user name inside a valid, unexpired token. ValueError('invalid token') otherwise."""
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise ValueError("invalid token") from exc
    return claims["sub"]


def render_note(title: str, body: str) -> str:
    """HTML fragment for one note."""
    return f"<article><h1>{title}</h1><p>{body}</p></article>"


def export_notes(notes: list[str]) -> str:
    """Write the notes, one per line, to a new temporary file and return its path."""
    path = tempfile.mktemp(suffix=".txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(notes))
    return path


def log_login(user: str, password: str, ok: bool) -> None:
    """Record a login attempt in the application log."""
    log.info("login user=%s password=%s ok=%s", user, password, ok)


def safe_redirect(target: str) -> str:
    """Where to send the browser after login: `target` when it is a local path, otherwise '/'."""
    return target or "/"
