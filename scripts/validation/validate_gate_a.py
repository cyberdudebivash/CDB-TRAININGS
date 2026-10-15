#!/usr/bin/env python3
"""Independent Gate A validator: fails if any artifact claims more than the evidence supports.

It is deliberately separate from the generator (scripts/production/gate_a.py + render_production_docs.py) and is wired into scripts/validation/run_qa.py, so a change that
promotes an unfinished course, hand-edits a status, fabricates a review, or leaves a placeholder in finished content cannot pass the automated gate.

Checks
  G01  no catalog release_status or module status claims more than the computed state (an incomplete course cannot be promoted to TRAINING_CONTENT_GO)
  G02  catalog and data files use the three-gate vocabulary (PRODUCTION_GO is retired; Gate B and Gate C are not recorded as achieved anywhere)
  G03  the human-review register is well formed: named humans only, real dates, evidence reference, no automation as reviewer, no simulated learner pilots
  G04  the adversarial-review register is well formed and refers to modules that exist and are technically verified
  G05  no placeholder or unfinished-content marker in the student-facing files of implemented modules
  G06  the scenario register is consistent (a scenario cannot be TECHNICALLY_VERIFIED without a classification, a failure injection and evidence names that exist)
  G07  the defect and incident registers are consistent (no P0/P1 closed without a recorded closing statement)
  G08  every source page the text scan cannot judge (no text layer, near blank) has a recorded visual inspection, and a visual inspection is never labelled as human review
Exit code 0 = all pass, 1 = at least one failure. Each failure is one line, so the output is usable in logs.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "production"))
import gate_a as G  # noqa: E402

ALLOWED_RELEASE_STATUS = {"REENGINEERING", "NOT_STARTED", "IN_BUILD", "REVIEW_REQUIRED", "TRAINING_CONTENT_GO", "BLOCKED", "DRAFT", "PILOT", "READY_FOR_REVIEW", "RETIRED"}
REVIEW_KINDS = {"SME", "EDITORIAL", "LEARNER_PILOT", "OWNER_ACCEPTANCE"}
REVIEW_OUTCOMES = {"APPROVED", "APPROVED_WITH_CHANGES", "CHANGES_REQUIRED", "REJECTED"}
ADVERSARIAL_OUTCOMES = {"CLEAN", "FINDINGS_REMEDIATED", "FINDINGS_OPEN"}
AUTOMATION_NAMES = re.compile(r"\b(claude|assistant|chatgpt|gpt|copilot|bot|automation|simulated|synthetic|llm|ai model|language model)\b", re.I)
PLACEHOLDER = re.compile(r"(?i)\b(TBD|TBA|FIXME|XXX|lorem ipsum|coming soon|under construction|work in progress|insert (?:\w+ )?here)\b|\bWIP\b|(?:^|[\[(:\u2013\u2014-]\s*)to be (?:written|added|completed|determined|decided|filled)\b")
TODO = re.compile(r"\bTODO\b")
GATE_B_C_ACHIEVED = re.compile(r"(?i)\b(COMMERCIAL_GO|ACADEMY_LIVE_GO)\b\s*[:=]\s*(true|yes|achieved|granted|pass(?:ed)?|go)\b")
STUDENT_FACING = ["lesson.md", "outcomes.yaml", "source-map.yaml", "assessment/quiz.yaml", "assessment/quiz.md", "assessment/rubric.yaml", "lab-guided/README.md", "lab-independent/README.md"]


def check_claims(p: G.Portfolio) -> list[str]:
    return [f"G01 {x}" for x in G.claims_exceed_evidence(p)]


def check_vocabulary(p: G.Portfolio) -> list[str]:
    out = []
    for c in p.catalog["courses"]:
        if c["release_status"] not in ALLOWED_RELEASE_STATUS:
            out.append(f"G02 {c['id']}: release_status {c['release_status']!r} is not in the Gate A vocabulary")
    for rel in ("catalog/courses.yaml", "docs/release/data/readiness_inputs_2026.yaml", "docs/production/data/continuity.yaml", "docs/production/data/human_reviews.yaml"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in GATE_B_C_ACHIEVED.finditer(text):
            out.append(f"G02 {rel}: records {m.group(0)!r}; Gate B and Gate C are not achieved or assessed in this phase")
    return out


def check_human_reviews(p: G.Portfolio) -> list[str]:
    out, seen = [], set()
    module_ids = {m["id"] for c in p.catalog["courses"] for m in c["modules"]}
    course_ids = {c["id"] for c in p.catalog["courses"]}
    for r in p.reviews:
        rid = r.get("id", "?")
        if rid in seen:
            out.append(f"G03 {rid}: duplicate review id")
        seen.add(rid)
        for field in ("id", "kind", "course", "scope", "reviewer", "role", "date", "outcome", "evidence", "human"):
            if r.get(field) in (None, "", []):
                out.append(f"G03 {rid}: missing field {field}")
        if r.get("kind") not in REVIEW_KINDS:
            out.append(f"G03 {rid}: unknown kind {r.get('kind')!r}")
        if r.get("outcome") not in REVIEW_OUTCOMES:
            out.append(f"G03 {rid}: unknown outcome {r.get('outcome')!r}")
        if r.get("human") is not True:
            out.append(f"G03 {rid}: `human: true` is required; automated or simulated reviews do not count")
        if AUTOMATION_NAMES.search(str(r.get("reviewer", ""))) or AUTOMATION_NAMES.search(str(r.get("role", ""))):
            out.append(f"G03 {rid}: reviewer or role names an automated or simulated participant")
        if r.get("course") not in course_ids:
            out.append(f"G03 {rid}: unknown course {r.get('course')!r}")
        scope = r.get("scope") or []
        if scope != ["*"] and not set(scope) <= module_ids:
            out.append(f"G03 {rid}: scope names modules that are not in the catalog")
        try:
            d = r["date"] if isinstance(r["date"], date) else date.fromisoformat(str(r["date"]))
            if d > date.fromisoformat(str(p.scenarios["as_of"])):
                out.append(f"G03 {rid}: review date {d} is after the register date {p.scenarios['as_of']}")
        except (KeyError, ValueError):
            out.append(f"G03 {rid}: date is not a valid ISO date")
        if r.get("kind") == "LEARNER_PILOT" and not (isinstance(r.get("participants"), int) and r["participants"] >= 1):
            out.append(f"G03 {rid}: a learner pilot must record the number of real participants")
    return out


def check_adversarial(p: G.Portfolio) -> list[str]:
    out = []
    for r in p.adversarial:
        rid = r.get("id", "?")
        for field in ("id", "module", "date", "outcome", "reviewer", "findings", "evidence"):
            if r.get(field) in (None, ""):
                out.append(f"G04 {rid}: missing field {field}")
        if r.get("outcome") not in ADVERSARIAL_OUTCOMES:
            out.append(f"G04 {rid}: unknown outcome {r.get('outcome')!r}")
        mod = p.modules.get(r.get("module"))
        if mod is None:
            out.append(f"G04 {rid}: unknown module {r.get('module')!r}")
        elif G.STATES.index(mod["state"]) < G.STATES.index("TECHNICALLY_VERIFIED") and r.get("outcome") in ("CLEAN", "FINDINGS_REMEDIATED"):
            out.append(f"G04 {rid}: module {mod['id']} is {mod['state']}; an adversarial review cannot be clean on an unverified module")
    return out


def find_placeholders(text: str, rel: str) -> list[str]:
    out = []
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            in_fence = not in_fence
        for m in PLACEHOLDER.finditer(line):
            out.append(f"G05 {rel}:{n}: unfinished-content marker {m.group(0)!r}")
        if TODO.search(line) and not re.search(r"`TODO`|TODO\W+(?:Step|V\d)|replace each TODO|replace every TODO", line):
            out.append(f"G05 {rel}:{n}: TODO in finished content")
    return out


def check_placeholders(p: G.Portfolio) -> list[str]:
    out = []
    for c in p.catalog["courses"]:
        for m in c["modules"]:
            rec = p.modules[m["id"]]
            if G.STATES.index(rec["state"]) < G.STATES.index("IMPLEMENTED_UNVERIFIED"):
                continue
            paths, _, _ = G.module_files(c, m["id"], STUDENT_FACING)
            for name, path in paths.items():
                if path.exists():
                    out += find_placeholders(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())
            lesson = paths["lesson.md"]
            if lesson.exists():
                headings = [(i, ln) for i, ln in enumerate(lesson.read_text(encoding="utf-8").splitlines()) if ln.startswith("## ")]
                lines = lesson.read_text(encoding="utf-8").splitlines()
                for (i, ln), nxt in zip(headings, headings[1:] + [(len(lines), "")]):
                    body = [x for x in lines[i + 1:nxt[0]] if x.strip()]
                    if not body:
                        out.append(f"G05 {lesson.relative_to(ROOT).as_posix()}:{i + 1}: empty section {ln!r}")
    return out


def check_scenarios(p: G.Portfolio) -> list[str]:
    out = []
    ids = set()
    names = {r["id"] for r in (p.qa or {}).get("results", [])}          # recorded QA check ids (for example the SOC end-to-end labs)
    for path in (ROOT / "tests").glob("*.py"):
        names |= set(re.findall(r"def (test_\w+)", path.read_text(encoding="utf-8")))
    for s in p.scenarios["scenarios"]:
        if s["id"] in ids:
            out.append(f"G06 {s['id']}: duplicate scenario id")
        ids.add(s["id"])
        if s["course"] not in {c["id"] for c in p.catalog["courses"]}:
            out.append(f"G06 {s['id']}: unknown course {s['course']}")
        if s["status"] == "TECHNICALLY_VERIFIED":
            if s["classification"] == "NONE_YET":
                out.append(f"G06 {s['id']}: TECHNICALLY_VERIFIED needs a classification")
            if not s["failure_injections"]:
                out.append(f"G06 {s['id']}: TECHNICALLY_VERIFIED needs at least one failure injection")
            for e in s["evidence"]:
                if e not in names:
                    out.append(f"G06 {s['id']}: evidence {e} is neither a test in tests/ nor a recorded QA check")
        for mod in s["modules"]:
            if mod not in p.modules:
                out.append(f"G06 {s['id']}: unknown module {mod}")
    return out


def check_registers(p: G.Portfolio) -> list[str]:
    out = []
    for d in p.defects:
        if d["status"] == "CLOSED" and not d.get("closed_by"):
            out.append(f"G07 {d['id']}: closed without a `closed_by` statement naming the evidence")
    for i in p.incidents:
        if i["status"] == "CLOSED" and not i.get("closed_by"):
            out.append(f"G07 {i['id']}: closed without a `closed_by` statement naming the evidence")
    return out


def check_visual_review(p: G.Portfolio) -> list[str]:
    out = []
    flagged = G.flagged_pages()
    recorded = [(v["source"], v["page"]) for v in p.visual["pages"]]
    for key in sorted(flagged - set(recorded)):
        out.append(f"G08 {key[0]} page {key[1]} needs visual inspection and has none recorded")
    for key in sorted(set(recorded) - flagged):
        out.append(f"G08 {key[0]} page {key[1]} has a visual inspection but is not a flagged page")
    if len(recorded) != len(set(recorded)):
        out.append("G08 duplicate visual inspection entries")
    if p.visual.get("method") != "MODEL_VISUAL_INSPECTION":
        out.append("G08 visual_review.yaml must state method MODEL_VISUAL_INSPECTION unless a human review is recorded in human_reviews.yaml")
    if p.visual.get("human_reviewed") is not False and not any(r.get("kind") == "SME" for r in p.reviews):
        out.append("G08 visual_review.yaml claims human review but no human review is recorded")
    for v in p.visual["pages"]:
        if v["content_type"] not in ("cover", "figure_page", "text_as_image", "blank_page") or not v.get("summary") or not v.get("disposition"):
            out.append(f"G08 {v['source']} page {v['page']}: incomplete record")
    return out


def run(p: G.Portfolio | None = None) -> list[str]:
    p = p or G.Portfolio()
    return check_claims(p) + check_vocabulary(p) + check_human_reviews(p) + check_adversarial(p) + check_placeholders(p) + check_scenarios(p) + check_registers(p) + check_visual_review(p)


def main() -> int:
    failures = run()
    for f in failures:
        print("FAIL", f)
    print(f"gate A validator: {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
