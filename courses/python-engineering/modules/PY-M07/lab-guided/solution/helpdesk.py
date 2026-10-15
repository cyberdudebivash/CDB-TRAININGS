"""helpdesk - small helper functions of an internal help-desk tool (PY-M07 guided lab; the secure reference version)."""
from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import ssl
from pathlib import Path

import yaml

# ----------------------------------------------------------------------------------------------- calculator
_MAX_EXPRESSION = 100
_BINARY = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
           ast.Div: lambda a, b: a / b, ast.Mod: lambda a, b: a % b}


def _number(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    raise ValueError("only numbers are allowed")


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        exponent = _number(node.right)
        if not float(exponent).is_integer() or not 0 <= exponent <= 64:
            raise ValueError("exponent must be a whole number from 0 to 64")
        return _evaluate(node.left) ** int(exponent)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        try:
            return _BINARY[type(node.op)](_evaluate(node.left), _evaluate(node.right))
        except ZeroDivisionError:
            raise ValueError("division by zero") from None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    return _number(node)


def calculate(expression: str) -> int | float:
    """Evaluate an arithmetic expression: numbers, + - * / %, unary signs, parentheses and ** with a small whole exponent."""
    if not isinstance(expression, str) or len(expression) > _MAX_EXPRESSION:
        raise ValueError("expression must be text of at most 100 characters")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, RecursionError, MemoryError, ValueError) as exc:
        raise ValueError("not an arithmetic expression") from exc
    return _evaluate(tree.body)


# ----------------------------------------------------------------------------------------------- database
def find_users(conn: sqlite3.Connection, name: str) -> list[tuple]:
    """Rows (name, email, role) of users whose name equals `name` exactly."""
    cursor = conn.execute("SELECT name, email, role FROM users WHERE name = ?", (name,))
    return cursor.fetchall()


# ----------------------------------------------------------------------------------------------- files
def list_files(directory: str) -> list[str]:
    """Sorted names in `directory`. FileNotFoundError / NotADirectoryError when it does not exist or is not a directory."""
    if not os.path.isdir(directory):
        raise NotADirectoryError(directory)
    return sorted(os.listdir(directory))


def read_attachment(base: str | Path, filename: str) -> bytes:
    """Contents of `filename` inside the attachment folder `base`. ValueError('invalid attachment name') if it would leave the folder."""
    base_path = Path(base).resolve()
    target = (base_path / filename).resolve()
    if not target.is_relative_to(base_path) or target == base_path:
        raise ValueError("invalid attachment name")
    return target.read_bytes()


# ----------------------------------------------------------------------------------------------- serialisation
_ROLES = {"viewer", "agent", "admin"}


def _validate_session(data: object) -> dict:
    if (not isinstance(data, dict) or set(data) != {"user", "role"} or not isinstance(data["user"], str)
            or not 1 <= len(data["user"]) <= 64 or data["role"] not in _ROLES):
        raise ValueError("invalid session")
    return data


def dump_session(data: dict) -> bytes:
    """Serialise a session {'user': str, 'role': 'viewer'|'agent'|'admin'} as JSON bytes."""
    return json.dumps(_validate_session(data), sort_keys=True).encode("utf-8")


def load_session(blob: bytes) -> dict:
    """Parse session bytes produced by dump_session. ValueError('invalid session') for anything else."""
    try:
        data = json.loads(blob.decode("utf-8"))
    except ValueError as exc:
        raise ValueError("invalid session") from exc
    return _validate_session(data)


def load_config(text: str) -> dict:
    """Parse a YAML document that must be a mapping. ValueError('invalid configuration') otherwise."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError("invalid configuration") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid configuration")
    return data


# ----------------------------------------------------------------------------------------------- transport and secrets
def make_tls_context() -> ssl.SSLContext:
    """TLS client context used for calls to the ticket API: certificates and host names must be verified."""
    return ssl.create_default_context()


_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def hash_password(password: str) -> str:
    """Return 'scrypt$<salt hex>$<hash hex>' using a fresh random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """True only if `password` matches `stored`; malformed stored values return False."""
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return hmac.compare_digest(actual, expected)
