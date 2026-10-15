"""Content fingerprints that tie recorded execution evidence to the files it executed.

A fingerprint is the sha256 over (path, git blob hash) of every file under a module's execution inputs, committed or not, so it does not depend on commit ids and survives
squash merges and rebases. The lab matrix records one per module when it runs; Gate A (scripts/production/gate_a.py) recomputes it and treats a mismatch as stale evidence.
Git-ignored files are excluded, which is why the private instructor pack has its own fingerprint (`private_fingerprint`), comparable only on a machine that holds the pack.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMULA = 2           # 1: the private-pack fingerprint included tool caches (.mypy_cache, ...), which change on every run; 2: caches and build output are excluded
CACHE_PARTS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "build", "dist", ".hypothesis", ".tox"}


def execution_inputs(slug: str, module_id: str) -> list[str]:
    """Repository paths whose change after a recorded run makes that run's evidence for the module stale."""
    base = f"courses/{slug}/modules/{module_id}/"
    return [base + "lesson.md", base + "lab-guided/", base + "lab-independent/", f"courses/{slug}/labs/", "scripts/validation/lesson_blocks.py"]


def _hash_files(root: Path, files: list[str]) -> list[tuple[str, str]]:
    files = sorted({f for f in files if (root / f).is_file() and "__pycache__" not in f and not f.endswith(".pyc")})
    if not files:
        return []
    out = subprocess.run(["git", "hash-object", "--", *files], cwd=root, capture_output=True, text=True, check=False).stdout.split()
    return list(zip(files, out))


def fingerprint(inputs: list[str], root: Path = ROOT) -> str:
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *inputs], cwd=root, capture_output=True, text=True, check=False).stdout.splitlines()
    h = hashlib.sha256()
    for path, blob in _hash_files(root, listed):
        h.update(f"{path}\0{blob}\n".encode())
    return h.hexdigest()


def private_fingerprint(slug: str, module_id: str, root: Path = ROOT) -> str | None:
    """Fingerprint of the git-ignored instructor pack of a module, or None when this machine does not hold it."""
    folder = root / "courses" / slug / "instructor" / module_id
    if not folder.is_dir():
        return None
    files = sorted(str(p.relative_to(root)) for p in folder.rglob("*")
                   if p.is_file() and not CACHE_PARTS & set(p.parts) and p.suffix not in (".pyc", ".xml") and not any(part.endswith(".egg-info") for part in p.parts))
    h = hashlib.sha256()
    for path in files:
        h.update(f"{path}\0{hashlib.sha256((root / path).read_bytes()).hexdigest()}\n".encode())
    return h.hexdigest()
