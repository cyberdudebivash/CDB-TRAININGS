#!/usr/bin/env python3
"""Validate the October 2026 modernization data files against their evidence.

Checks (all deterministic, no network):
  * docs/audits/data/modernization_changes.yaml
  * docs/research/new_developments.yaml
  * docs/research/deprecation_rules.yaml (finding ids, research ids)

Every reference must resolve:
  F-*        -> docs/audits/data/findings.yaml
  R-*        -> docs/research/research_register.yaml
  probe:<id> -> docs/research/data/api_probes_<cutoff>.json
  snapshot:<id> -> docs/research/data/registry_snapshot_<cutoff>.json (tech_id)
  module ids -> catalog/courses.yaml
  source ids -> catalog/courses.yaml source_ids and the page-record INDEX

Exit code 0 when clean, 1 when any reference dangles. Imported by tests and run_qa.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2026-10-14"

ACTIONS = {"KEEP", "UPDATE", "REPLACE", "DEPRECATE", "EXPAND", "ADD", "MERGE", "REMOVE"}
VERIFICATION = {"EXECUTED", "RESEARCH_VERIFIED", "SECONDARY_ONLY", "MACHINE_ONLY", "NEEDS_VERIFICATION"}
MATURITY = {"STABLE", "EMERGING", "EXPERIMENTAL", "SPECULATIVE"}
IMPL_STATUS = {"PLANNED", "PILOT_BUILT", "BUILT"}

CHANGE_REQUIRED = ["id", "course", "source", "pages", "concept", "action", "original", "current", "reason", "ref",
                   "implemented", "learner_impact", "verification"]
DEV_REQUIRED = ["id", "title", "domain", "courses", "date", "maturity", "adoption_evidence", "relevance", "security",
                "operations", "commercial", "prerequisites", "action", "modules", "research"]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def reference_universe() -> dict:
    findings = {f["id"] for f in load("docs/audits/data/findings.yaml")["findings"]}
    register = {r["id"] for r in load("docs/research/research_register.yaml")["register"]}
    probes = {p["id"] for p in json.loads((ROOT / f"docs/research/data/api_probes_{CUTOFF}.json").read_text())["probes"]}
    snap = json.loads((ROOT / f"docs/research/data/registry_snapshot_{CUTOFF}.json").read_text())
    snapshot = {r["tech_id"] for r in snap["records"]}
    catalog = load("catalog/courses.yaml")
    modules, courses, sources = set(), set(), set()
    for c in catalog["courses"]:
        courses.add(c["id"])
        sources.update(c.get("source_ids") or [])
        for m in c["modules"]:
            modules.add(m["id"])
    inv = json.loads((ROOT / "docs/audits/data/page_records/INDEX.json").read_text())
    sources.update(p["source_id"] for p in inv["parts"])
    return {"F": findings, "R": register, "probe": probes, "snapshot": snapshot, "module": modules,
            "course": courses, "source": sources}


def check_ref(ref: str, uni: dict, where: str, errors: list) -> None:
    if ref.startswith("probe:"):
        if ref[6:] not in uni["probe"]:
            errors.append(f"{where}: unknown probe {ref}")
    elif ref.startswith("snapshot:"):
        if ref[9:] not in uni["snapshot"]:
            errors.append(f"{where}: unknown snapshot entry {ref}")
    elif ref.startswith("F-"):
        if ref not in uni["F"]:
            errors.append(f"{where}: unknown finding {ref}")
    elif ref.startswith("R-"):
        if ref not in uni["R"]:
            errors.append(f"{where}: unknown research entry {ref}")
    else:
        errors.append(f"{where}: unrecognised reference form {ref!r}")


def validate() -> list[str]:
    errors: list[str] = []
    uni = reference_universe()

    changes = load("docs/audits/data/modernization_changes.yaml")["changes"]
    seen = set()
    for ch in changes:
        cid = ch.get("id", "<no id>")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        for key in CHANGE_REQUIRED:
            if key not in ch or ch[key] in (None, "", []):
                if key == "ref" and ch.get(key) == []:
                    errors.append(f"{cid}: empty ref (every change needs evidence)")
                elif key not in ch:
                    errors.append(f"{cid}: missing {key}")
        if ch.get("action") not in ACTIONS:
            errors.append(f"{cid}: bad action {ch.get('action')!r}")
        if ch.get("course") not in uni["course"]:
            errors.append(f"{cid}: unknown course {ch.get('course')!r}")
        if ch.get("source") not in uni["source"]:
            errors.append(f"{cid}: unknown source {ch.get('source')!r}")
        v = ch.get("verification") or {}
        if v.get("status") not in VERIFICATION:
            errors.append(f"{cid}: bad verification status {v.get('status')!r}")
        if not v.get("result"):
            errors.append(f"{cid}: verification.result empty")
        if v.get("status") == "EXECUTED":
            cites_probe = any(str(r).startswith("probe:") for r in ch.get("ref", []))
            tests = re.findall(r"tests/[\w./-]+\.py", str(v.get("result", "")))
            if not cites_probe and not (tests and all((ROOT / t).exists() for t in tests)):
                errors.append(f"{cid}: EXECUTED verification must cite a probe: reference or an existing tests/ file")
        impl = ch.get("implemented") or {}
        if impl.get("status") not in IMPL_STATUS:
            errors.append(f"{cid}: bad implemented.status")
        for m in impl.get("modules", []):
            if m not in uni["module"]:
                errors.append(f"{cid}: unknown module {m}")
        if ch.get("action") not in {"REMOVE", "DEPRECATE"} and not impl.get("modules"):
            errors.append(f"{cid}: {ch.get('action')} needs at least one destination module")
        for ref in ch.get("ref", []):
            check_ref(str(ref), uni, cid, errors)
        # IDs embedded in free text must also resolve
        for key in ("original", "current", "reason", "learner_impact"):
            for fid in re.findall(r"\bF-[A-Z]+-\d{3}\b", str(ch.get(key, ""))):
                if fid not in uni["F"]:
                    errors.append(f"{cid}: {key} cites unknown finding {fid}")
        if impl.get("status") == "BUILT":
            if v.get("status") not in {"EXECUTED", "RESEARCH_VERIFIED"}:
                errors.append(f"{cid}: BUILT requires EXECUTED or RESEARCH_VERIFIED evidence")

    devs = load("docs/research/new_developments.yaml")["developments"]
    seen = set()
    for d in devs:
        did = d.get("id", "<no id>")
        if did in seen:
            errors.append(f"{did}: duplicate id")
        seen.add(did)
        for key in DEV_REQUIRED:
            if key not in d:
                errors.append(f"{did}: missing {key}")
        if d.get("maturity") not in MATURITY:
            errors.append(f"{did}: bad maturity {d.get('maturity')!r}")
        if d.get("action") not in ACTIONS:
            errors.append(f"{did}: bad action {d.get('action')!r}")
        for c in d.get("courses", []):
            if c not in uni["course"]:
                errors.append(f"{did}: unknown course {c}")
        for m in d.get("modules", []):
            if m not in uni["module"]:
                errors.append(f"{did}: unknown module {m}")
        if not d.get("research"):
            errors.append(f"{did}: no research reference (every development needs a source)")
        for r in d.get("research", []):
            check_ref(str(r), uni, did, errors)

    registry = {e["id"]: e for e in load("docs/research/technology_registry.yaml")["technologies"]}
    for tid, e in registry.items():
        for r in e.get("register", []) or []:
            if r not in uni["R"]:
                errors.append(f"registry {tid}: unknown research entry {r}")
    rules = load("docs/research/deprecation_rules.yaml")
    rule_list = rules.get("rules", rules) if isinstance(rules, dict) else rules
    for r in rule_list:
        for tid in r.get("tech", []):
            if tid not in registry:
                errors.append(f"{r.get('id')}: unknown technology id {tid}")
        for fid in re.findall(r"\bF-[A-Z]+-\d{3}\b", json.dumps(r)):
            if fid not in uni["F"]:
                errors.append(f"{r.get('id')}: cites unknown finding {fid}")
        for rid in re.findall(r"\bR-\d{3}\b", json.dumps(r)):
            if rid not in uni["R"]:
                errors.append(f"{r.get('id')}: cites unknown research entry {rid}")
    return errors


def main() -> int:
    errors = validate()
    for e in errors:
        print("ERROR", e)
    print(f"modernization data validation: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
