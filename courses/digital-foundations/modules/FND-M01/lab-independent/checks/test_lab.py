"""Published student contracts; intentional starter failures are expected."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from access_check import check_access

class AccessCheckContract(unittest.TestCase):
    def test_allows_exact_match(self):
        self.assertTrue(check_access({"role":"analyst"},{"permissions":{"analyst":["read"]}},"read"))
    def test_denies_other_role(self):
        self.assertFalse(check_access({"role":"guest"},{"permissions":{"analyst":["read"]}},"read"))
    def test_denies_implicit_wildcard(self):
        self.assertFalse(check_access({"role":"analyst"},{"permissions":{"analyst":["read-all"]}},"read"))
    def test_denies_no_matching_grant(self):
        self.assertFalse(check_access({"role":"analyst"},{"permissions":{}},"read"))
    def test_rejects_unknown_operation(self):
        with self.assertRaises(ValueError):check_access({"role":"analyst"},{"permissions":{}},"delete")
    def test_rejects_missing_role(self):
        with self.assertRaises(ValueError):check_access({},{"permissions":{}},"read")
    def test_rejects_malformed_permissions(self):
        with self.assertRaises(ValueError):check_access({"role":"analyst"},{"permissions":{"analyst":"read"}},"read")

if __name__=="__main__":unittest.main()
