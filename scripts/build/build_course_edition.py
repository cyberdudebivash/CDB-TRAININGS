#!/usr/bin/env python3
"""Build the complete-course PREVIEW edition of a course: every module's lesson, lab READMEs and quiz in one validated, tagged PDF (the "PDF factory", one edition per course).

The edition is assembled from the module student-edition configurations (courses/<slug>/student/<MODULE>-student-edition.yaml), in catalog order, so the course PDF can never
contain more than the module previews contain, and never less. It is a PREVIEW: nothing in it has been reviewed by a subject-matter expert, piloted with learners or accepted by
the owner, and the title says so. A course edition is built only when every module of the course is BUILT in the catalog and has an edition configuration; otherwise the build refuses.
The result is recorded in docs/production/data/pdf_manifest.json under `course_editions` with kind PREVIEW; Gate A criterion A14 (a final edition built from the whole approved
curriculum) is not satisfied by a preview (scripts/production/gate_a.py).

Run:  .venv/bin/python scripts/build/build_course_edition.py [--course COURSE-PY-ENG] [--out dist] [--no-record]
Requires pandoc, poppler-utils and a Chromium binary, like scripts/build/build_student_edition.py (which does the building and all the checks).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import build_student_edition as BSE  # noqa: E402

MANIFEST = ROOT / "docs" / "production" / "data" / "pdf_manifest.json"
KIND = "PREVIEW"


class CourseEditionError(Exception):
    pass


def course_config(course: dict, slug_dir: Path) -> tuple[dict, list[Path]]:
    """The edition configuration of the whole course, built from its module configurations. Raises CourseEditionError when a module cannot be included."""
    module_configs: list[Path] = []
    cfgs: list[dict] = []
    for module in course["modules"]:
        path = slug_dir / "student" / f"{module['id']}-student-edition.yaml"
        if module["status"] != "BUILT":
            raise CourseEditionError(f"{module['id']} is {module['status']}: a course edition needs every module BUILT")
        if not path.is_file():
            raise CourseEditionError(f"{module['id']} has no student edition configuration ({path.relative_to(ROOT)})")
        module_configs.append(path)
        cfgs.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    include: list[str] = []
    for cfg in cfgs:
        for rel in cfg["include"]:
            if rel not in include:
                include.append(rel)
    forbidden_paths = sorted({f for cfg in cfgs for f in cfg["forbidden_path_fragments"]})
    forbidden_markers = sorted({m for cfg in cfgs for m in cfg["forbidden_markers"]})
    ids = [m["id"] for m in course["modules"]]
    title = f"{course['title']} - Complete Course Preview Edition (unreviewed)"
    config = {
        "edition": "course-preview", "course": course["id"], "module": course["id"], "modules": ids, "scope_label": f"Complete course ({len(ids)} modules)", "title": title,
        "version": "0.1.0-preview", "language": "en", "attribution": False, "notice_title": "Preview status.",
        "notice_text": ("This edition contains every module of the course and has not been reviewed by a qualified subject-matter expert, has not been piloted with learners, has not been accepted by the owner "
                        "and is not a certified or production-ready course. Completion is awarded only for demonstrated competence on the rubrics, never for reading this document."),
        "edition_metadata": "auto", "expected_strings": [course["id"], "Preview status", "Complete Course Preview Edition", "PY-M01", ids[-1]],
        "include": include, "forbidden_path_fragments": forbidden_paths, "forbidden_markers": forbidden_markers,
    }
    return config, module_configs


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(entry: dict) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"schema_version": 1, "editions": [], "course_editions": []}
    data["course_editions"] = [e for e in data.get("course_editions", []) if e.get("course") != entry["course"]] + [entry]
    MANIFEST.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", default="COURSE-PY-ENG")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--no-record", action="store_true", help="build and check, but do not write the result into docs/production/data/pdf_manifest.json")
    a = ap.parse_args(argv)
    catalog = yaml.safe_load((ROOT / "catalog" / "courses.yaml").read_text(encoding="utf-8"))
    course = next((c for c in catalog["courses"] if c["id"] == a.course), None)
    if course is None:
        print(f"unknown course {a.course}", file=sys.stderr)
        return 2
    try:
        config, module_configs = course_config(course, ROOT / "courses" / course["slug"])
    except CourseEditionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / f"{course['id']}-course-preview.config.yaml"
    config_path.write_text("# generated by scripts/build/build_course_edition.py from the module student-edition configurations; do not edit\n" + yaml.safe_dump(config, sort_keys=False, width=200), encoding="utf-8")
    try:
        manifest = BSE.build(config_path, out, strict=True)
    except BSE.BuildError as exc:
        print(f"BUILD ERROR: {exc}", file=sys.stderr)
        return 2
    pdf = manifest["pdf"]
    print(f"built {manifest['edition']}: pdf {pdf['pages']} pages, {pdf['words']} words, tagged={pdf['tagged']}, outline={pdf['outline_entries']}; mobile {manifest['mobile_360px']}")
    for area, probs in manifest["problems"].items():
        for p in probs:
            print(f"  PROBLEM [{area}] {p}")
    sources = {rel: sha256(ROOT / rel) for rel in manifest["sources"]}
    sources.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in module_configs})
    entry = {"course": course["id"], "edition": manifest["edition"], "kind": KIND, "modules": config["modules"], "sources": dict(sorted(sources.items())), "html_sha256": manifest["html"]["sha256"],
             "pdf_pages": pdf["pages"], "pdf_words": pdf["words"], "tagged": pdf["tagged"], "outline_entries": pdf["outline_entries"], "mobile_360px": manifest["mobile_360px"],
             "problems": {k: v for k, v in manifest["problems"].items() if v}, "passed": bool(manifest["passed"])}
    if not a.no_record:
        record(entry)
        print(f"recorded in {MANIFEST.relative_to(ROOT)}")
    print("RESULT:", "PASS" if manifest["passed"] else "FAIL")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
