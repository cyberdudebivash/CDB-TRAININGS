"""Checkpoint authentication/rollback negative controls; offline-only synthetic tenants."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from enterprise.audit_checkpoint import (issue, verify, _load_receipt, _read_key_file,
                                          _write_new_receipt, main, PolicyError)
from enterprise.pilot_ledger import PilotLedger

KEY = bytes(range(32))  # SYNTHETIC PUBLIC UNIT TEST KEY. Never an operational key.
DIFFERENT = bytes(reversed(range(32)))

def sha(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cdb-audit-checkpoint-test-')
        self.base = Path(self.tmp.name)
        self.db_path = self.base/'pilot.db'
        self.ledger = PilotLedger(self.db_path)
        self.ledger.bootstrap_tenant('company_a', 'owner_a')
        self.ledger.bootstrap_tenant('company_b', 'owner_b')
        self.ledger.add_principal('company_a', 'owner_a', 'learner_a', 'learner')
        self.ledger.add_principal('company_a', 'owner_a', 'teacher_a', 'instructor')
        self.ledger.create_cohort('company_a', 'owner_a', 'cohort_a', 'COURSE-PY-ENG', '0.1-pilot')
        self.ledger.assign_instructor('company_a', 'owner_a', 'cohort_a', 'teacher_a')
        self.ledger.enroll('company_a', 'owner_a', 'cohort_a', 'learner_a')
        self.ledger.add_assignment('company_a', 'teacher_a', 'cohort_a', 'lab_a', 'Synthetic triage')
        self.ledger.submit('company_a', 'learner_a', 'cohort_a', 'lab_a', 'sub_a', sha('artifact'))
        self.ledger.grade('company_a', 'teacher_a', 'sub_a', 89, sha('evidence'))

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def receipt(self):
        return issue(self.ledger, 'company_a', 'owner_a', KEY, key_id='operator_key_1')

    def validated(self, receipt=None):
        return verify(self.ledger, 'company_a', 'owner_a', KEY, self.receipt() if receipt is None else receipt,
                      expected_key_id='operator_key_1')

    def test_roundtrip_exact_snapshot_and_reopening(self):
        receipt = self.receipt()
        self.assertEqual(self.validated(receipt)['events'], 9)
        self.ledger.close()
        self.ledger = PilotLedger(self.db_path)
        self.assertTrue(self.validated(receipt)['valid'])

    def test_changed_score_rejected_even_if_unkeyed_chain_valid(self):
        receipt = self.receipt()
        self.ledger._connection.execute("UPDATE grades SET score=100 WHERE tenant='company_a'")
        with self.assertRaisesRegex(PolicyError, 'audit/materialized state mismatch'):
            self.validated(receipt)

    def test_rewritten_history_with_valid_unkeyed_chain_is_detected(self):
        receipt = self.receipt()
        db = self.ledger._connection
        db.execute("UPDATE grades SET score=100 WHERE tenant='company_a'")
        # An attacker with FULL SQLite access can rehash the entire unkeyed history.
        import enterprise.pilot_ledger as pl
        prev = {}
        for seq, tenant, stamp, event, body in db.execute('SELECT seq,tenant,timestamp,event,payload FROM audit ORDER BY seq').fetchall():
            if tenant == 'company_a' and event == 'GRADE_RECORDED':
                d = json.loads(body); d['score'] = 100; body = pl._canonical(d)
            ancestor = prev.get(tenant, pl.GENESIS)
            current = pl._event_hash(tenant, ancestor, stamp, event, body)
            db.execute('UPDATE audit SET payload=?,previous_sha=?,current_sha=? WHERE seq=?',
                       (body, ancestor, current, seq))
            prev[tenant] = current
        self.assertEqual(self.ledger.audit_anchor('company_a', 'owner_a')['events'], receipt['events'])
        with self.assertRaisesRegex(PolicyError, 'checkpoint does not match'):
            self.validated(receipt)

    def test_deletion_rollback_to_old_consistent_db_is_detected(self):
        # Take checkpoint, then replace with older still internally consistent state.
        older = self.base/'older.db'
        self.ledger._connection.backup(sqlite3.connect(str(older)))
        self.ledger.add_assignment('company_a', 'teacher_a', 'cohort_a', 'lab_b', 'Another lab')
        later = self.receipt()
        self.ledger.close(); os.replace(older, self.db_path)
        self.ledger = PilotLedger(self.db_path)
        with self.assertRaisesRegex(PolicyError, 'checkpoint does not match'):
            self.validated(later)

    def test_added_event_invalidates_old_receipt(self):
        receipt = self.receipt()
        self.ledger.add_assignment('company_a', 'teacher_a', 'cohort_a', 'lab_b', 'Synthetic follow-up')
        with self.assertRaisesRegex(PolicyError, 'checkpoint does not match'):
            self.validated(receipt)
        self.assertTrue(self.validated(self.receipt())['valid'])

    def test_wrong_key_denied(self):
        with self.assertRaisesRegex(PolicyError, 'authentication failed'):
            verify(self.ledger,'company_a','owner_a',DIFFERENT,self.receipt(),expected_key_id='operator_key_1')

    def test_mac_tamper_denied(self):
        receipt=self.receipt(); receipt['mac']='0'*64
        with self.assertRaisesRegex(PolicyError, 'authentication failed'):
            self.validated(receipt)

    def test_body_tamper_denied(self):
        receipt=self.receipt(); receipt['events']+=1
        with self.assertRaisesRegex(PolicyError, 'authentication failed'):
            self.validated(receipt)

    def test_role_and_cross_tenant_scope(self):
        with self.assertRaisesRegex(PolicyError, 'access denied'):
            issue(self.ledger,'company_a','learner_a',KEY,key_id='operator_key_1')
        with self.assertRaises(PolicyError):
            verify(self.ledger,'company_b','owner_b',KEY,self.receipt(),expected_key_id='operator_key_1')

    def test_wrong_key_id_and_tenant_denied(self):
        with self.assertRaisesRegex(PolicyError, 'wrong tenant or checkpoint key'):
            verify(self.ledger,'company_a','owner_a',KEY,self.receipt(),expected_key_id='wrong_key')

    def test_key_type_and_size_fail_closed(self):
        for key in (b'123', b'a'*31, b'b'*33, 'a'*32, bytearray(32)):
            with self.subTest(key=type(key).__name__,length=len(key)), self.assertRaisesRegex(PolicyError,'exactly 32'):
                issue(self.ledger,'company_a','owner_a',key,key_id='operator_key_1')

    def test_unknown_fields_and_wrong_types_denied(self):
        for name,val in [('events',True),('last_seq',1.5),('sha256','FAKE'),('key_id','../attack'),('version',True)]:
            with self.subTest(name=name),self.assertRaises(PolicyError):
                val_receipt=self.receipt();val_receipt[name]=val
                self.validated(val_receipt)
        extra=self.receipt();extra['production_approved']=True
        with self.assertRaises(PolicyError):self.validated(extra)

    def test_file_private_create_only(self):
        path=self.base/'receipts.json'
        _write_new_receipt(path,self.receipt())
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        self.assertTrue(self.validated(_load_receipt(path))['valid'])
        with self.assertRaisesRegex(PolicyError,'already exists'):_write_new_receipt(path,self.receipt())

    def test_symlink_receipt_rejected(self):
        path=self.base/'receipt.json'
        _write_new_receipt(path,self.receipt())
        link=self.base/'link.json'
        try:link.symlink_to(path)
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(PolicyError,'symlink'):_load_receipt(link)

    @unittest.skipUnless(os.name == 'posix', 'POSIX-only filesystem fixture')
    def test_fifo_receipt_rejected_without_blocking(self):
        fifo = self.base/'untrusted.pipe'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(PolicyError, 'small regular'):
            _load_receipt(fifo)

    def test_duplicate_json_key_rejected(self):
        path=self.base/'duplicate.json'
        path.write_text('{"mac":"a", "mac":"b"}',encoding='utf-8')
        with self.assertRaisesRegex(PolicyError,'duplicate'):_load_receipt(path)

    def test_oversized_receipt_rejected(self):
        path=self.base/'huge.json';path.write_text('x'*4200,encoding='utf-8')
        with self.assertRaisesRegex(PolicyError,'small regular'):_load_receipt(path)

    @unittest.skipUnless(os.name == 'posix', 'POSIX-only secret file contract')
    def test_private_key_file_permission_and_symlink_controls(self):
        path=self.base/'key.bin'; path.write_bytes(KEY)
        os.chmod(path,0o600)
        self.assertEqual(_read_key_file(path),KEY)
        os.chmod(path,0o644)
        with self.assertRaisesRegex(PolicyError,'private'):_read_key_file(path)
        os.chmod(path,0o600)
        link=self.base/'secret-link.bin'
        link.symlink_to(path)
        with self.assertRaises(PolicyError):_read_key_file(link)

    @unittest.skipUnless(os.name == 'posix', 'POSIX-only CLI contract')
    def test_cli_creates_and_verifies_no_false_course_release(self):
        key_file=self.base/'operator.bin';key_file.write_bytes(KEY);os.chmod(key_file,0o600)
        receipt=self.base/'archive.receipt.json'
        common=['--db',str(self.db_path),'--tenant','company_a','--actor','owner_a','--key-file',str(key_file),'--key-id','operator_key_1','--receipt',str(receipt)]
        self.assertEqual(main(['issue',*common]),0)
        self.assertEqual(main(['verify',*common]),0)
        self.assertEqual(main(['issue',*common]),3) # never replace external historical evidence

if __name__=='__main__':unittest.main()
