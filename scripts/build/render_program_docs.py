#!/usr/bin/env python3
"""Render the generated blocks inside the program-level documents from the catalog (single source of truth).

Narrative text in these documents is hand-written; only the regions between

    <!-- BEGIN GENERATED: name -->  ...  <!-- END GENERATED: name -->

are owned by this script.  `--check` exits 1 when any region on disk differs from what would be generated,
which is how CI/QA detects drift between the catalog and the documents.

Run:  .venv/bin/python scripts/build/render_program_docs.py [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
from validate_catalog import CATALOG, PATHWAYS, load_yaml, pathway_modules  # noqa: E402

DOCS = {
    "blueprint": ROOT / "docs" / "curriculum" / "MASTER_CURRICULUM_BLUEPRINT.md",
    "pathways": ROOT / "docs" / "curriculum" / "COMPETENCY_PATHWAYS.md",
    "products": ROOT / "docs" / "commercial" / "COURSE_PRODUCT_CATALOG.md",
    "readiness": ROOT / "docs" / "commercial" / "COMMERCIAL_READINESS.md",
}


def esc(text: str) -> str:
    return str(text).replace("|", "\\|")


def fmt_h(h: float) -> str:
    return str(int(h)) if float(h).is_integer() else f"{h:g}"


# ------------------------------------------------------------------------------------------------ blocks
def block_portfolio(catalog: dict, **_) -> str:
    rows = ["| Course | ID | Level span | Modules | Planned hours | Labs planned / built / verified | Outcomes assessed | Lifecycle | Release status |",
            "|---|---|---|---:|---:|---|---:|---|---|"]
    tot_m = tot_h = tot_l = 0
    for c in catalog["courses"]:
        lv = sorted(c["competency_levels"])
        lab = c["lab_coverage"]
        rows.append(f"| {esc(c['title'])} | `{c['id']}` | L{lv[0]}-L{lv[-1]} | {len(c['modules'])} | {fmt_h(c['estimated_duration_hours'])} | "
                    f"{lab['planned']} / {lab['built']} / {lab['verified_executable']} | {c['assessment_coverage']['outcomes_assessed']}/{c['assessment_coverage']['outcomes_total']} | "
                    f"{c['lifecycle']} | `{c['release_status']}` |")
        tot_m += len(c["modules"]); tot_h += c["estimated_duration_hours"]; tot_l += lab["planned"]
    rows.append(f"| **Total** | | | **{tot_m}** | **{fmt_h(tot_h)}** | **{tot_l}** planned | | | |")
    rows.append("")
    rows.append("Hours are **planning estimates** (module authoring budgets), not measured learner times. The portfolio total counts modules that appear in several pathways once.")
    return "\n".join(rows)


def block_modules(catalog: dict, **_) -> str:
    out: list[str] = []
    for c in catalog["courses"]:
        out += [f"### {c['title']} (`{c['id']}`)", "",
                f"Prerequisites: {', '.join('`'+p+'`' for p in c['prerequisites']) or 'none'} · Estimated hours: {fmt_h(c['estimated_duration_hours'])} · Capstone: {c['capstone']}", "",
                "| Module | Title | Level | Hours | State | Primary outcome (observable) |", "|---|---|---:|---:|---|---|"]
        for m in c["modules"]:
            state = m["status"] + (f" / lab {m['lab_state']}" if m.get("lab_state") else "")
            reuse = f" _(reuses {', '.join(m['reuses'])})_" if m.get("reuses") else ""
            out.append(f"| `{m['id']}` | {esc(m['title'])} | L{m['level']} | {fmt_h(m['estimated_hours'])} | {state} | {esc(m['primary_outcome'])}{reuse} |")
        out.append("")
    return "\n".join(out).rstrip()


def block_levels(pathways: dict, **_) -> str:
    rows = ["| Level | Name | What the learner can do | Evidence collected | Supervision |", "|---:|---|---|---|---|"]
    for lv in pathways["levels"]:
        rows.append(f"| L{lv['id']} | {esc(lv['name'])} | {esc(lv['descriptor'])} | {esc(lv['evidence'])} | {esc(lv['supervision'])} |")
    return "\n".join(rows)


def path_summary(p: dict, catalog: dict) -> tuple[list[str], float, int]:
    by_id = {c["id"]: c for c in catalog["courses"]}
    lines, hours, n = [], 0.0, 0
    for step in p["steps"]:
        c = by_id[step["course"]]
        mods = pathway_modules(step, c)
        h = sum(m["estimated_hours"] for m in mods)
        hours += h; n += len(mods)
        scope = "all modules" if step.get("modules") is None else ", ".join(m["id"] for m in mods)
        note = f" — {step['note']}" if step.get("note") else ""
        lines.append(f"{c['title']} (`{c['id']}`): {scope} · {len(mods)} modules · {fmt_h(h)} h{note}")
    return lines, hours, n


def block_pathways(catalog: dict, pathways: dict, **_) -> str:
    out = ["| Pathway | Modules | Planning hours | Capstone | Courses in order |", "|---|---:|---:|---|---|"]
    for p in pathways["pathways"]:
        lines, hours, n = path_summary(p, catalog)
        courses = " → ".join(f"`{s['course'].replace('COURSE-', '')}`" + ("*" if s.get("modules") else "") for s in p["steps"])
        out.append(f"| **{esc(p['title'])}** (`{p['id']}`) | {n} | {fmt_h(hours)} | `{p['capstone_module']}` | {courses} |")
    out += ["", "`*` = only the listed modules of that course. Hours are planning estimates."]
    return "\n".join(out)


def block_pathway_detail(catalog: dict, pathways: dict, **_) -> str:
    out: list[str] = []
    for p in pathways["pathways"]:
        lines, hours, n = path_summary(p, catalog)
        out += [f"### {p['title']} (`{p['id']}`)", "", f"_Audience:_ {p['audience']}  ", f"_Capstone evidence:_ `{p['capstone_module']}`  ", f"_Total:_ {n} modules, {fmt_h(hours)} planning hours", ""]
        out += [f"{i}. {line}" for i, line in enumerate(lines, 1)]
        out.append("")
    return "\n".join(out).rstrip()


def block_level_matrix(catalog: dict, **_) -> str:
    rows = ["| Course | L0 | L1 | L2 | L3 |", "|---|---:|---:|---:|---:|"]
    for c in catalog["courses"]:
        cnt = defaultdict(int)
        for m in c["modules"]:
            cnt[m["level"]] += 1
        rows.append(f"| `{c['id']}` | " + " | ".join(str(cnt[i]) if cnt[i] else "·" for i in range(4)) + " |")
    return "\n".join(rows)


def block_products(catalog: dict, **_) -> str:
    rows = ["| Candidate product | Based on | Format hypothesis | Content ready | Blocking gates (from gate report) | Price |",
            "|---|---|---|---|---|---|"]
    for c in catalog["courses"]:
        built = c["lab_coverage"]["built"]
        ready = f"{built}/{c['lab_coverage']['planned']} labs built" if built else "plan only (no learner content built)"
        if c["lifecycle"] == "PILOT_BUILT":
            ready = f"1 module built (SOC-M04); {built}/{c['lab_coverage']['planned']} labs built"
        fmt = "self-paced course with automated lab checks" if c["id"] != "COURSE-FND-DIGITAL" else "self-paced entry course (free or low-friction entry is a hypothesis to test)"
        blockers = []
        if c["source_ids"]:
            blockers.append("licence/provenance (G1)")
        if c["review_status"] != "SME_REVIEWED":
            blockers.append("SME review (G7)")
        if c["lab_coverage"]["verified_executable"] != c["lab_coverage"]["planned"]:
            blockers.append("labs (G4)")
        if c["assessment_coverage"]["outcomes_assessed"] != c["assessment_coverage"]["outcomes_total"]:
            blockers.append("assessments (G3)")
        if c.get("blocking_findings"):
            blockers.append("open P0/P1 (G8)")
        rows.append(f"| {esc(c['title'])} | {', '.join('`'+s+'`' for s in c['source_ids']) or 'new'} | {fmt} | {ready} | {', '.join(blockers)} | NOT SET (owner decision) |")
    return "\n".join(rows)


def block_pathway_products(catalog: dict, pathways: dict, **_) -> str:
    rows = ["| Candidate bundle | Pathway | Modules | Planning hours | Status |", "|---|---|---:|---:|---|"]
    for p in pathways["pathways"]:
        _, hours, n = path_summary(p, catalog)
        rows.append(f"| {esc(p['title'])} pathway | `{p['id']}` | {n} | {fmt_h(hours)} | HYPOTHESIS — not buildable until its courses leave REENGINEERING |")
    return "\n".join(rows)


def block_totals(catalog: dict, **_) -> str:
    cs = catalog["courses"]
    mods = [m for c in cs for m in c["modules"]]
    built = [m for m in mods if m["status"] != "PLANNED"]
    labs = {k: sum(c["lab_coverage"][k] for c in cs) for k in ("planned", "built", "verified_executable")}
    oc = {k: sum(c["assessment_coverage"][k] for c in cs) for k in ("outcomes_total", "outcomes_assessed")}
    by_status = defaultdict(int)
    for c in cs:
        by_status[c["release_status"]] += 1
    reviewed = sum(1 for c in cs if c["review_status"] == "SME_REVIEWED")
    owned = sum(1 for c in cs if c["owner"] != "UNASSIGNED")
    rows = ["| Measure | Value |", "|---|---:|",
            f"| Courses | {len(cs)} |",
            f"| Modules planned / with built content | {len(mods)} / {len(built)} |",
            f"| Labs planned / built / verified executable in QA | {labs['planned']} / {labs['built']} / {labs['verified_executable']} |",
            f"| Module outcomes total / assessed | {oc['outcomes_total']} / {oc['outcomes_assessed']} |",
            f"| Courses with SME review recorded | {reviewed} |",
            f"| Courses with a named owner | {owned} |",
            "| Courses by release status | " + ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())) + " |"]
    return "\n".join(rows)


BLOCKS = {
    "totals": block_totals,
    "portfolio": block_portfolio, "modules": block_modules, "levels": block_levels, "pathways": block_pathways,
    "pathway-detail": block_pathway_detail, "level-matrix": block_level_matrix, "products": block_products,
    "pathway-products": block_pathway_products,
}
REGION = re.compile(r"(<!-- BEGIN GENERATED: (?P<name>[a-z-]+) -->)\n.*?\n?(<!-- END GENERATED: (?P=name) -->)", re.S)


def render(path: Path, ctx: dict) -> tuple[str, str, list[str]]:
    text = path.read_text(encoding="utf-8")
    used: list[str] = []

    def sub(m: re.Match) -> str:
        name = m.group("name")
        if name not in BLOCKS:
            raise SystemExit(f"{path}: unknown generated block '{name}'")
        used.append(name)
        return m.group(1) + "\n" + BLOCKS[name](**ctx) + "\n" + m.group(3)

    return text, REGION.sub(sub, text), used


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail when generated regions are out of date")
    a = ap.parse_args()
    ctx = {"catalog": load_yaml(CATALOG), "pathways": load_yaml(PATHWAYS)}
    drift = []
    total = 0
    for key, path in DOCS.items():
        if not path.exists():
            drift.append(f"{path.relative_to(ROOT)}: missing")
            continue
        old, new, used = render(path, ctx)
        total += len(used)
        if old != new:
            if a.check:
                drift.append(f"{path.relative_to(ROOT)}: generated regions are stale")
            else:
                path.write_text(new, encoding="utf-8")
    if drift:
        print("program documents out of date:\n  - " + "\n  - ".join(drift))
        return 1
    print(f"program documents {'up to date' if a.check else 'rendered'}: {len(DOCS)} files, {total} generated regions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
