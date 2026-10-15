"""FND-M04: isolated Git workflow over synthetic files.

Never clones, fetches, pushes or accesses remote repositories. All Git calls
execute in a disposable temp directory with arguments rather than shell syntax.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


class PracticeRepo:
    """Owned disposable sandbox with narrowly scoped Git operations."""

    def __init__(self) -> None:
        self._temp = None
        self.path: Path | None = None

    def __enter__(self) -> 'PracticeRepo':
        if not shutil.which('git'):
            raise RuntimeError('Git executable required for this lab')
        self._temp = tempfile.TemporaryDirectory(prefix='cdb-fnd-m04-')
        self.path = Path(self._temp.name)
        try:
            self.git('init', '-q', '--initial-branch=main')
            self.git('config', '--local', 'user.name', 'Training Learner')
            self.git('config', '--local', 'user.email', 'learner@example.invalid')
            self.git('config', '--local', 'commit.gpgsign', 'false')
            self.write('README.md', '# Synthetic service\n')
            self.git('add', '--', 'README.md')
            self.git('commit', '-q', '-m', 'docs: initialize synthetic practice repo')
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._temp is not None:
            self._temp.cleanup()
        self.path = None
        self._temp = None

    def git(self, *args: str, check: bool = True) -> GitResult:
        if self.path is None or not self.path.is_dir():
            raise RuntimeError('practice sandbox is not active')
        if not args or not all(isinstance(arg, str) for arg in args):
            raise ValueError('Git arguments must be nonempty strings')
        # Permit only this lesson's exact synthetic commands. Without an allowlist,
        # extra -C/--git-dir flags or unrelated Git subcommands could escape scope.
        allowed = {
            ('init', '-q', '--initial-branch=main'),
            ('config', '--local', 'user.name', 'Training Learner'),
            ('config', '--local', 'user.email', 'learner@example.invalid'),
            ('config', '--local', 'commit.gpgsign', 'false'),
            ('config', '--local', 'user.email'),
            ('add', '--', 'README.md'), ('add', '--', 'runbook.md'),
            ('add', '--', 'settings.txt'),
            ('commit', '-q', '-m', 'docs: initialize synthetic practice repo'),
            ('commit', '-q', '-m', 'docs: add support runbook'),
            ('commit', '-q', '-m', 'test: add synthetic configuration'),
            ('commit', '-q', '-m', 'test: feature setting'),
            ('commit', '-q', '-m', 'test: main setting'),
            ('commit', '-q', '-m', 'docs: resolve synthetic settings conflict'),
            ('switch', '-q', '-c', 'feature/runbook'),
            ('switch', '-q', '-c', 'feature/change'),
            ('switch', '-q', 'main'),
            ('rev-parse', 'HEAD'),
            ('diff', 'main...HEAD', '--', 'runbook.md'),
            ('diff', '--name-only', 'main...HEAD'),
            ('branch', '--show-current'),
            ('merge', '--no-ff', '--no-edit', 'feature/runbook'),
            ('merge', '--no-ff', '--no-edit', 'feature/change'),
            ('rev-list', '--parents', '-n', '1', 'HEAD'),
            ('status', '--porcelain'),
            ('status', '--short', '--', '*.md'),
            ('ls-files', '-u', '--', 'settings.txt'),
            ('ls-files', '-u'),
            ('remote', '-v'),
            ('log', '-1', '--format=%an'),
        }
        if tuple(args) not in allowed:
            raise ValueError('Git action outside the approved synthetic lab allowlist')
        # Every command below uses a direct argv list; no shell expansion.
        proc = subprocess.run(
            ['git', '-C', str(self.path), *args], capture_output=True,
            text=True, encoding='utf-8', errors='replace', timeout=20,
            env=self._safe_env(),
        )
        if check and proc.returncode:
            raise RuntimeError(f'Git action {args[0]} failed with exit {proc.returncode}: {proc.stderr[-400:]}')
        return GitResult(proc.returncode, proc.stdout, proc.stderr)

    @staticmethod
    def _safe_env() -> dict[str, str]:
        # Avoid Git's global credential and signature helpers. No remote commands used.
        import os
        env = dict(os.environ)
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        env['GIT_CONFIG_GLOBAL'] = os.devnull
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_NO_REPLACE_OBJECTS'] = '1'
        env['GIT_AUTHOR_NAME'] = 'Training Learner'
        env['GIT_AUTHOR_EMAIL'] = 'learner@example.invalid'
        env['GIT_COMMITTER_NAME'] = 'Training Learner'
        env['GIT_COMMITTER_EMAIL'] = 'learner@example.invalid'
        return env

    def write(self, filename: str, content: str) -> None:
        if self.path is None:
            raise RuntimeError('no active sandbox')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(md|txt)', filename):
            raise ValueError('only top-level synthetic .md or .txt files permitted')
        if not isinstance(content, str) or len(content.encode('utf-8')) > 16384:
            raise ValueError('practice content exceeds 16 KiB')
        (self.path / filename).write_text(content, encoding='utf-8')


def reviewable_feature() -> dict:
    """Create local feature, inspect changes, merge and return factual evidence."""
    with PracticeRepo() as sandbox:
        baseline = sandbox.git('rev-parse', 'HEAD').stdout.strip()
        sandbox.git('switch', '-q', '-c', 'feature/runbook')
        sandbox.write('runbook.md', '# Synthetic troubleshooting steps\n1. Inspect error.\n')
        sandbox.git('add', '--', 'runbook.md')
        sandbox.git('commit', '-q', '-m', 'docs: add support runbook')
        head = sandbox.git('rev-parse', 'HEAD').stdout.strip()
        diff = sandbox.git('diff', 'main...HEAD', '--', 'runbook.md').stdout
        changed_files = sandbox.git('diff', '--name-only', 'main...HEAD').stdout.splitlines()
        branch_before_merge = sandbox.git('branch', '--show-current').stdout.strip()
        sandbox.git('switch', '-q', 'main')
        sandbox.git('merge', '--no-ff', '--no-edit', 'feature/runbook')
        merge_sha = sandbox.git('rev-parse', 'HEAD').stdout.strip()
        parents = sandbox.git('rev-list', '--parents', '-n', '1', 'HEAD').stdout.strip().split()
        clean = sandbox.git('status', '--porcelain').stdout == ''
        return {
            'baseline_sha': baseline, 'feature_sha': head,
            'reviewable_diff': diff, 'changed_files': changed_files,
            'feature_branch': branch_before_merge, 'merge_sha': merge_sha,
            'merge_parent_count': len(parents) - 1, 'clean_after_merge': clean,
            'remote_review_observed': False,
        }


def conflict_and_recovery() -> dict:
    """Demonstrate a genuine content conflict and intentional local resolution."""
    with PracticeRepo() as sandbox:
        sandbox.write('settings.txt', 'MODE=default\n')
        sandbox.git('add', '--', 'settings.txt')
        sandbox.git('commit', '-q', '-m', 'test: add synthetic configuration')
        sandbox.git('switch', '-q', '-c', 'feature/change')
        sandbox.write('settings.txt', 'MODE=training\n')
        sandbox.git('add', '--', 'settings.txt')
        sandbox.git('commit', '-q', '-m', 'test: feature setting')
        sandbox.git('switch', '-q', 'main')
        sandbox.write('settings.txt', 'MODE=production-example\n')
        sandbox.git('add', '--', 'settings.txt')
        sandbox.git('commit', '-q', '-m', 'test: main setting')
        conflict = sandbox.git('merge', '--no-ff', '--no-edit', 'feature/change', check=False)
        unmerged = sandbox.git('ls-files', '-u', '--', 'settings.txt').stdout
        text_with_markers = (sandbox.path / 'settings.txt').read_text(encoding='utf-8')
        if conflict.returncode == 0 or not unmerged or '<<<<<<<' not in text_with_markers:
            raise AssertionError('the intended teaching conflict was not observed')
        sandbox.write('settings.txt', 'MODE=reviewed\n')
        sandbox.git('add', '--', 'settings.txt')
        sandbox.git('commit', '-q', '-m', 'docs: resolve synthetic settings conflict')
        return {
            'conflict_exit_nonzero': conflict.returncode != 0,
            'unmerged_entries_observed': bool(unmerged),
            'conflict_markers_observed': '<<<<<<<' in text_with_markers,
            'resolved_bytes': (sandbox.path / 'settings.txt').read_text(encoding='utf-8'),
            'clean_after_resolution': sandbox.git('status', '--porcelain').stdout == '',
            'remaining_unmerged_entries': sandbox.git('ls-files', '-u').stdout,
        }
