"""Public learner contract: deliberately fails until the starter is implemented."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from review_gate import assess_review as _student_assess


def assess_review(evidence):
    try:
        return _student_assess(evidence)
    except NotImplementedError:
        raise AssertionError(
            'FND-M04 STARTER INCOMPLETE: implement assess_review(evidence) in '
            'starter/review_gate.py, then rerun the public contracts.'
        ) from None


BASE = 'a' * 40
HEAD = 'b' * 40


def sample(**overrides):
    data = {
        'base_sha': BASE,
        'head_sha': HEAD,
        'changed_files': ['docs/runbook.md'],
        'checks_passed': True,
        'reviewed_by_other': True,
        'conflicts_remaining': False,
    }
    data.update(overrides)
    return data


class ReviewGateContract(unittest.TestCase):
    def test_ready_when_all_synthetic_checks_satisfied(self):
        self.assertEqual(assess_review(sample()), {'ready': True, 'reasons': []})

    def test_changed_sha_required(self):
        self.assertEqual(assess_review(sample(head_sha=BASE)), {'ready': False, 'reasons': ['no-diff']})

    def test_changed_files_required(self):
        self.assertEqual(assess_review(sample(changed_files=[])), {'ready': False, 'reasons': ['no-diff']})

    def test_failed_checks_block(self):
        self.assertEqual(assess_review(sample(checks_passed=False)), {'ready': False, 'reasons': ['checks-failed']})

    def test_unreviewed_branch_blocks(self):
        self.assertEqual(assess_review(sample(reviewed_by_other=False)), {'ready': False, 'reasons': ['review-missing']})

    def test_unresolved_conflicts_block(self):
        self.assertEqual(assess_review(sample(conflicts_remaining=True)), {'ready': False, 'reasons': ['conflicts-open']})

    def test_combined_reasons_use_fixed_order(self):
        actual = assess_review(sample(checks_passed=False, reviewed_by_other=False, conflicts_remaining=True))
        self.assertEqual(actual, {'ready': False, 'reasons': ['checks-failed', 'review-missing', 'conflicts-open']})

    def test_boolean_contract_must_be_exact(self):
        self.assertEqual(assess_review(sample(checks_passed=1)), {'ready': False, 'reasons': ['invalid-evidence']})

    def test_rejects_unknown_extra_key(self):
        self.assertEqual(assess_review(sample(admin=True)), {'ready': False, 'reasons': ['invalid-evidence']})

    def test_rejects_path_traversal_and_absolute_path(self):
        for changed in (['../secret.txt'], ['/etc/passwd'], ['.git/config']):
            with self.subTest(changed=changed):
                self.assertEqual(assess_review(sample(changed_files=changed)), {'ready': False, 'reasons': ['invalid-evidence']})

    def test_rejects_invalid_git_hash(self):
        self.assertEqual(assess_review(sample(head_sha='not-a-sha')), {'ready': False, 'reasons': ['invalid-evidence']})

    def test_rejects_duplicate_files(self):
        self.assertEqual(assess_review(sample(changed_files=['a.txt', 'a.txt'])), {'ready': False, 'reasons': ['invalid-evidence']})


if __name__ == '__main__':
    unittest.main()
