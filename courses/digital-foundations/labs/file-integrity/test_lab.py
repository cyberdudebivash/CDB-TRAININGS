import tempfile
import unittest
from pathlib import Path
from integrity import inventory, verify

class FileIntegrityTests(unittest.TestCase):
    def test_hashes_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'a.txt').write_bytes(b'known bytes')
            expected=inventory(p)
            self.assertEqual(len(expected),1)
            self.assertEqual(len(expected[0]['sha256']),64)
            self.assertTrue(verify(p,expected))
            (p/'a.txt').write_bytes(b'changed')
            self.assertFalse(verify(p,expected))
    def test_added_file_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); original=inventory(p)
            (p/'hidden.txt').write_text('x'); self.assertFalse(verify(p,original))
    def test_directory_rejected_if_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'actual').mkdir()
            try: (p/'alias').symlink_to(p/'actual',target_is_directory=True)
            except (OSError,NotImplementedError): self.skipTest('symlinks disabled on host')
            with self.assertRaises(ValueError): inventory(p/'alias')
    def test_symlink_entry_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'ok').write_text('ok')
            try: (p/'link').symlink_to(p/'ok')
            except (OSError,NotImplementedError): self.skipTest('symlinks disabled on host')
            with self.assertRaises(ValueError): inventory(p)
    def test_invalid_manifest_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): verify(Path(d),{'not':'list'})
if __name__=='__main__': unittest.main()
