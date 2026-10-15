"""Offline foundations exercise: trustworthy inventory of a directory of regular files."""
from __future__ import annotations
import hashlib
from pathlib import Path

def inventory(directory: Path) -> list[dict[str, str | int]]:
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("source must be a real directory")
    results = []
    for item in sorted(directory.iterdir(), key=lambda x: x.name):
        if item.is_symlink():
            raise ValueError(f"symbolic link not permitted: {item.name}")
        if item.is_dir():
            continue
        if not item.is_file():
            raise ValueError(f"unsupported path: {item.name}")
        digest = hashlib.sha256()
        with item.open('rb') as file:
            for chunk in iter(lambda: file.read(65536), b''):
                digest.update(chunk)
        results.append({'name': item.name, 'bytes': item.stat().st_size, 'sha256': digest.hexdigest()})
    return results

def verify(directory: Path, expected: list[dict[str, str | int]]) -> bool:
    if not isinstance(expected, list) or any(not isinstance(row,dict) for row in expected):
        raise ValueError('manifest must be a list of records')
    return inventory(directory) == expected
