#!/usr/bin/env python3
"""Validate catalog/courses.yaml (schema + cross-file rules).

Exit code 0 only when every check passes.  Output is deterministic (no timestamps).

Run:  .venv/bin/python scripts/validation/validate_catalog.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog" / "courses.yaml"
SCHEMA = ROOT / "catalog" / "schema" / "course-catalog.schema.json"
FINDINGS = ROOT / "docs" / "audits" / "data" / "findings.yaml"
INVENTORY = ROOT / "docs" / "audits" / "data" / "source_inventory.json"
PATHWAYS = ROOT / "catalog" / "learning-pathways.yaml"

# Measurable action verbs accepted at the start of an outcome (Bloom-style, observable behaviour).
ACTION_VERBS = {
    "analyse", "apply", "assess", "audit", "automate", "build", "classify", "compare", "complete", "compose",
    "configure", "consume", "create", "cut", "deliver", "demonstrate", "deploy", "design", "detect", "diagnose",
    "document", "enforce", "execute", "explain", "exploit", "find", "geolocate", "generate", "identify",
    "implement", "improve", "ingest", "integrate", "investigate", "locate", "map", "measure", "model", "navigate",
    "open", "operate", "orchestrate", "parse", "perform", "plan", "process", "produce", "prove", "rate", "reach",
    "reconstruct", "reduce", "refactor", "run", "show", "specify", "threat-model", "trace", "train", "triage",
    "validate", "write", "add", "author", "define", "harden", "evaluate", "estimate", "extract", "preserve",
    "recommend", "remediate", "reproduce", "review", "select", "submit", "verify",
}
BANNED_PHRASES = ["understand everything", "become an expert", "master ", "be able to understand", "learn about"]


class _IsoDateLoader(yaml.SafeLoader):
    """SafeLoader that keeps YAML dates as ISO strings so they validate against the JSON schema."""


_IsoDateLoader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_IsoDateLoader)  # noqa: S506 - SafeLoader subclass


def check(errors: list[str], cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        stack.append(n)
        for m in graph.get(n, []):
            if state.get(m) == 1:
                return stack[stack.index(m):] + [m]
            if state.get(m) is None:
                found = visit(m)
                if found:
                    return found
        state[n] = 2
        stack.pop()
        return None

    for node in graph:
        if state.get(node) is None:
            cyc = visit(node)
            if cyc:
                return cyc
    return None


def pathway_modules(step: dict, course: dict) -> list[dict]:
    """Modules a pathway step contributes, in catalog order (all modules when the step lists none)."""
    wanted = step.get("modules")
    mods = course["modules"]
    return [m for m in mods if wanted is None or m["id"] in wanted]


def validate_pathways(catalog: dict) -> list[str]:
    errors: list[str] = []
    data = load_yaml(PATHWAYS)
    levels = [lv["id"] for lv in data["levels"]]
    check(errors, levels == list(range(len(levels))), f"pathways: level ids must be 0..n contiguous, got {levels}")
    for lv in data["levels"]:
        for key in ("name", "descriptor", "evidence", "supervision"):
            check(errors, bool(str(lv.get(key, "")).strip()), f"pathways: level {lv['id']} missing {key}")
    by_id = {c["id"]: c for c in catalog["courses"]}
    module_course = {m["id"]: c["id"] for c in catalog["courses"] for m in c["modules"]}
    module_level = {m["id"]: m["level"] for c in catalog["courses"] for m in c["modules"]}
    module_order = {m["id"]: i for c in catalog["courses"] for i, m in enumerate(c["modules"])}
    seen: set[str] = set()
    for p in data["pathways"]:
        pid = p["id"]
        check(errors, pid not in seen, f"pathways: duplicate id {pid}")
        seen.add(pid)
        check(errors, bool(p.get("steps")), f"{pid}: no steps")
        done_courses: list[str] = []
        done_modules: set[str] = set()
        in_path: list[str] = []
        for step in p.get("steps", []):
            cid = step["course"]
            if cid not in by_id:
                errors.append(f"{pid}: unknown course {cid}")
                continue
            course = by_id[cid]
            for pre in course["prerequisites"]:
                check(errors, pre in done_courses, f"{pid}: {cid} needs prerequisite {pre} earlier in the pathway")
            listed = step.get("modules")
            if listed is not None:
                for mid in listed:
                    check(errors, module_course.get(mid) == cid, f"{pid}: module {mid} does not belong to {cid}")
                order = [module_order.get(mid, -1) for mid in listed]
                check(errors, order == sorted(order), f"{pid}: modules of {cid} are not in catalog order")
            for m in pathway_modules(step, course):
                for r in m.get("reuses", []):
                    check(errors, r in done_modules, f"{pid}: {m['id']} reuses {r}, which is not completed earlier in the pathway")
                done_modules.add(m["id"])
                in_path.append(m["id"])
            done_courses.append(cid)
        cap = p.get("capstone_module")
        check(errors, cap in in_path, f"{pid}: capstone_module {cap} is not part of the pathway")
        if cap in in_path:
            top = max(module_level[m] for m in in_path)
            check(errors, module_level[cap] == top, f"{pid}: capstone {cap} is level {module_level[cap]} but the pathway reaches level {top}")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    catalog = load_yaml(CATALOG)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for err in sorted(Draft202012Validator(schema).iter_errors(catalog), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path)
        errors.append(f"schema: {loc or '<root>'}: {err.message}")
    if errors:  # structural problems make the semantic checks unreliable
        return errors

    findings = {f["id"]: f for f in load_yaml(FINDINGS)["findings"]}
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    known_sources = {d["source_id"] for d in inventory["documents"]}

    import datetime as _dt

    for label, value in [("catalog", catalog.get("last_verified"))] + [(c["id"], c["last_verified"]) for c in catalog["courses"]]:
        try:
            _dt.date.fromisoformat(value)
        except (TypeError, ValueError):
            errors.append(f"{label}: last_verified '{value}' is not an ISO date")
    courses = catalog["courses"]
    ids = [c["id"] for c in courses]
    slugs = [c["slug"] for c in courses]
    check(errors, len(ids) == len(set(ids)), "duplicate course ids")
    check(errors, len(slugs) == len(set(slugs)), "duplicate course slugs")

    all_modules: dict[str, str] = {}
    graph: dict[str, list[str]] = {}
    mapped_sources: set[str] = set()
    for c in courses:
        cid = c["id"]
        graph[cid] = c["prerequisites"]
        for pre in c["prerequisites"]:
            check(errors, pre in ids, f"{cid}: unknown prerequisite {pre}")
        for sid in c["source_ids"]:
            check(errors, sid in known_sources, f"{cid}: unknown source id {sid}")
            mapped_sources.add(sid)
        mods = c["modules"]
        for m in mods:
            mid = m["id"]
            check(errors, mid not in all_modules, f"duplicate module id {mid}")
            all_modules[mid] = cid
            first = re.split(r"[\s,]+", m["primary_outcome"].strip().lower(), maxsplit=1)[0]
            check(errors, first in ACTION_VERBS, f"{mid}: outcome must start with a measurable action verb (got '{first}')")
            low = m["primary_outcome"].lower()
            for bad in BANNED_PHRASES:
                check(errors, bad not in low, f"{mid}: vague outcome phrase '{bad.strip()}'")
        total = sum(m["estimated_hours"] for m in mods)
        check(errors, abs(total - c["estimated_duration_hours"]) < 1e-6,
              f"{cid}: module hours sum {total} != estimated_duration_hours {c['estimated_duration_hours']}")
        capstones = sum(1 for m in mods if m["title"].lower().startswith("capstone"))
        expected_labs = 2 * (len(mods) - capstones) + capstones
        check(errors, c["lab_coverage"]["planned"] == expected_labs,
              f"{cid}: planned labs {c['lab_coverage']['planned']} != unit contract {expected_labs} (guided + independent per module, one per capstone)")
        check(errors, c["lab_coverage"]["built"] <= c["lab_coverage"]["planned"], f"{cid}: built labs exceed planned")
        check(errors, c["lab_coverage"]["verified_executable"] <= c["lab_coverage"]["built"], f"{cid}: verified labs exceed built")
        ac = c["assessment_coverage"]
        check(errors, ac["outcomes_assessed"] <= ac["outcomes_total"], f"{cid}: assessed outcomes exceed total")
        levels = {m["level"] for m in mods}
        check(errors, levels <= set(c["competency_levels"]), f"{cid}: module levels {sorted(levels)} outside competency_levels")
        for fid in c.get("blocking_findings", []):
            check(errors, fid in findings, f"{cid}: unknown finding {fid}")
            if fid in findings:
                check(errors, findings[fid]["severity"] in ("P0", "P1"), f"{cid}: {fid} is not P0/P1")
        for m in mods:
            for r in m.get("reuses", []):
                check(errors, any(r == mm["id"] for cc in courses for mm in cc["modules"]), f"{m['id']}: reuses unknown module {r}")
        # Hard gate: PRODUCTION_GO cannot be asserted by editing one field.
        if c["release_status"] == "PRODUCTION_GO":
            check(errors, c["review_status"] == "SME_REVIEWED", f"{cid}: PRODUCTION_GO requires SME_REVIEWED")
            check(errors, c["qa_status"] == "PASSING", f"{cid}: PRODUCTION_GO requires qa_status PASSING")
            check(errors, c["lab_coverage"]["verified_executable"] == c["lab_coverage"]["planned"], f"{cid}: PRODUCTION_GO requires all labs verified")
            check(errors, ac["outcomes_assessed"] == ac["outcomes_total"], f"{cid}: PRODUCTION_GO requires every outcome assessed")
            check(errors, not c.get("blocking_findings"), f"{cid}: PRODUCTION_GO requires no blocking findings")
            check(errors, c["owner"] != "UNASSIGNED" and c["reviewers"], f"{cid}: PRODUCTION_GO requires a named owner and reviewers")
        # Every P0/P1 finding against the course's sources blocks the course until the course is fully rebuilt:
        # a fix inside one pilot module does not clear a finding for the whole course.
        if c["lifecycle"] != "VALIDATED":
            required = sorted(f["id"] for f in findings.values() if f["source_id"] in c["source_ids"] and f["severity"] in ("P0", "P1"))
            missing = [fid for fid in required if fid not in c.get("blocking_findings", [])]
            check(errors, not missing, f"{cid}: P0/P1 findings missing from blocking_findings: {', '.join(missing)}")

    cycle = find_cycle(graph)
    check(errors, cycle is None, f"prerequisite cycle: {' -> '.join(cycle or [])}")
    for sid in sorted(known_sources - mapped_sources):
        errors.append(f"source {sid} is not mapped to any course")
    errors += validate_pathways(catalog)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"catalog validation FAILED ({len(errors)} problem(s))")
        for e in errors:
            print(f"  - {e}")
        return 1
    catalog = load_yaml(CATALOG)
    n_mod = sum(len(c["modules"]) for c in catalog["courses"])
    n_path = len(load_yaml(PATHWAYS)["pathways"])
    print(f"catalog validation OK: {len(catalog['courses'])} courses, {n_mod} modules, {n_path} pathways")
    return 0


if __name__ == "__main__":
    sys.exit(main())
