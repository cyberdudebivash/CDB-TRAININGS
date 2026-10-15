#!/usr/bin/env python3
"""Build every module student edition and record the result in docs/production/data/pdf_manifest.json (the evidence for Gate A criteria A12, A14 and A15).

For each module that has a student-edition config the script runs the strict edition build (HTML + tagged PDF + all gates: forbidden markers, personal-data scan,
360 px overflow, bookmark outline) into dist/ (git-ignored) and records, per edition: the sha256 of every source file it was built from, the sha256 of the HTML (deterministic),
page and word counts, tagged and outline status, and whether every gate passed. PDF hashes are not recorded because a PDF embeds its creation time.

Gate A treats a recorded edition as evidence only while every source file still has the recorded hash (scripts/production/gate_a.py: edition_is_fresh).
Complete course editions (the whole approved curriculum of a course in one PDF) are not built here: a course edition may only be built when every required module of the course
is implemented, so for every course that is incomplete the right result is "no course edition", and `course_editions` stays empty.

Run: .venv/bin/python scripts/production/build_pdf_manifest.py [--reuse] [--only PY-M05]
  --reuse   do not rebuild; read the manifests already present in dist/ (fails if one is missing)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "production"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import build_student_edition as BSE  # noqa: E402
import gate_a as G  # noqa: E402
import yaml  # noqa: E402

OUT = ROOT / "dist"
MANIFEST = ROOT / "docs" / "production" / "data" / "pdf_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_from(manifest: dict, module_id: str, config: Path) -> dict:
    sources = {rel: sha256(ROOT / rel) for rel in manifest["sources"]}
    sources[config.relative_to(ROOT).as_posix()] = sha256(config)
    pdf = manifest["pdf"]
    return {
        "module": module_id, "edition": manifest["edition"], "sources": dict(sorted(sources.items())), "html_sha256": manifest["html"]["sha256"],
        "pdf_pages": pdf["pages"], "pdf_words": pdf["words"], "tagged": pdf["tagged"], "outline_entries": pdf["outline_entries"], "mobile_360px": manifest["mobile_360px"],
        "problems": {k: v for k, v in manifest["problems"].items() if v}, "passed": bool(manifest["passed"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--only", action="append", default=[], help="module id to (re)build; others keep their recorded entry")
    a = ap.parse_args(argv)
    catalog = G.load_yaml("catalog/courses.yaml")
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"editions": [], "course_editions": []}
    kept = {e["module"]: e for e in previous["editions"]}
    editions: dict[str, dict] = {}
    failed = False
    for course in catalog["courses"]:
        for module in course["modules"]:
            _, config, _ = G.module_files(course, module["id"], [])
            if config is None or not config.exists():
                continue
            if a.only and module["id"] not in a.only:
                if module["id"] in kept:
                    editions[module["id"]] = kept[module["id"]]
                continue
            cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
            stem = f"{cfg['module']}-{cfg['edition']}-{cfg['version']}"
            if a.reuse:
                manifest = json.loads((OUT / f"{stem}.manifest.json").read_text(encoding="utf-8"))
            else:
                try:
                    manifest = BSE.build(config, OUT, strict=True)
                except BSE.BuildError as exc:
                    print(f"{module['id']}: BUILD ERROR {exc}", file=sys.stderr)
                    failed = True
                    continue
            entry = entry_from(manifest, cfg["module"], config)
            editions[module["id"]] = entry
            print(f"{module['id']}: {entry['pdf_pages']} pages, {entry['pdf_words']} words, tagged={entry['tagged']}, outline={entry['outline_entries']}, passed={entry['passed']}")
            failed = failed or not entry["passed"]
    out = {"schema_version": 1, "editions": [editions[k] for k in sorted(editions)], "course_editions": previous.get("course_editions", [])}
    MANIFEST.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(ROOT)} ({len(editions)} module editions; {len(out['course_editions'])} course editions)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
