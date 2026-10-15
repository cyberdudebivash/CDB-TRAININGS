"""Offline contract and negative tests for the PY-M08 persistence reference."""
import math
import tempfile
import unittest
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "solution") if (Path(__file__).resolve().parents[1] / "solution").is_dir() else str(Path(__file__).resolve().parent))
from eventstore import Event, EventStore, IdempotencyConflict

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def event(eid="evt-1", entity="customer-A", kind="created", when=NOW, payload=None):
    return Event(eid, entity, kind, when, {"value": 1} if payload is None else payload)


class EventStoreContract(unittest.TestCase):
    def setUp(self):
        self.store = EventStore()

    def tearDown(self):
        self.store.close()

    def test_insert_and_roundtrip(self):
        self.assertTrue(self.store.append(event()))
        self.assertEqual(self.store.list_for_entity("customer-A"), [event()])

    def test_exact_retry_is_idempotent(self):
        self.assertTrue(self.store.append(event()))
        self.assertFalse(self.store.append(event()))
        self.assertEqual(self.store.count(), 1)

    def test_semantically_equal_payload_retry(self):
        self.store.append(event(payload={"a": 1, "b": 2}))
        self.assertFalse(self.store.append(event(payload={"b": 2, "a": 1})))

    def test_conflicting_retry_raises_and_does_not_mutate(self):
        self.store.append(event())
        with self.assertRaises(IdempotencyConflict):
            self.store.append(event(payload={"value": 99}))
        self.assertEqual(self.store.list_for_entity("customer-A"), [event()])
        self.assertTrue(self.store.append(event("evt-2")))

    def test_sql_injection_is_data_only(self):
        weird = "'; DROP TABLE events; --"
        self.store.append(event("evil", entity=weird))
        self.assertEqual([e.event_id for e in self.store.list_for_entity(weird)], ["evil"])
        self.assertEqual(self.store.count(), 1)

    def test_invalid_fields_rejected(self):
        for bad in ("", "bad\nkey", "x" * 129):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.store.append(event(eid=bad))
        self.assertEqual(self.store.count(), 0)

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.store.append(event(when=datetime(2026, 10, 14)))

    def test_bad_json_values_rejected(self):
        for payload in ({"bad": float("nan")}, {"bad": {1, 2}}, {"bad": math.inf}):
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(ValueError):
                    self.store.append(event(payload=payload))
        self.assertEqual(self.store.count(), 0)

    def test_large_payload_rejected(self):
        with self.assertRaisesRegex(ValueError, "65536"):
            self.store.append(event(payload={"data": "a" * 70000}))

    def test_seek_pagination_stable(self):
        for eid in ("b", "a", "c"):
            self.store.append(event(eid))
        first = self.store.list_for_entity("customer-A", limit=2)
        self.assertEqual([e.event_id for e in first], ["a", "b"])
        rest = self.store.list_for_entity("customer-A", after=(first[-1].occurred_at.isoformat(), first[-1].event_id))
        self.assertEqual([e.event_id for e in rest], ["c"])

    def test_page_size_and_cursor_validation(self):
        for invalid in (0, -1, 101, 1.2, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.store.list_for_entity("customer-A", limit=invalid)
        for cursor in (("not-date", "evt"), ("2026-10-14", "evt"), (None, "evt"), "bad"):
            with self.subTest(cursor=cursor):
                with self.assertRaises(ValueError):
                    self.store.list_for_entity("customer-A", after=cursor)

    def test_normalizes_timezone_to_utc(self):
        offset = timezone(timedelta(hours=5, minutes=30))
        self.store.append(event(when=NOW.astimezone(offset)))
        self.assertEqual(self.store.list_for_entity("customer-A")[0].occurred_at, NOW)

    def test_entities_isolated(self):
        self.store.append(event("evt-1", entity="alpha"))
        self.store.append(event("evt-2", entity="beta"))
        self.assertEqual([e.event_id for e in self.store.list_for_entity("alpha")], ["evt-1"])

    def test_persists_after_reopen(self):
        with tempfile.TemporaryDirectory() as dirname:
            db = Path(dirname) / "events.db"
            with EventStore(db) as first:
                first.append(event())
            with EventStore(db) as second:
                self.assertEqual(second.list_for_entity("customer-A"), [event()])


if __name__ == "__main__":
    unittest.main()
