"""FND-M04 local Git lab. Tests require Git installed and never use remotes."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'solution'))
from git_workflow import PracticeRepo, reviewable_feature, conflict_and_recovery


class GitWorkflowContracts(unittest.TestCase):
    def test_feature_branch_is_reviewable(self):
        result = reviewable_feature()
        self.assertEqual(result['feature_branch'], 'feature/runbook')
        self.assertEqual(result['changed_files'], ['runbook.md'])
        self.assertIn('+1. Inspect error.', result['reviewable_diff'])
        self.assertFalse(result['remote_review_observed'])

    def test_history_uses_real_shas_and_two_parent_merge(self):
        result = reviewable_feature()
        self.assertRegex(result['baseline_sha'], r'^[0-9a-f]{40}$')
        self.assertRegex(result['feature_sha'], r'^[0-9a-f]{40}$')
        self.assertRegex(result['merge_sha'], r'^[0-9a-f]{40}$')
        self.assertEqual(result['merge_parent_count'], 2)
        self.assertNotEqual(result['baseline_sha'], result['feature_sha'])

    def test_merge_leaves_clean_working_tree(self):
        self.assertTrue(reviewable_feature()['clean_after_merge'])

    def test_real_merge_conflict_detected(self):
        result = conflict_and_recovery()
        self.assertTrue(result['conflict_exit_nonzero'])
        self.assertTrue(result['unmerged_entries_observed'])
        self.assertTrue(result['conflict_markers_observed'])

    def test_conflict_recovery_is_explicit_and_clean(self):
        result = conflict_and_recovery()
        self.assertEqual(result['resolved_bytes'], 'MODE=reviewed\n')
        self.assertEqual(result['remaining_unmerged_entries'], '')
        self.assertTrue(result['clean_after_resolution'])

    def test_practice_directory_is_deleted(self):
        with PracticeRepo() as repo:
            path = repo.path
            self.assertTrue((path / 'README.md').is_file())
        self.assertFalse(path.exists())

    def test_no_global_config_writes(self):
        with PracticeRepo() as repo:
            self.assertEqual(repo.git('config', '--local', 'user.email').stdout.strip(), 'learner@example.invalid')
            self.assertIn('Training Learner', repo.git('log', '-1', '--format=%an').stdout)

    def test_rejects_traversal(self):
        with PracticeRepo() as repo:
            for filename in ('../outside.txt', 'nested/path.md', '.gitconfig', 'config.yaml'):
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    repo.write(filename, 'safe')

    def test_rejects_oversized_content(self):
        with PracticeRepo() as repo:
            with self.assertRaises(ValueError):
                repo.write('large.txt', 'x' * 17000)

    def test_session_not_reusable_after_cleanup(self):
        sandbox = PracticeRepo()
        with sandbox:
            self.assertTrue(sandbox.git('status', '--porcelain').returncode == 0)
        with self.assertRaises(RuntimeError):
            sandbox.git('status')

    def test_training_repos_have_no_remotes(self):
        with PracticeRepo() as repo:
            self.assertEqual(repo.git('remote', '-v').stdout.strip(), '')

    def test_unapproved_git_operations_fail_closed(self):
        with PracticeRepo() as repo:
            for args in (('push', 'origin', 'main'), ('-C', '/', 'status'),
                         ('config', '--global', 'user.email', 'unsafe@example.invalid'),
                         ('clean', '-fdx'), ('remote', 'add', 'origin', 'https://example.invalid')):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    repo.git(*args)

    def test_no_shell_expansion_or_network_needed(self):
        with PracticeRepo() as repo:
            result = repo.git('status', '--short', '--', '*.md')
            self.assertEqual(result.returncode, 0)

if __name__ == '__main__':
    unittest.main()
