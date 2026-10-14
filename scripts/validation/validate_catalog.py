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

# Measurable action verbs accepted at the start of an outcome (Bloom-style, observable behaviour).
ACTION_VERBS = {
    "analyse", "apply", "assess", "audit", "automate", "build", "classify", "compare", "complete", "compose",
    "configure", "consume", "create", "cut", "deliver", "demonstrate", "deploy", "design", "detect", "diagnose",
    "document", "enforce", "execute", "explain", "exploit", "find", "geolocate", "generate", "identify",
    "implement", "improve", "ingest", "integrate", "investigate", "locate", "map", "measure", "model", "navigate",
    "open", "operate", "orchestrate", "parse", "perform", "plan", "process", "produce", "prove", "rate", "reach",
    "reconstruct", "reduce", "refactor", "run", "show", "specify", "threat-model", "trace", "train", "triage",
    "validate", "write", "add", "author", "define", "harden", "evaluate", "estimate", "extract", "preserve",
    "recommend", "remediate", "reproduce", "review", "submit", "verify",
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
        check(errors, c["lab_coverage"]["planned"] >= len(mods), f"{cid}: every module needs at least one planned lab")
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
        # Open P0/P1 findings against any of the course's sources must be listed as blocking until remediated.
        for f in findings.values():
            if f["source_id"] in c["source_ids"] and f["severity"] in ("P0", "P1") and f["remediation"]["status"] != "DONE_IN_PILOT":
                if c["release_status"] == "PRODUCTION_GO":
                    errors.append(f"{cid}: open {f['severity']} finding {f['id']} contradicts PRODUCTION_GO")

    cycle = find_cycle(graph)
    check(errors, cycle is None, f"prerequisite cycle: {' -> '.join(cycle or [])}")
    for sid in sorted(known_sources - mapped_sources):
        errors.append(f"source {sid} is not mapped to any course")
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
    print(f"catalog validation OK: {len(catalog['courses'])} courses, {n_mod} modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
