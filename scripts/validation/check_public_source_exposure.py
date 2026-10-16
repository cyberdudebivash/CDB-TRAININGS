#!/usr/bin/env python3
"""Fail closed when the known privacy-incident source is still in a distributable Git tree.

This checks the index and untracked, non-ignored files. It does NOT rewrite
history, inspect GitHub caches, or claim that all PDF content is privacy-safe.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROHIBITED_NAMES = frozenset({"INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK.pdf"})
# Git *blob*, not a SHA-256 checksum. Identifies the known exposed PDF even
# if the same bytes are staged under another filename.
PROHIBITED_BLOBS = frozenset({"6da92a05b08f263d6ed262139bbf195f180d9284"})


class InspectionError(RuntimeError):
    """The Git-tree inspection could not be completed; never assume PASS."""


def _run_git(root: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise InspectionError("Git tree unavailable or failed to enumerate")
    return proc.stdout


def _name(path: str) -> str:
    return unicodedata.normalize("NFKC", Path(path).name).casefold()


def check_tree(
    root: Path,
    forbidden_names: frozenset[str] = PROHIBITED_NAMES,
    forbidden_blobs: frozenset[str] = PROHIBITED_BLOBS,
) -> list[str]:
    """Return nonsensitive finding codes; never print PDF text or identities.

    The caller must separately quarantine historical objects and determine
    author permissions. A clean current tree is NOT a closed privacy incident.
    """
    root = Path(root)
    deny = {_name(x) for x in forbidden_names}
    findings: set[str] = set()

    index = _run_git(root, "ls-files", "--stage", "-z")
    for entry in index.split(b"\0"):
        if not entry:
            continue
        metadata, sep, raw_path = entry.partition(b"\t")
        if not sep or len(metadata.split()) != 3:
            raise InspectionError("unexpected staged-file record")
        parts = metadata.split()
        sha = parts[1].decode("ascii", errors="strict").lower()
        file_path = raw_path.decode("utf-8", errors="surrogateescape")
        if _name(file_path) in deny:
            findings.add("PROHIBITED_SOURCE_FILENAME_IN_GIT_INDEX")
        if sha in forbidden_blobs:
            findings.add("KNOWN_EXPOSED_PDF_BLOB_IN_GIT_INDEX")

    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw in untracked.split(b"\0"):
        if raw and _name(raw.decode("utf-8", errors="surrogateescape")) in deny:
            findings.add("PROHIBITED_SOURCE_FILENAME_IN_UNTRACKED_FILE")

    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        findings = check_tree(args.root)
    except (InspectionError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        print(f"public-source guard: ERROR ({type(exc).__name__}); not approved", file=sys.stderr)
        return 2
    if findings:
        print("public-source guard: BLOCKED; known third-party privacy source remains", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print("Current-tree cleanup cannot erase reachable Git history.", file=sys.stderr)
        return 1
    print("public-source guard: CURRENT_TREE_PASS; historical exposure NOT ASSESSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
