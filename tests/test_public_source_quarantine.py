"""Narrow source-quarantine contract tests. Never include real personal data."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
from check_public_source_exposure import (  # noqa: E402
    InspectionError, PROHIBITED_NAMES, check_tree, main,
)


class SourceQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def _add(self, rel: str, payload: bytes = b"synthetic test file") -> None:
        file = self.root / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(payload)
        subprocess.run(["git", "-C", str(self.root), "add", "--", rel], check=True)

    def test_missing_prohibited_source_is_current_tree_pass(self):
        self._add("safe.txt")
        self.assertEqual(check_tree(self.root), [])

    def test_known_filename_in_index_is_blocked(self):
        self._add(next(iter(PROHIBITED_NAMES)))
        self.assertIn("PROHIBITED_SOURCE_FILENAME_IN_GIT_INDEX", check_tree(self.root))

    def test_filename_in_nested_directory_is_blocked_casefold(self):
        self._add("backup/internal frontend developer onboarding playbook.PDF")
        self.assertIn("PROHIBITED_SOURCE_FILENAME_IN_GIT_INDEX", check_tree(self.root))

    def test_untracked_exposed_filename_is_detected(self):
        (self.root / next(iter(PROHIBITED_NAMES))).write_bytes(b"synthetic")
        self.assertIn("PROHIBITED_SOURCE_FILENAME_IN_UNTRACKED_FILE", check_tree(self.root))

    def test_same_blob_under_different_filename_is_blocked(self):
        self._add("changed-name.pdf", b"synthetic content that is not private")
        raw = subprocess.run(
            ["git", "-C", str(self.root), "hash-object", "changed-name.pdf"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(check_tree(self.root, frozenset(), frozenset({raw})),
                         ["KNOWN_EXPOSED_PDF_BLOB_IN_GIT_INDEX"])

    def test_index_removal_unblocks_current_tree_only(self):
        name = next(iter(PROHIBITED_NAMES))
        self._add(name)
        subprocess.run(["git", "-C", str(self.root), "rm", "--", name],
                       check=True, capture_output=True)
        self.assertEqual(check_tree(self.root), [])

    def test_missing_git_repository_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(InspectionError):
                check_tree(Path(directory))
            self.assertEqual(main(["--root", directory]), 2)

    def test_report_does_not_emit_synthetic_file_contents(self):
        name = next(iter(PROHIBITED_NAMES))
        self._add(name, b"EXAMPLE_SENTINEL_NEVER_DISPLAY")
        self.assertEqual(main(["--root", str(self.root)]), 1)

    def test_default_production_policy_is_nonempty(self):
        self.assertEqual(len(PROHIBITED_NAMES), 1)


if __name__ == "__main__":
    unittest.main()
