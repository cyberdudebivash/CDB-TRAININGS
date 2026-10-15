"""Read-only CLI contract checks, including error exit codes and input scope."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "solution"
sys.path.insert(0, str(SRC))
from runbook import scan, main

HEADER = "timestamp,service,severity,message\n"
ROWS = "2026-10-15T10:00:00+00:00,auth,INFO,Started\n2026-10-15T10:01:00+00:00,auth,ERROR,Timeout\n"

class RunbookTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        (self.root / "events.csv").write_text(HEADER + ROWS, encoding="utf-8")
    def test_level_filter(self):
        self.assertEqual([e["severity"] for e in scan(self.root,"events.csv","WARN")], ["ERROR"])
    def test_deterministic_json(self):
        out = subprocess.run([sys.executable, str(SRC/"runbook.py"),"--root",str(self.root),"--input","events.csv"], capture_output=True,text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["count"], 2)
    def test_alert_exit_code(self):
        self.assertEqual(main(["--root",str(self.root),"--input","events.csv","--fail-on-error"]), 3)
    def test_invalid_csv_returns_2(self):
        (self.root/"events.csv").write_text("wrong,header\n",encoding="utf-8")
        self.assertEqual(main(["--root",str(self.root),"--input","events.csv"]),2)
    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError):scan(self.root,"../events.csv")
    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):scan(self.root,str(self.root/"events.csv"))
    def test_unsupported_severity(self):
        (self.root/"events.csv").write_text(HEADER+ROWS.replace("ERROR","CRITICAL"),encoding="utf-8")
        with self.assertRaises(ValueError):scan(self.root,"events.csv")
    def test_missing_timezone_rejected(self):
        (self.root/"events.csv").write_text(HEADER+"2026-10-15T10:00:00,auth,INFO,Started\n",encoding="utf-8")
        with self.assertRaises(ValueError):scan(self.root,"events.csv")
    def test_duplicate_events_rejected(self):
        (self.root/"events.csv").write_text(HEADER+ROWS+ROWS,encoding="utf-8")
        with self.assertRaises(ValueError):scan(self.root,"events.csv")
    def test_empty_csv_allowed_but_zero_events(self):
        (self.root/"events.csv").write_text(HEADER,encoding="utf-8")
        self.assertEqual(scan(self.root,"events.csv"),[])
    def test_symlink_rejected(self):
        (self.root/"alias.csv").symlink_to(self.root/"events.csv")
        with self.assertRaises(ValueError):scan(self.root,"alias.csv")
    def test_oversize_rejected(self):
        (self.root/"events.csv").write_bytes(b"a"*70000)
        with self.assertRaises(ValueError):scan(self.root,"events.csv")
    def test_shell_injection_is_data(self):
        (self.root/"events.csv").write_text(HEADER+"2026-10-15T10:00:00+00:00,auth,WARN,echo harmless; rm -rf ..\n",encoding="utf-8")
        self.assertEqual(len(scan(self.root,"events.csv")),1)
    def test_invalid_utf8_returns_2(self):
        (self.root/"events.csv").write_bytes(b"\xff\xfe\x00")
        self.assertEqual(main(["--root",str(self.root),"--input","events.csv"]),2)

if __name__=="__main__":unittest.main()
