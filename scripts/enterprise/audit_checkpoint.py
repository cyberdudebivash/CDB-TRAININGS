"""Offline HMAC checkpoints for internally operated, single-process pilot ledgers.

This is *not* a digital signature, trusted timestamp, cloud archive, or an
enterprise identity system. The operator MUST custody the key and receipt in an
independent trust boundary to detect simultaneous rewrites of SQLite history.
"""
from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

from .pilot_ledger import PilotLedger, PolicyError, _id

KIND = 'CDB_PILOT_AUDIT_HMAC_RECEIPT'
VERSION = 1
DOMAIN = b'CDB-PILOT-RECEIPT-V1\x00'
SCHEMA = frozenset({'kind','version','tenant','events','last_seq','sha256','recorded_at','key_id','mac'})
BODY_KEYS = SCHEMA - {'mac'}


def _body_bytes(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _key(key: bytes) -> bytes:
    if type(key) is not bytes or len(key) != 32:
        raise PolicyError('operator checkpoint HMAC key must be exactly 32 raw bytes')
    return key


def _read_key_file(path: Path) -> bytes:
    """POSIX-only; symlinks/group/world permissions fail closed. Do not log key."""
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise PolicyError('key-file operations require a POSIX system with O_NOFOLLOW')
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
    try:
        fd = os.open(path, flags)
        try:
            mode = os.fstat(fd)
            if not stat.S_ISREG(mode.st_mode) or mode.st_mode & 0o077:
                raise PolicyError('key file must be regular and private (mode 0600 or stricter)')
            with os.fdopen(fd, 'rb', closefd=False) as fh:
                raw = fh.read(33)
        finally:
            os.close(fd)
    except OSError as exc:
        raise PolicyError('key file unavailable or not permitted') from exc
    return _key(raw)


def _require_body(body: dict) -> None:
    if type(body) is not dict or set(body) != BODY_KEYS:
        raise PolicyError('unrecognized checkpoint schema')
    if body['kind'] != KIND or type(body['version']) is not int or body['version'] != VERSION:
        raise PolicyError('unrecognized checkpoint version')
    _id(body['tenant']); _id(body['key_id'])
    if type(body['events']) is not int or body['events'] < 1:
        raise PolicyError('checkpoint must contain at least one audited event')
    if type(body['last_seq']) is not int or body['last_seq'] < 1:
        raise PolicyError('invalid checkpoint sequence number')
    if type(body['sha256']) is not str or len(body['sha256']) != 64 or any(c not in '0123456789abcdef' for c in body['sha256']):
        raise PolicyError('invalid checkpoint fingerprint')
    if type(body['recorded_at']) is not str:
        raise PolicyError('invalid checkpoint timestamp')
    try:
        moment = datetime.fromisoformat(body['recorded_at'])
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError('timezone required')
    except ValueError as exc:
        raise PolicyError('invalid checkpoint timestamp') from exc


def issue(ledger: PilotLedger, tenant: str, actor: str, key: bytes, *, key_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Admin/instructor-scoped checkpoint of audited tenant state, no course signoff."""
    secret = _key(key)
    key_id = _id(key_id)
    anchor = ledger.audit_anchor(_id(tenant), _id(actor))
    moment = datetime.now(timezone.utc) if now is None else now
    if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
        raise PolicyError('timestamp must be timezone-aware')
    body = {'kind': KIND, 'version': VERSION, 'tenant': anchor['tenant'],
            'events': anchor['events'], 'last_seq': anchor['last_seq'],
            'sha256': anchor['sha256'], 'recorded_at': moment.astimezone(timezone.utc).isoformat(timespec='microseconds'),
            'key_id': key_id}
    _require_body(body)
    mac = hmac.new(secret, DOMAIN + _body_bytes(body), hashlib.sha256).hexdigest()
    return {**body, 'mac': mac}


def verify(ledger: PilotLedger, tenant: str, actor: str, key: bytes, receipt: dict[str, Any], *, expected_key_id: str) -> dict:
    """Verify both receipt authentication and **exact** current ledger snapshot."""
    secret = _key(key)
    expected_key_id = _id(expected_key_id)
    if type(receipt) is not dict or set(receipt) != SCHEMA:
        raise PolicyError('unrecognized checkpoint schema')
    body = {k: v for k, v in receipt.items() if k != 'mac'}
    _require_body(body)
    if type(receipt['mac']) is not str or len(receipt['mac']) != 64 or any(c not in '0123456789abcdef' for c in receipt['mac']):
        raise PolicyError('invalid checkpoint authentication code')
    if body['key_id'] != expected_key_id or body['tenant'] != _id(tenant):
        raise PolicyError('wrong tenant or checkpoint key identifier')
    proposed = hmac.new(secret, DOMAIN + _body_bytes(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(proposed, receipt['mac']):
        raise PolicyError('checkpoint authentication failed')
    actual = ledger.audit_anchor(tenant, _id(actor))   # _read_snapshot reconciles all tables
    if any(body[k] != actual[k] for k in ('tenant', 'events', 'last_seq', 'sha256')):
        raise PolicyError('checkpoint does not match the current tenant ledger (rollback/change/stale receipt)')
    return {'valid': True, 'tenant': tenant, 'events': body['events'], 'last_seq': body['last_seq'],
            'sha256': body['sha256'], 'receipt_kind': KIND,
            'decision': 'EXACT_SNAPSHOT_MATCH_ONLY_NOT_AN_EXTERNAL_TIMESTAMP_NOT_A_CERTIFICATE'}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise PolicyError('duplicate JSON key in checkpoint')
        result[name] = value
    return result


def _load_receipt(path: Path) -> dict:
    """Bounded regular-file read. Reject FIFOs, links and path replacement."""
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise PolicyError('receipt-file operations require POSIX O_NOFOLLOW support')
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= 4096:
                raise PolicyError('checkpoint file must be a small regular file, not a symlink')
            with os.fdopen(fd, 'rb', closefd=False) as fh:
                data = fh.read(4097)
            if len(data) > 4096:
                raise PolicyError('checkpoint file exceeds bounded length')
        finally:
            os.close(fd)
    except PolicyError:
        raise
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PolicyError('checkpoint receipt symlink not permitted') from exc
        raise PolicyError('checkpoint file unreadable or not permitted') from exc
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=_reject_duplicate_keys,
                          parse_constant=lambda value: (_ for _ in ()).throw(PolicyError('nonfinite JSON constant')))
    except PolicyError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PolicyError('checkpoint file malformed') from exc


def _write_new_receipt(path: Path, receipt: dict) -> None:
    """Create-only, private file; never overwrite a historical checkpoint."""
    data = (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('utf-8')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise PolicyError('checkpoint destination already exists or is unavailable') from exc
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        try: path.unlink(missing_ok=True)
        finally: raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Offline HMAC checkpoint. Not a digital signature or release approval.')
    p.add_argument('action', choices=('issue', 'verify'))
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--tenant', required=True)
    p.add_argument('--actor', required=True)
    p.add_argument('--key-file', type=Path, required=True, help='32 raw random bytes, private POSIX file outside SQLite and Git')
    p.add_argument('--key-id', required=True)
    p.add_argument('--receipt', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        key = _read_key_file(args.key_file)
        if not args.db.is_file() or args.db.is_symlink():
            raise PolicyError('existing nonsymlink SQLite database required')
        with PilotLedger(args.db) as ledger:
            if args.action == 'issue':
                receipt = issue(ledger, args.tenant, args.actor, key, key_id=args.key_id)
                _write_new_receipt(args.receipt, receipt)
                print('CHECKPOINT ISSUED: copy receipt to independent immutable storage before relying on it')
            else:
                receipt = _load_receipt(args.receipt)
                result = verify(ledger, args.tenant, args.actor, key, receipt, expected_key_id=args.key_id)
                print(json.dumps(result, sort_keys=True))
        return 0
    except (PolicyError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print('CHECKPOINT BLOCKED: ' + str(exc), file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
