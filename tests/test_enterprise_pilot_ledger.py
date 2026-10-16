"""Narrow, executed offline pilot controls; not an LMS deployment certification."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from enterprise.pilot_ledger import PilotLedger, PolicyError, GENESIS  # noqa: E402


def sha(body: bytes = b"synthetic artifact") -> str:
    return hashlib.sha256(body).hexdigest()


class PilotLedgerContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "pilot.db"
        self.db = PilotLedger(self.path)
        self.db.bootstrap_tenant("enterprise_a", "owner_a")
        self.db.bootstrap_tenant("enterprise_b", "owner_b")
        for tenant, owner, student, teacher in [
            ("enterprise_a", "owner_a", "learner_a", "trainer_a"),
            ("enterprise_b", "owner_b", "learner_b", "trainer_b"),
        ]:
            self.db.add_principal(tenant, owner, student, "learner")
            self.db.add_principal(tenant, owner, teacher, "instructor")
            self.db.create_cohort(tenant, owner, "cohort_1", "COURSE-PY-ENG", "0.1-preview")
            self.db.assign_instructor(tenant, owner, "cohort_1", teacher)
            self.db.enroll(tenant, owner, "cohort_1", student)
            self.db.add_assignment(tenant, teacher, "cohort_1", "lab_1", "Synthetic log triage")

    def tearDown(self):
        self.db.close()
        self.temporary.cleanup()

    def submit_a(self, submission="s1", value=None):
        return self.db.submit("enterprise_a", "learner_a", "cohort_1", "lab_1", submission, value or sha())

    def grade_a(self, score=90):
        self.db.grade("enterprise_a", "trainer_a", "s1", score, sha(b"review evidence"))

    def test_no_certificate_on_approved_pilot(self):
        self.submit_a(); self.grade_a()
        result = self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")
        self.assertTrue(result["meets_pilot_threshold"])
        self.assertEqual(result["status"], "PILOT_ASSIGNMENT_CRITERIA_MET")
        self.assertFalse(result["course_completed"])
        self.assertEqual(result["credential"], "NOT_A_CERTIFICATE")
        self.assertEqual(result["commercial_release"], "NOT_AUTHORIZED")

    def test_threshold_fails_closed(self):
        self.submit_a(); self.grade_a(score=84)
        self.assertFalse(self.db.progress("enterprise_a", "owner_a", "cohort_1", "learner_a")["meets_pilot_threshold"])

    def test_unsubmitted_student_not_approved(self):
        self.assertFalse(self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")["meets_pilot_threshold"])

    def test_all_assignments_required(self):
        self.submit_a(); self.grade_a()
        self.db.add_assignment("enterprise_a", "trainer_a", "cohort_1", "lab_2", "Incident memo")
        result = self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")
        self.assertFalse(result["meets_pilot_threshold"])
        self.assertEqual(result["graded"], 1)
        self.assertEqual(result["assignments"], 2)

    def test_cross_tenant_student_unreadable(self):
        with self.assertRaises(PolicyError):
            self.db.progress("enterprise_a", "learner_b", "cohort_1", "learner_a")

    def test_cross_tenant_instructor_cannot_grade(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_b", "trainer_b", "s1", 100, sha())

    def test_tenant_admin_cannot_view_other_tenant(self):
        with self.assertRaises(PolicyError):
            self.db.progress("enterprise_b", "owner_a", "cohort_1", "learner_b")

    def test_student_cannot_see_peer(self):
        self.db.add_principal("enterprise_a", "owner_a", "peer_a", "learner")
        self.db.enroll("enterprise_a", "owner_a", "cohort_1", "peer_a")
        with self.assertRaises(PolicyError):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "peer_a")

    def test_students_cannot_grade(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_a", "learner_a", "s1", 100, sha())

    def test_admin_cannot_grade(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_a", "owner_a", "s1", 100, sha())

    def test_unauthorized_student_cannot_create_assignment(self):
        with self.assertRaises(PolicyError):
            self.db.add_assignment("enterprise_a", "learner_a", "cohort_1", "hack", "Out of scope")

    def test_missing_cohort_assignment_fails(self):
        with self.assertRaises(PolicyError):
            self.db.add_assignment("enterprise_a", "trainer_a", "missing", "new", "Synthetic")

    def test_unassigned_instructor_cannot_grade_same_tenant(self):
        self.db.add_principal("enterprise_a", "owner_a", "other_trainer", "instructor")
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_a", "other_trainer", "s1", 100, sha())

    def test_unassigned_instructor_cannot_read_progress(self):
        self.db.add_principal("enterprise_a", "owner_a", "other_trainer", "instructor")
        with self.assertRaises(PolicyError):
            self.db.progress("enterprise_a", "other_trainer", "cohort_1", "learner_a")

    def test_retry_same_submission_no_duplicate_audit(self):
        self.assertTrue(self.submit_a())
        before=self.db.audit_anchor("enterprise_a","owner_a")
        self.assertFalse(self.submit_a())
        after=self.db.audit_anchor("enterprise_a","owner_a")
        self.assertEqual(before,after)

    def test_changed_submissions_immutable(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.submit_a(value=sha(b"tampered"))
        with self.assertRaises(PolicyError):
            self.submit_a(submission="changed_id")

    def test_submission_id_cannot_be_reused(self):
        self.db.add_assignment("enterprise_a", "trainer_a", "cohort_1", "lab_2", "Incident report")
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.submit("enterprise_a", "learner_a", "cohort_1", "lab_2", "s1", sha(b"other"))

    def test_grades_are_immutable(self):
        self.submit_a(); self.grade_a()
        with self.assertRaises(PolicyError):
            self.grade_a(99)

    def test_boolean_score_rejected(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_a","trainer_a","s1",True,sha())

    def test_fractional_score_rejected(self):
        self.submit_a()
        with self.assertRaises(PolicyError):
            self.db.grade("enterprise_a","trainer_a","s1",85.5,sha())

    def test_threshold_not_boolean(self):
        with self.assertRaises(PolicyError):
            self.db.create_cohort("enterprise_a","owner_a","extra","COURSE-PY-ENG","v1",True)

    def test_bad_digest_rejected(self):
        for value in ("abc",sha().upper(),"0"*63,"x"*64):
            with self.subTest(value=value),self.assertRaises(PolicyError):
                self.submit_a(value=value)

    def test_sql_injection_identifier_rejected(self):
        with self.assertRaises(PolicyError):
            self.db.progress("enterprise_a'; DROP TABLE audit; --", "owner_a", "cohort_1", "learner_a")
        self.assertGreater(self.db.audit_anchor("enterprise_a","owner_a")["events"],0)

    def test_provisioning_idempotency_not_silent(self):
        with self.assertRaises(PolicyError):
            self.db.bootstrap_tenant("enterprise_a","attacker")

    def test_privilege_escalation_admin_role_rejected(self):
        with self.assertRaises(PolicyError):
            self.db.add_principal("enterprise_a","owner_a","second_admin","admin")

    def test_another_tenant_cannot_be_enrolled(self):
        with self.assertRaises(PolicyError):
            self.db.enroll("enterprise_a","owner_a","cohort_1","learner_b")

    def test_audit_chain_tracks_append_only_events(self):
        before=self.db.audit_anchor("enterprise_a","owner_a")
        self.submit_a()
        after=self.db.audit_anchor("enterprise_a","owner_a")
        self.assertEqual(after["events"],before["events"]+1)
        self.assertNotEqual(after["sha256"],before["sha256"])
        self.assertEqual(len(after["sha256"]),64)
        self.assertEqual(after["security"],"LOCAL_UNANCHORED_CHAIN_NOT_A_SIGNATURE")

    def test_audit_detects_payload_mutation(self):
        with self.db._transaction() as db:
            db.execute("UPDATE audit SET payload=? WHERE tenant=? AND event='COHORT_CREATED'", ('{"course":"fake"}',"enterprise_a"))
        with self.assertRaisesRegex(PolicyError,"audit chain"):
            self.db.audit_anchor("enterprise_a","owner_a")

    def test_audit_detects_timestamp_mutation(self):
        with self.db._transaction() as db:
            db.execute("UPDATE audit SET timestamp='1970' WHERE tenant=? AND event='COHORT_CREATED'", ("enterprise_a",))
        with self.assertRaisesRegex(PolicyError,"audit chain"):
            self.db.audit_anchor("enterprise_a","owner_a")

    def test_audit_detects_event_label_mutation(self):
        with self.db._transaction() as db:
            db.execute("UPDATE audit SET event='APPROVED' WHERE tenant=? AND event='COHORT_CREATED'", ("enterprise_a",))
        with self.assertRaisesRegex(PolicyError,"audit chain"):
            self.db.audit_anchor("enterprise_a","owner_a")

    def test_grade_row_tamper_cannot_create_passing_progress(self):
        self.submit_a(); self.grade_a(score=10)
        with self.db._transaction() as db:
            db.execute("UPDATE grades SET score=100 WHERE tenant='enterprise_a' AND submission_id='s1'")
        with self.assertRaisesRegex(PolicyError, "state mismatch: grades"):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")
        with self.assertRaisesRegex(PolicyError, "state mismatch: grades"):
            self.db.audit_anchor("enterprise_a", "owner_a")

    def test_grade_deletion_blocks_progress(self):
        self.submit_a(); self.grade_a()
        with self.db._transaction() as db:
            db.execute("DELETE FROM grades WHERE tenant='enterprise_a' AND submission_id='s1'")
        with self.assertRaisesRegex(PolicyError, "state mismatch: grades"):
            self.db.progress("enterprise_a", "owner_a", "cohort_1", "learner_a")

    def test_forged_grade_without_audit_is_rejected(self):
        self.submit_a()
        with self.db._transaction() as db:
            db.execute("INSERT INTO grades VALUES(?,?,?,?,?)", ("enterprise_a", "s1", "trainer_a", 100, sha()))
        with self.assertRaisesRegex(PolicyError, "state mismatch: grades"):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")

    def test_submission_artifact_digest_tamper_is_rejected(self):
        self.submit_a()
        with self.db._transaction() as db:
            db.execute("UPDATE submissions SET artifact_sha=? WHERE tenant='enterprise_a' AND submission_id='s1'", (sha(b'altered'),))
        with self.assertRaisesRegex(PolicyError, "state mismatch: submissions"):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")

    def test_cohort_threshold_tamper_is_rejected(self):
        self.submit_a(); self.grade_a(score=55)
        with self.db._transaction() as db:
            db.execute("UPDATE cohorts SET minimum_percent=1 WHERE tenant='enterprise_a' AND id='cohort_1'")
        with self.assertRaisesRegex(PolicyError, "state mismatch: cohorts"):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")

    def test_assignment_title_tamper_is_rejected(self):
        with self.db._transaction() as db:
            db.execute("UPDATE assignments SET title='Changed after issue' WHERE tenant='enterprise_a' AND id='lab_1'")
        with self.assertRaisesRegex(PolicyError, "state mismatch: assignments"):
            self.db.audit_anchor("enterprise_a", "owner_a")

    def test_role_escalation_sql_tamper_is_rejected(self):
        with self.db._transaction() as db:
            db.execute("UPDATE principals SET role='admin' WHERE tenant='enterprise_a' AND id='learner_a'")
        with self.assertRaisesRegex(PolicyError, "state mismatch: principals"):
            self.db.audit_anchor("enterprise_a", "owner_a")

    def test_unlogged_tenant_insertion_is_rejected(self):
        with self.db._transaction() as db:
            db.execute("INSERT INTO tenants VALUES(?)", ('forged_tenant',))
        with self.assertRaisesRegex(PolicyError, "state mismatch: tenants"):
            self.db.audit_anchor("enterprise_a", "owner_a")

    def test_mutation_is_fail_closed_after_tamper(self):
        self.submit_a()
        with self.db._transaction() as db:
            db.execute("UPDATE submissions SET artifact_sha=? WHERE tenant='enterprise_a' AND submission_id='s1'", (sha(b'adversarial'),))
        with self.assertRaisesRegex(PolicyError, "state mismatch: submissions"):
            self.db.grade("enterprise_a", "trainer_a", "s1", 99, sha())
        with self.assertRaisesRegex(PolicyError, "state mismatch: submissions"):
            self.db.progress("enterprise_a", "learner_a", "cohort_1", "learner_a")

    def test_persisted_ledger_verifies_after_reopen(self):
        self.submit_a(); self.grade_a()
        good = self.db.audit_anchor('enterprise_a', 'owner_a')
        self.db.close(); self.db=PilotLedger(self.path)
        self.assertEqual(good, self.db.audit_anchor('enterprise_a', 'owner_a'))
        self.assertTrue(self.db.progress('enterprise_a', 'learner_a', 'cohort_1', 'learner_a')['meets_pilot_threshold'])

    def test_file_persistence_after_reopening(self):
        self.submit_a()
        self.db.close()
        self.db=PilotLedger(self.path)
        result=self.db.progress("enterprise_a","owner_a","cohort_1","learner_a")
        self.assertEqual(result["graded"],0)
        self.assertGreater(self.db.audit_anchor("enterprise_a","owner_a")["events"],0)

    def test_forged_role_cannot_be_passed_as_argument(self):
        with self.assertRaises(TypeError):
            self.db.grade("enterprise_a","learner_a","s1",100,sha(),role="instructor")

    def test_ungraded_submission_does_not_count_as_completion(self):
        self.submit_a()
        result=self.db.progress("enterprise_a","learner_a","cohort_1","learner_a")
        self.assertEqual(result["graded"],0)
        self.assertFalse(result["meets_pilot_threshold"])


if __name__ == "__main__":
    unittest.main()
