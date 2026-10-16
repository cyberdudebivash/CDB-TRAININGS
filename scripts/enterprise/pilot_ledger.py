"""Fail-closed, offline evidence ledger for INTERNAL learning pilots.

NOT a hosted LMS, identity provider, commercial offer, certificate issuer or
production multi-tenant API.  Do not expose this class to untrusted callers.
Caller identity must be authenticated by a future independent gateway.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Iterator

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z", re.ASCII)
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
ROLES = frozenset({"admin", "instructor", "learner"})
GENESIS = "0" * 64


class PolicyError(ValueError):
    """Reject an unauthorized or malformed operation without partial mutation."""


def _id(value: str) -> str:
    if type(value) is not str or not ID.fullmatch(value):
        raise PolicyError("invalid opaque identifier")
    return value


def _digest(value: str) -> str:
    if type(value) is not str or not SHA.fullmatch(value):
        raise PolicyError("artifact digest must be lowercase SHA-256 hex")
    return value


def _text(value: str, max_len: int) -> str:
    if type(value) is not str or not (1 <= len(value) <= max_len) or "\x00" in value:
        raise PolicyError("invalid bounded text")
    return value


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _event_hash(tenant: str, previous: str, timestamp: str, event: str, payload: str) -> str:
    return hashlib.sha256(_canonical({"tenant": tenant, "previous": previous, "timestamp": timestamp, "event": event, "payload": payload}).encode("ascii")).hexdigest()


class PilotLedger:
    """Local single-process SQLite pilot with tenant-scoped operations and audit hashes.

    The bootstrap operation is intentionally privileged and must never be put on
    a public API. Callers are trusted *only* after a future upstream identity
    provider validates tenant_id + actor_id; no tokens/passwords are handled here.
    """

    def __init__(self, db_path: str | Path):
        self._connection = sqlite3.connect(str(db_path), isolation_level=None, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._lock = RLock()
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS principals (
                tenant TEXT NOT NULL, id TEXT NOT NULL, role TEXT NOT NULL,
                PRIMARY KEY(tenant,id), FOREIGN KEY(tenant) REFERENCES tenants(id),
                CHECK(role IN ('admin','instructor','learner')));
            CREATE TABLE IF NOT EXISTS cohorts (
                tenant TEXT NOT NULL, id TEXT NOT NULL, course TEXT NOT NULL,
                content_version TEXT NOT NULL, minimum_percent INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'INTERNAL_PILOT',
                PRIMARY KEY(tenant,id), FOREIGN KEY(tenant) REFERENCES tenants(id),
                CHECK(minimum_percent BETWEEN 1 AND 100),
                CHECK(state = 'INTERNAL_PILOT'));
            CREATE TABLE IF NOT EXISTS cohort_instructors (
                tenant TEXT NOT NULL, cohort TEXT NOT NULL, instructor TEXT NOT NULL,
                PRIMARY KEY(tenant,cohort,instructor),
                FOREIGN KEY(tenant,cohort) REFERENCES cohorts(tenant,id),
                FOREIGN KEY(tenant,instructor) REFERENCES principals(tenant,id));
            CREATE TABLE IF NOT EXISTS enrollments (
                tenant TEXT NOT NULL, cohort TEXT NOT NULL, learner TEXT NOT NULL,
                PRIMARY KEY(tenant,cohort,learner),
                FOREIGN KEY(tenant,cohort) REFERENCES cohorts(tenant,id),
                FOREIGN KEY(tenant,learner) REFERENCES principals(tenant,id));
            CREATE TABLE IF NOT EXISTS assignments (
                tenant TEXT NOT NULL, cohort TEXT NOT NULL, id TEXT NOT NULL,
                title TEXT NOT NULL, PRIMARY KEY(tenant,cohort,id),
                FOREIGN KEY(tenant,cohort) REFERENCES cohorts(tenant,id));
            CREATE TABLE IF NOT EXISTS submissions (
                tenant TEXT NOT NULL, cohort TEXT NOT NULL, assignment TEXT NOT NULL,
                learner TEXT NOT NULL, submission_id TEXT NOT NULL, artifact_sha TEXT NOT NULL,
                PRIMARY KEY(tenant,cohort,assignment,learner),
                UNIQUE(tenant,submission_id),
                FOREIGN KEY(tenant,cohort,assignment) REFERENCES assignments(tenant,cohort,id),
                FOREIGN KEY(tenant,cohort,learner) REFERENCES enrollments(tenant,cohort,learner));
            CREATE TABLE IF NOT EXISTS grades (
                tenant TEXT NOT NULL, submission_id TEXT NOT NULL, instructor TEXT NOT NULL,
                score INTEGER NOT NULL, evidence_sha TEXT NOT NULL,
                PRIMARY KEY(tenant,submission_id),
                FOREIGN KEY(tenant,submission_id) REFERENCES submissions(tenant,submission_id),
                FOREIGN KEY(tenant,instructor) REFERENCES principals(tenant,id),
                CHECK(score BETWEEN 0 AND 100));
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL,
                timestamp TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL,
                previous_sha TEXT NOT NULL, current_sha TEXT NOT NULL,
                FOREIGN KEY(tenant) REFERENCES tenants(id));
            CREATE INDEX IF NOT EXISTS audit_tenant ON audit(tenant,seq);
        """)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "PilotLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
                self._connection.execute("COMMIT")
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise

    def _role(self, db: sqlite3.Connection, tenant: str, actor: str, allowed: set[str]) -> str:
        row = db.execute("SELECT role FROM principals WHERE tenant=? AND id=?", (tenant, actor)).fetchone()
        if row is None or row[0] not in allowed:
            raise PolicyError("access denied")
        return row[0]

    def _log(self, db: sqlite3.Connection, tenant: str, event: str, payload: dict) -> str:
        prior = db.execute("SELECT current_sha FROM audit WHERE tenant=? ORDER BY seq DESC LIMIT 1", (tenant,)).fetchone()
        prev_sha = prior[0] if prior else GENESIS
        body = _canonical(payload)
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        digest = _event_hash(tenant, prev_sha, now, event, body)
        db.execute("INSERT INTO audit(tenant,timestamp,event,payload,previous_sha,current_sha) VALUES(?,?,?,?,?,?)",
                   (tenant, now, event, body, prev_sha, digest))
        return digest

    def bootstrap_tenant(self, tenant: str, admin: str) -> None:
        """Trusted offline setup only. NO public endpoint or self-registration."""
        tenant, admin = _id(tenant), _id(admin)
        with self._transaction() as db:
            if db.execute("SELECT 1 FROM tenants WHERE id=?", (tenant,)).fetchone():
                raise PolicyError("tenant already provisioned")
            db.execute("INSERT INTO tenants(id) VALUES(?)", (tenant,))
            db.execute("INSERT INTO principals(tenant,id,role) VALUES(?,?,'admin')", (tenant, admin))
            self._log(db, tenant, "TENANT_PROVISIONED", {"admin": admin})

    def add_principal(self, tenant: str, actor: str, person: str, role: str) -> None:
        tenant, actor, person = _id(tenant), _id(actor), _id(person)
        if type(role) is not str or role not in ROLES or role == "admin":
            raise PolicyError("only nonadmin roles can be assigned in a pilot")
        with self._transaction() as db:
            self._role(db, tenant, actor, {"admin"})
            try:
                db.execute("INSERT INTO principals(tenant,id,role) VALUES(?,?,?)", (tenant, person, role))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("principal already exists or tenant missing") from exc
            self._log(db, tenant, "PRINCIPAL_ADDED", {"actor": actor, "principal": person, "role": role})

    def create_cohort(self, tenant: str, actor: str, cohort: str, course: str,
                      version: str, minimum_percent: int = 85) -> None:
        tenant, actor, cohort, course = map(_id, (tenant, actor, cohort, course))
        version = _text(version, 64)
        if type(minimum_percent) is not int or not 1 <= minimum_percent <= 100:
            raise PolicyError("minimum score must be an integer percentage")
        with self._transaction() as db:
            self._role(db, tenant, actor, {"admin"})
            try:
                db.execute("INSERT INTO cohorts(tenant,id,course,content_version,minimum_percent) VALUES(?,?,?,?,?)",
                           (tenant, cohort, course, version, minimum_percent))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("cohort already exists") from exc
            self._log(db, tenant, "COHORT_CREATED", {"actor": actor, "cohort": cohort, "course": course, "version": version})

    def assign_instructor(self, tenant: str, actor: str, cohort: str, instructor: str) -> None:
        tenant, actor, cohort, instructor = map(_id, (tenant, actor, cohort, instructor))
        with self._transaction() as db:
            self._role(db, tenant, actor, {"admin"})
            self._role(db, tenant, instructor, {"instructor"})
            try:
                db.execute("INSERT INTO cohort_instructors VALUES(?,?,?)", (tenant, cohort, instructor))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("instructor cohort assignment invalid or already exists") from exc
            self._log(db, tenant, "INSTRUCTOR_ASSIGNED", {"actor": actor, "cohort": cohort, "instructor": instructor})

    def _instructor_cohort(self, db: sqlite3.Connection, tenant: str, instructor: str, cohort: str) -> None:
        if not db.execute("SELECT 1 FROM cohort_instructors WHERE tenant=? AND cohort=? AND instructor=?",
                          (tenant, cohort, instructor)).fetchone():
            raise PolicyError("instructor not assigned to cohort")

    def enroll(self, tenant: str, actor: str, cohort: str, learner: str) -> None:
        tenant, actor, cohort, learner = map(_id, (tenant, actor, cohort, learner))
        with self._transaction() as db:
            self._role(db, tenant, actor, {"admin"})
            self._role(db, tenant, learner, {"learner"})
            try:
                db.execute("INSERT INTO enrollments VALUES(?,?,?)", (tenant, cohort, learner))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("enrollment invalid or already exists") from exc
            self._log(db, tenant, "LEARNER_ENROLLED", {"actor": actor, "cohort": cohort, "learner": learner})

    def add_assignment(self, tenant: str, actor: str, cohort: str, assignment: str, title: str) -> None:
        tenant, actor, cohort, assignment = map(_id, (tenant, actor, cohort, assignment))
        title = _text(title, 160)
        with self._transaction() as db:
            role = self._role(db, tenant, actor, {"admin", "instructor"})
            if role == "instructor":
                self._instructor_cohort(db, tenant, actor, cohort)
            try:
                db.execute("INSERT INTO assignments VALUES(?,?,?,?)", (tenant, cohort, assignment, title))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("assignment invalid or duplicate") from exc
            self._log(db, tenant, "ASSIGNMENT_DEFINED", {"actor": actor, "cohort": cohort, "assignment": assignment})

    def submit(self, tenant: str, actor: str, cohort: str, assignment: str,
               submission: str, artifact_sha: str) -> bool:
        tenant, actor, cohort, assignment, submission = map(_id, (tenant, actor, cohort, assignment, submission))
        artifact_sha = _digest(artifact_sha)
        with self._transaction() as db:
            self._role(db, tenant, actor, {"learner"})
            prior = db.execute("SELECT submission_id,artifact_sha FROM submissions WHERE tenant=? AND cohort=? AND assignment=? AND learner=?",
                               (tenant, cohort, assignment, actor)).fetchone()
            if prior:
                if prior == (submission, artifact_sha):
                    return False  # idempotent retry; no second audit event
                raise PolicyError("submission immutable; changed retries rejected")
            try:
                db.execute("INSERT INTO submissions VALUES(?,?,?,?,?,?)", (tenant, cohort, assignment, actor, submission, artifact_sha))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("learner not enrolled, assignment invalid or duplicate submission id") from exc
            self._log(db, tenant, "ARTIFACT_SUBMITTED", {"learner": actor, "cohort": cohort, "assignment": assignment,
                                                        "submission": submission, "artifact_sha": artifact_sha})
            return True

    def grade(self, tenant: str, actor: str, submission: str, score: int, evidence_sha: str) -> None:
        tenant, actor, submission = map(_id, (tenant, actor, submission))
        evidence_sha = _digest(evidence_sha)
        if type(score) is not int or not 0 <= score <= 100:
            raise PolicyError("score must be an integer percentage")
        with self._transaction() as db:
            self._role(db, tenant, actor, {"instructor"})
            row = db.execute("SELECT cohort,learner FROM submissions WHERE tenant=? AND submission_id=?", (tenant, submission)).fetchone()
            if row is None or row[1] == actor:
                raise PolicyError("submission outside authorized scope or self-grading")
            self._instructor_cohort(db, tenant, actor, row[0])
            try:
                db.execute("INSERT INTO grades VALUES(?,?,?,?,?)", (tenant, submission, actor, score, evidence_sha))
            except sqlite3.IntegrityError as exc:
                raise PolicyError("submission already graded") from exc
            self._log(db, tenant, "GRADE_RECORDED", {"instructor": actor, "submission": submission,
                                                    "score": score, "evidence_sha": evidence_sha})

    def progress(self, tenant: str, actor: str, cohort: str, learner: str) -> dict:
        tenant, actor, cohort, learner = map(_id, (tenant, actor, cohort, learner))
        with self._lock:
            db = self._connection
            role = self._role(db, tenant, actor, {"admin", "instructor", "learner"})
            if role == "learner" and actor != learner:
                raise PolicyError("learner cannot inspect another learner")
            if role == "instructor":
                self._instructor_cohort(db, tenant, actor, cohort)
            if not db.execute("SELECT 1 FROM enrollments WHERE tenant=? AND cohort=? AND learner=?",
                              (tenant, cohort, learner)).fetchone():
                raise PolicyError("not enrolled in this cohort")
            row = db.execute("SELECT course,content_version,minimum_percent FROM cohorts WHERE tenant=? AND id=?",
                             (tenant, cohort)).fetchone()
            if row is None:
                raise PolicyError("unknown cohort")
            rows = db.execute("""
               SELECT a.id,s.submission_id,g.score
               FROM assignments a
               LEFT JOIN submissions s ON s.tenant=a.tenant AND s.cohort=a.cohort
                   AND s.assignment=a.id AND s.learner=?
               LEFT JOIN grades g ON g.tenant=s.tenant AND g.submission_id=s.submission_id
               WHERE a.tenant=? AND a.cohort=? ORDER BY a.id
            """, (learner, tenant, cohort)).fetchall()
            done = len(rows)>0 and all(r[2] is not None for r in rows)
            passing = done and all(r[2] >= row[2] for r in rows)
            return {"tenant": tenant, "cohort": cohort, "course": row[0], "content_version": row[1],
                    "learner": learner, "assignments": len(rows), "graded": sum(r[2] is not None for r in rows),
                    "meets_pilot_threshold": passing,
                    "status": "PILOT_ASSIGNMENT_CRITERIA_MET" if passing else "IN_PROGRESS_OR_NOT_PASSED",
                    "course_completed": False, "credential": "NOT_A_CERTIFICATE", "commercial_release": "NOT_AUTHORIZED"}

    def audit_anchor(self, tenant: str, actor: str) -> dict:
        tenant, actor = _id(tenant), _id(actor)
        with self._lock:
            db=self._connection
            self._role(db, tenant, actor, {"admin", "instructor"})
            chain = db.execute("SELECT seq,timestamp,event,payload,previous_sha,current_sha FROM audit WHERE tenant=? ORDER BY seq", (tenant,)).fetchall()
            previous = GENESIS
            for _, timestamp, event, body, prev, sha in chain:
                if prev != previous or sha != _event_hash(tenant, previous, timestamp, event, body):
                    raise PolicyError("audit chain verification failed")
                previous = sha
            return {"tenant": tenant, "events": len(chain), "last_seq": chain[-1][0] if chain else None,
                    "sha256": previous, "security": "LOCAL_UNANCHORED_CHAIN_NOT_A_SIGNATURE"}
