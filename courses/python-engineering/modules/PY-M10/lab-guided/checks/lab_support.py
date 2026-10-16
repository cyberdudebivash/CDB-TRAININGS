"""Helpers shared by the PY-M10 guided-lab checks (kept out of conftest.py so that test modules can import them under `--import-mode=importlib`)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

SECRET = "correct-horse-battery-staple-9f2c7d1e4a"          # 38 characters, 20 different ones: a valid signing secret for tests only
T0 = 1_791_979_200                                         # 2026-10-14T12:00:00Z


class Clock:
    """A clock the test controls: calling it returns the current second; .advance() moves it."""

    def __init__(self, start: float = T0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now


def b64(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def forge_token(claims: dict[str, Any], *, secret: str = SECRET, header: dict[str, Any] | None = None, alg: str = "HS256") -> str:
    """A token signed by hand, so that a test can put ANY header or claims in it (the library under test would refuse to issue most of these)."""
    head = {"alg": alg, "typ": "JWT", **(header or {})}
    signing_input = b64(json.dumps(head, separators=(",", ":")).encode()) + b"." + b64(json.dumps(claims, separators=(",", ":")).encode())
    digest = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}.get(alg)
    signature = b"" if digest is None else b64(hmac.new(secret.encode(), signing_input, digest).digest())
    return (signing_input + b"." + signature).decode()


class Api:
    """The service plus a client. Built on first use (see the module docstring)."""

    def __init__(self, ta, tmp_path, clock, **settings) -> None:
        from fastapi.testclient import TestClient

        self.ta = ta
        self.clock = clock
        self.settings = ta.Settings(secret=settings.pop("secret", SECRET), db_path=settings.pop("db_path", str(tmp_path / "tickets.db")), clock=clock, **settings)
        self.app = ta.create_app(self.settings)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def token(self, subject: str = "alice", role: str = "reader") -> str:
        return self.ta.issue_token(self.settings, subject, role)

    def as_(self, subject: str = "alice", role: str = "reader") -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(subject, role)}"}

    def claims(self, **overrides: Any) -> dict[str, Any]:
        """Valid claims for alice (reader) at the current time; keys given as None are removed."""
        now = int(self.clock())
        claims: dict[str, Any] = {"iss": self.settings.issuer, "aud": self.settings.audience, "sub": "alice", "role": "reader", "iat": now, "exp": now + 900}
        claims.update(overrides)
        return {k: v for k, v in claims.items() if v is not None}

    def forged(self, claims: dict[str, Any] | None = None, **kw: Any) -> dict[str, str]:
        return {"Authorization": "Bearer " + forge_token(self.claims() if claims is None else claims, **kw)}

    def new_ticket(self, who: str = "alice", role: str = "reader", title: str = "Printer on fire", body: str = "It smells of smoke.", **extra: Any) -> dict[str, Any]:
        response = self.client.post("/tickets", json={"title": title, "body": body, **extra}, headers=self.as_(who, role))
        assert response.status_code == 201, response.text
        return response.json()

    def __getattr__(self, name: str):
        return getattr(self.client, name)


class LazyApi:
    """Builds the Api when a test first uses it."""

    def __init__(self, ta, tmp_path, clock) -> None:
        self.__dict__["_args"] = (ta, tmp_path, clock)
        self.__dict__["_api"] = None

    def build(self, **settings: Any) -> Api:
        api = Api(*self._args, **settings)
        self.__dict__["_api"] = api
        return api

    def __getattr__(self, name: str):
        if self._api is None:
            self.build()
        return getattr(self._api, name)


class SharedApi:
    """One Api for all the tests of a module, built (and prepared by `prepare(api)`) the first time a test uses it, so that a step you have not written yet is a failed check in each test
    and not a set-up error. Tests using it must only add data, never depend on there being none."""

    def __init__(self, ta, tmp_path, prepare) -> None:
        self.__dict__.update(_ta=ta, _tmp=tmp_path, _prepare=prepare, _api=None)

    def __getattr__(self, name: str):
        if self.__dict__["_api"] is None:
            api = Api(self._ta, self._tmp, Clock())
            self._prepare(api)
            self.__dict__["_api"] = api
        return getattr(self.__dict__["_api"], name)
