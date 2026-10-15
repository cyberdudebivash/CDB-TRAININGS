#!/usr/bin/env python3
"""Structural personal-data guard for everything this repository authors or generates.

It looks for e-mail addresses and telephone numbers in text. It does not know whose they are, so it cannot decide that a string is a person's data; it decides that
a string has the *shape* of one and is not on the reviewed allow-list (docs/production/data/privacy_allowlist.yaml: placeholder domains, the owner's own domain).
Findings are printed masked (first character, then asterisks) so that a failing run never copies personal data into logs.

What is scanned:
  * every tracked or untracked-but-not-ignored text file of the repository, EXCEPT the ten source PDFs (binary; they are the owner's originals, see
    docs/production/data/incidents.yaml for the one known exposure in them);
  * with --text FILE: any extra text, for example the text of a built student edition (the edition builder calls scan_text directly).

Exit code 0 = no finding, 1 = at least one finding.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "docs" / "production" / "data" / "privacy_allowlist.yaml"

EMAIL = re.compile(r"(?<![\w.+-])([A-Za-z0-9][A-Za-z0-9._%+-]*)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
# A telephone number: an international prefix (+CC ...) with at least 9 digits in total, or a label (phone, mobile, tel, whatsapp) followed by a number with 9+ digits.
PHONE_PLUS = re.compile(r"(?<![\w.])\+\d{1,3}[\s().-]?(?:\d[\s().-]?){8,13}\d(?![\w])")
PHONE_LABEL = re.compile(r"(?i)\b(?:phone|mobile|mob|tel|telephone|whatsapp|contact no\.?)\b[^\w\n]{0,6}(\+?\d(?:[\s().-]?\d){8,13})")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".jsonl", ".py", ".txt", ".toml", ".ini", ".cfg", ".html", ".css", ".js", ".csv", ".log", ".sh"}


@dataclass(frozen=True)
class Finding:
    where: str
    line: int
    kind: str
    masked: str

    def __str__(self) -> str:
        return f"{self.where}:{self.line}: {self.kind} {self.masked}"


def load_allowlist() -> dict:
    data = yaml.safe_load(ALLOWLIST.read_text(encoding="utf-8")) or {}
    return {"domains": [d.lower() for d in data.get("email_domains", [])], "paths": data.get("path_globs", []), "phones": [re.sub(r"\D", "", p) for p in data.get("phone_digits", [])]}


def domain_allowed(domain: str, allowed: list[str]) -> bool:
    domain = domain.lower()
    return any(domain == a or domain.endswith("." + a) or (a.startswith("*.") and domain.endswith(a[1:])) for a in allowed)


def mask_email(local: str, domain: str) -> str:
    return f"{local[0]}{'*' * min(len(local) - 1, 6)}@{domain}"


def scan_text(text: str, where: str, allow: dict | None = None) -> list[Finding]:
    allow = allow or load_allowlist()
    found: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            local, domain = m.group(1), m.group(2)
            if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", local) or domain.lower().endswith((".png", ".jpg", ".svg", ".js", ".py", ".md")) or not re.search(r"\.[A-Za-z]{2,}$", domain):
                continue                                                # a hash, an image file name with a density suffix, or a package pin with a version number: not an address
            if not domain_allowed(domain, allow["domains"]):
                found.append(Finding(where, number, "e-mail", mask_email(local, domain)))
        for pattern in (PHONE_PLUS, PHONE_LABEL):
            for m in pattern.finditer(line):
                digits = re.sub(r"\D", "", m.group(m.lastindex or 0))
                if len(digits) < 9 or digits in allow["phones"] or len(set(digits)) <= 2:
                    continue
                found.append(Finding(where, number, "phone", f"{'*' * (len(digits) - 3)}{digits[-3:]}"))
    return found


def repo_text_files() -> list[Path]:
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    return [ROOT / rel for rel in listed if (ROOT / rel).is_file() and (ROOT / rel).suffix.lower() in TEXT_SUFFIXES]


def scan_repo() -> list[Finding]:
    allow = load_allowlist()
    findings: list[Finding] = []
    for path in repo_text_files():
        rel = path.relative_to(ROOT).as_posix()
        if any(fnmatch(rel, g) for g in allow["paths"]):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings += scan_text(text, rel, allow)
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--text", action="append", default=[], help="extra text file to scan (for example the text of a built edition)")
    a = ap.parse_args(argv)
    findings = scan_repo()
    allow = load_allowlist()
    for extra in a.text:
        findings += scan_text(Path(extra).read_text(encoding="utf-8", errors="replace"), extra, allow)
    for f in findings:
        print(f)
    print(f"privacy guard: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
