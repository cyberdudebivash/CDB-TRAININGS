#!/usr/bin/env python3
"""Gate A (TRAINING_CONTENT_GO): compute the state of every module and course from repository artifacts and evidence files.

Nothing in this module reads a status that someone typed to certify completeness. A module is `IMPLEMENTED_UNVERIFIED` only if its files exist, `TECHNICALLY_VERIFIED`
only if the recorded lab-matrix run executed its tests and they passed, `REVIEW_REQUIRED` only if an adversarial review is recorded, and no module or course reaches
`TRAINING_CONTENT_GO` without human approvals that only a person can enter in docs/production/data/human_reviews.yaml.

Gate B (commercial) and Gate C (Academy) are not computed here and are not part of this assignment.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "production" / "data"
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
import evidence_fingerprint as EF  # noqa: E402

STATES = ["NOT_STARTED", "IN_PROGRESS", "IMPLEMENTED_UNVERIFIED", "TECHNICALLY_VERIFIED", "REVIEW_REQUIRED", "TRAINING_CONTENT_GO"]
MET, PARTIAL, NOT_MET, NOT_ASSESSED = "MET", "PARTIAL", "NOT_MET", "NOT_ASSESSED"
OPEN_VERIFICATION = {"NEEDS_VERIFICATION", "SECONDARY_ONLY", "MACHINE_ONLY"}
STAGE_B_DATE = "2026-10-24"

# The SOC pilot module predates the standard module layout; everything else uses courses/<slug>/modules/<ID>/.
SOC_PILOT = {
    "SOC-M04": {
        "lesson.md": "courses/soc-analyst/lessons/m04-auth-detection/lesson.md",
        "outcomes.yaml": "courses/soc-analyst/curriculum/outcomes.yaml",
        "source-map.yaml": "courses/soc-analyst/curriculum/source-map.yaml",
        "assessment/quiz.yaml": "courses/soc-analyst/assessments/m04/quiz.yaml",
        "assessment/quiz.md": "courses/soc-analyst/assessments/m04/quiz.md",
        "assessment/rubric.yaml": "courses/soc-analyst/assessments/m04/rubric.yaml",
        "lab-guided/README.md": "courses/soc-analyst/labs/m04-guided/README.md",
        "lab-independent/README.md": "courses/soc-analyst/labs/m04-independent/README.md",
        "_edition": "courses/soc-analyst/student/student-edition.yaml",
        "_private": ["courses/soc-analyst/instructor/m04-quiz-answer-key.md", "courses/soc-analyst/instructor/m04-grading-notes.md"],
    }
}


def load_yaml(rel: str | Path):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def load_json(rel: str | Path):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def latest_lab_matrix() -> dict | None:
    files = sorted((ROOT / "docs" / "qa" / "data").glob("lab_execution_*.json"))
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


# ------------------------------------------------------------------------------------------------------ module level
def module_files(course: dict, module_id: str, required: list[str]) -> tuple[dict[str, Path], Path | None, list[Path]]:
    """Return ({required file name: path}, student edition config path or None, private pack paths)."""
    if module_id in SOC_PILOT:
        spec = SOC_PILOT[module_id]
        return {name: ROOT / spec[name] for name in required}, ROOT / spec["_edition"], [ROOT / p for p in spec["_private"]]
    folder = ROOT / "courses" / course["slug"] / "modules" / module_id
    edition = ROOT / "courses" / course["slug"] / "student" / f"{module_id}-student-edition.yaml"
    private = ROOT / "courses" / course["slug"] / "instructor" / module_id
    return {name: folder / name for name in required}, edition, [private / "answer-key.md", private / "grading-notes.md"]


def count_blocks(markdown: str) -> dict[str, int]:
    kinds = Counter()
    for m in re.finditer(r"^```([^\n]*)\n", markdown, re.M):
        tokens = m.group(1).split()
        if len(tokens) >= 2 and tokens[0] == "python" and (tokens[1] in ("run", "test") or tokens[1].startswith("module=")):
            kinds["executed_python"] += 1
    return dict(kinds)


def lesson_facts(path: Path) -> dict:
    if not path.exists():
        return {"words": 0, "sections": 0, "executed_blocks": 0, "versions_cited": None, "last_verified": None, "research_refs": [], "probe_refs": [], "findings": []}
    text = path.read_text(encoding="utf-8")
    front = {}
    if text.startswith("---"):
        try:
            front = yaml.safe_load(text.split("---", 2)[1]) or {}
        except yaml.YAMLError:
            front = {}
    body = text.split("---", 2)[2] if text.startswith("---") else text
    return {"words": len(re.findall(r"\w+", body)), "sections": len(re.findall(r"^## \d+\.", body, re.M)), "executed_blocks": count_blocks(body).get("executed_python", 0),
            "versions_cited": front.get("versions_cited"), "last_verified": str(front.get("last_verified")) if front.get("last_verified") else None,
            "research_refs": sorted(set(re.findall(r"\bR-\d{3}\b", text))), "probe_refs": sorted(set(re.findall(r"`([a-z0-9-]+)` probe|probe `([a-z0-9-]+)`", text))),
            "findings": sorted(set(re.findall(r"\bF-[A-Z]+-\d{3}\b", text)))}


def input_changes(commit: str, inputs: list[str]) -> list[str] | None:
    """Files under `inputs` whose content differs from their content at `commit` (new, removed or modified). Content-based, so it does not depend on whether the change is committed yet.
    None if the commit cannot be resolved in this clone (the evidence is then unverifiable)."""
    if subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True).returncode != 0:
        return None
    then: dict[str, str] = {}
    for line in subprocess.run(["git", "ls-tree", "-r", commit, "--", *inputs], cwd=ROOT, capture_output=True, text=True).stdout.splitlines():
        meta, path = line.split("\t", 1)
        then[path] = meta.split()[2]
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *inputs], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    now_files = sorted({f for f in listed if (ROOT / f).is_file() and "__pycache__" not in f and not f.endswith(".pyc")})
    now: dict[str, str] = {}
    if now_files:
        hashes = subprocess.run(["git", "hash-object", "--", *now_files], cwd=ROOT, capture_output=True, text=True).stdout.split()
        now = dict(zip(now_files, hashes))
    return sorted(p for p in set(then) | set(now) if then.get(p) != now.get(p) and "__pycache__" not in p)


def edition_is_fresh(entry: dict) -> bool:
    """A recorded edition build counts only while every source file still has the content it was built from."""
    sources = entry.get("sources") or {}
    if not sources:
        return False
    for rel, digest in sources.items():
        path = ROOT / rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
    return True


def matrix_evidence(module_id: str, matrix: dict | None, qa: dict | None, inputs: list[str] | None = None, slug: str | None = None) -> dict:
    """Execution evidence for a module from the recorded lab-matrix run (Python Engineering) or the recorded QA run (SOC pilot)."""
    if module_id in SOC_PILOT:
        by_id = {r["id"]: r["status"] for r in (qa or {}).get("results", [])}
        wanted = ["lab-guided-e2e", "lab-independent-e2e", "pytest"]
        ok = all(by_id.get(w) == "PASS" for w in wanted)
        return {"kind": "qa_run", "valid": ok, "interpreters": ["CPython " + (qa or {}).get("python", "?")], "tests": len(wanted), "skipped": [], "negative_controls": ok, "detail": "recorded QA run: " + ", ".join(f"{w} {by_id.get(w, 'absent')}" for w in wanted)}
    if not matrix or not module_id.startswith("PY-M"):
        return {"kind": "none", "valid": False, "interpreters": [], "tests": 0, "skipped": [], "negative_controls": False, "detail": "no recorded execution evidence for this module"}
    nn = int(module_id.split("M")[-1])
    lab_marker, pack_marker = f"::test_m{nn:02d}_", f"[{module_id}]"
    interpreters, tests, skipped, failed = [], set(), [], []
    ran = [i for i in matrix["interpreters"] if i["status"] != "NOT_EXECUTED"]
    for interp in ran:
        mine = [t for t in interp["tests"] if lab_marker in t["id"] or t["id"].endswith(pack_marker)]
        interpreters.append(interp["python"])
        for t in mine:
            tests.add(t["id"])
            if t["outcome"] == "skipped":
                skipped.append(f"{t['id']} on {interp['python']}")
            elif t["outcome"] != "passed":
                failed.append(f"{t['id']} on {interp['python']}")
    lab_tests = [t for t in tests if lab_marker in t]
    negative = any(re.search(r"starter.*(fail|defect)|mutant|discriminating|exploit|reintroduc|kill", t) for t in lab_tests)
    stale: list[str] = []
    unverifiable = False
    recorded = (matrix.get("fingerprints") or {}).get(module_id)
    if inputs and recorded:                                    # content fingerprint: independent of commit ids, survives squash merges and rebases
        if EF.fingerprint(inputs) != recorded:
            stale = ["content of the module's lesson, labs or shared lab tools differs from the content that was executed"]
        recorded_private = (matrix.get("private_fingerprints") or {}).get(module_id)
        current_private = EF.private_fingerprint(slug, module_id) if slug else None
        if recorded_private and current_private and recorded_private != current_private:
            stale.append("the private instructor pack differs from the one that was executed")
    elif inputs:                                               # older record without fingerprints: compare with the recorded commit
        changed = input_changes(matrix.get("commit", ""), inputs)
        if changed is None:
            unverifiable = True
        else:
            stale = changed
    valid = bool(ran) and len(lab_tests) >= 3 and not failed and not skipped and len(ran) >= 3 and not stale and not unverifiable
    note = f"; STALE: {stale[0]}" if stale and recorded else f"; STALE: {len(stale)} input file(s) changed after the recorded run at {matrix.get('commit')}" if stale else "; recorded commit not found in this clone" if unverifiable else ""
    return {"kind": "lab_matrix", "valid": valid, "interpreters": interpreters, "tests": len(tests), "lab_tests": len(lab_tests), "skipped": skipped, "failed": failed, "negative_controls": negative, "stale_inputs": stale[:5],
            "detail": f"{len(tests)} tests on {len(ran)} interpreters; failed {len(failed)}, skipped {len(skipped)}{note}"}


class Portfolio:
    def __init__(self, overrides: dict | None = None) -> None:
        """`overrides` replaces loaded inputs by attribute name before anything is computed. It exists so tests can try to promote an incomplete course; production use passes nothing."""
        self.criteria = load_yaml(DATA / "gate_a_criteria.yaml")
        self.catalog = load_yaml("catalog/courses.yaml")
        self.summary = load_json("docs/audits/data/page_audit_summary.json")
        self.matrix = latest_lab_matrix()
        qa_path = ROOT / "docs" / "release" / "data" / "qa_run.json"
        self.qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else None
        self.reviews = (load_yaml(DATA / "human_reviews.yaml") or {}).get("reviews") or []
        self.adversarial = (load_yaml(DATA / "adversarial_reviews.yaml") or {}).get("reviews") or []
        self.incidents = load_yaml(DATA / "incidents.yaml")["incidents"]
        self.defects = load_yaml(DATA / "defects.yaml")["defects"]
        self.scenarios = load_yaml(DATA / "operational_scenarios.yaml")
        manifest = DATA / "pdf_manifest.json"
        self.pdfs = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {"editions": [], "course_editions": []}
        self.inputs = load_yaml("docs/release/data/readiness_inputs_2026.yaml")
        self.changes = load_yaml("docs/audits/data/modernization_changes.yaml")["changes"]
        self.page_stats = dict(self.summary["sources"]) if isinstance(self.summary["sources"], list) else self.summary["sources"]
        for name, value in (overrides or {}).items():
            if not hasattr(self, name):
                raise AttributeError(f"unknown Portfolio input {name}")
            setattr(self, name, value)
        self.modules = {m["id"]: self.module_record(c, m) for c in self.catalog["courses"] for m in c["modules"]}
        self.courses = {c["id"]: self.course_record(c) for c in self.catalog["courses"]}

    # ------------------------------------------------------------------------------------------ modules
    def module_record(self, course: dict, module: dict) -> dict:
        required = self.criteria["module_required_files"]
        paths, edition, private = module_files(course, module["id"], required)
        present = {name: p.exists() for name, p in paths.items()}
        missing = [n for n, ok in present.items() if not ok]
        lesson = lesson_facts(paths["lesson.md"])
        evidence = matrix_evidence(module["id"], self.matrix, self.qa, EF.execution_inputs(course["slug"], module["id"]), course["slug"])
        reviewed = [r for r in self.adversarial if r["module"] == module["id"] and r["outcome"] in ("CLEAN", "FINDINGS_REMEDIATED")]
        edition_manifest = next((e for e in self.pdfs["editions"] if e.get("module") == module["id"]), None)
        if edition_manifest:
            edition_manifest = {**edition_manifest, "fresh": edition_is_fresh(edition_manifest)}
            edition_manifest["passed"] = bool(edition_manifest.get("passed")) and edition_manifest["fresh"]      # a build whose sources changed afterwards is not evidence
        any_files = any(present.values())
        if module["status"] == "PLANNED" and not any_files:
            state = "NOT_STARTED"
        elif missing or module["status"] == "PLANNED":
            state = "IN_PROGRESS"
        elif not evidence["valid"] or lesson["words"] < self.criteria["min_lesson_words"]:
            state = "IMPLEMENTED_UNVERIFIED"
        elif not reviewed:
            state = "TECHNICALLY_VERIFIED"
        else:
            state = "REVIEW_REQUIRED"          # a module never reaches TRAINING_CONTENT_GO on its own: only a whole course does, after human approvals
        outcomes = quiz = rubric = None
        if not missing:
            outs = yaml.safe_load(paths["outcomes.yaml"].read_text(encoding="utf-8")).get("outcomes", [])
            outcomes = len(outs)
            quiz = len(yaml.safe_load(paths["assessment/quiz.yaml"].read_text(encoding="utf-8")).get("items", []))
            rubric = len(yaml.safe_load(paths["assessment/rubric.yaml"].read_text(encoding="utf-8")).get("criteria", []))
        return {"id": module["id"], "course": course["id"], "title": module["title"], "catalog_status": module["status"], "estimated_hours": module["estimated_hours"], "state": state, "missing_files": missing,
                "lesson": lesson, "evidence": evidence, "adversarial_reviews": [r["id"] for r in reviewed], "edition_config": bool(edition and edition.exists()), "edition": edition_manifest,
                "private_pack_local": all(p.exists() for p in private), "outcomes": outcomes, "quiz_items": quiz, "rubric_criteria": rubric}

    # ------------------------------------------------------------------------------------------ courses
    def course_record(self, course: dict) -> dict:
        mods = [self.modules[m["id"]] for m in course["modules"]]
        required = len(mods)
        at_least = lambda s: sum(1 for m in mods if STATES.index(m["state"]) >= STATES.index(s))
        implemented, verified, reviewed = at_least("IMPLEMENTED_UNVERIFIED"), at_least("TECHNICALLY_VERIFIED"), at_least("REVIEW_REQUIRED")
        changes = [c for c in self.changes if c["course"] == course["id"]]
        verified_changes = [c for c in changes if c["verification"]["status"] in ("EXECUTED", "RESEARCH_VERIFIED")]
        open_changes = [c for c in changes if c["verification"]["status"] in OPEN_VERIFICATION]
        scenarios = [s for s in self.scenarios["scenarios"] if s["course"] == course["id"]]
        verified_scenarios = [s for s in scenarios if self.scenario_state(s) == "TECHNICALLY_VERIFIED"]
        realtime = [s for s in verified_scenarios if s["classification"] in ("CONTROLLED_LIVE", "REPLAY_SIMULATION")]
        sources = course.get("source_ids") or []
        pages_total = sum(self.page_stats[s]["pages"] for s in sources if s in self.page_stats)
        covered = self.source_pages_with_disposition(course)
        covered_n = sum(len(v) for v in covered.values())
        capstone = next((m for m in mods if m["title"].lower().startswith("capstone")), None)
        defects = [d for d in self.defects if d["status"] != "CLOSED" and ("*" in d["applies_to"] or course["id"] in d["applies_to"])]
        incidents = [i for i in self.incidents if i["status"] != "CLOSED" and ("*" in i["blocks"] or course["id"] in i["blocks"])]
        labs, outs = course["lab_coverage"], course["assessment_coverage"]
        ip = (self.inputs["course_overrides"].get(course["id"], {}) or {}).get("ip_licensing") or self.inputs["defaults"]["ip_licensing"]
        course_pdf = next((e for e in self.pdfs.get("course_editions", []) if e.get("course") == course["id"]), None)
        approvals = self.approvals(course["id"], [m["id"] for m in course["modules"]])
        rec = {"id": course["id"], "slug": course["slug"], "title": course["title"], "required": required, "implemented": implemented, "verified": verified, "reviewed": reviewed,
               "modules": [m["id"] for m in mods], "lessons_substantive": sum(1 for m in mods if m["lesson"]["words"] >= self.criteria["min_lesson_words"] and STATES.index(m["state"]) >= 3),
               "lesson_sections": sum(m["lesson"]["sections"] for m in mods if STATES.index(m["state"]) >= 2), "executed_blocks": sum(m["lesson"]["executed_blocks"] for m in mods),
               "labs": labs, "outcomes": outs, "changes_total": len(changes), "changes_verified": len(verified_changes), "changes_open": len(open_changes), "scenarios": scenarios, "scenarios_required": len(scenarios),
               "scenarios_verified": len(verified_scenarios), "realtime_verified": len(realtime), "source_pages": pages_total, "source_pages_with_disposition": covered_n, "capstone": capstone["id"] if capstone else None,
               "capstone_state": capstone["state"] if capstone else None, "defects": defects, "incidents": incidents, "ip": ip, "course_pdf": course_pdf, "approvals": approvals,
               "release_status_claimed": course["release_status"]}
        rec["criteria"] = self.criteria_for(course, rec, mods)
        rec["scores"] = self.scores_for(rec, mods)
        rec["score"] = round(sum(v["points"] for v in rec["scores"].values()), 1)
        rec["engineering_state"] = self.course_state(rec, mods)
        mandatory_met = all(c["status"] == MET for c in rec["criteria"].values())
        rec["eligible"] = mandatory_met and rec["score"] >= self.criteria["score_threshold"]
        rec["state"] = "TRAINING_CONTENT_GO" if rec["eligible"] else rec["engineering_state"]
        return rec

    def scenario_state(self, s: dict) -> str:
        """A scenario is TECHNICALLY_VERIFIED only if it has a real classification, a failure injection and evidence tests that the recorded executions passed."""
        if s["status"] != "TECHNICALLY_VERIFIED":
            return s["status"]
        if s["classification"] == "NONE_YET" or not s["failure_injections"] or not s["evidence"]:
            return "IN_PROGRESS"
        names = set()
        if self.matrix:
            for interp in self.matrix["interpreters"]:
                if interp["status"] != "NOT_EXECUTED":
                    names |= {t["id"].split("::")[-1] for t in interp["tests"] if t["outcome"] == "passed"}
        qa = {r["id"] for r in (self.qa or {}).get("results", []) if r["status"] == "PASS"}
        return "TECHNICALLY_VERIFIED" if all(e in names or e in qa for e in s["evidence"]) else "IMPLEMENTED_UNVERIFIED"

    def source_pages_with_disposition(self, course: dict) -> dict[str, set[int]]:
        out: dict[str, set[int]] = {s: set() for s in (course.get("source_ids") or [])}
        for m in course["modules"]:
            rec = self.modules[m["id"]]
            if STATES.index(rec["state"]) < 2:
                continue
            paths, _, _ = module_files(course, m["id"], ["source-map.yaml"])
            data = yaml.safe_load(paths["source-map.yaml"].read_text(encoding="utf-8"))
            src = data.get("source")
            if src in out:
                for mp in data.get("mappings", []):
                    out[src].update(int(p) for p in mp.get("source_pages", []))
        return out

    def approvals(self, course_id: str, module_ids: list[str]) -> dict[str, bool]:
        have = {}
        for kind in ("SME", "EDITORIAL", "LEARNER_PILOT", "OWNER_ACCEPTANCE"):
            rel = [r for r in self.reviews if r["kind"] == kind and r["outcome"] in ("APPROVED", "APPROVED_WITH_CHANGES") and r["course"] == course_id]
            scope = set()
            for r in rel:
                scope |= set(module_ids) if "*" in r["scope"] else set(r["scope"])
            have[kind] = bool(module_ids) and set(module_ids) <= scope
        return have

    def course_state(self, rec: dict, mods: list[dict]) -> str:
        if rec["implemented"] == 0 and not any(STATES.index(m["state"]) >= 1 for m in mods):
            return "NOT_STARTED"
        if rec["implemented"] < rec["required"]:
            return "IN_PROGRESS"
        states = [m["state"] for m in mods]
        if any(s == "IMPLEMENTED_UNVERIFIED" for s in states):
            return "IMPLEMENTED_UNVERIFIED"
        return "TECHNICALLY_VERIFIED" if any(s == "TECHNICALLY_VERIFIED" for s in states) else "REVIEW_REQUIRED"

    # ------------------------------------------------------------------------------------------ criteria
    def criteria_for(self, course: dict, rec: dict, mods: list[dict]) -> dict[str, dict]:
        c: dict[str, dict] = {}
        built = rec["implemented"] > 0

        def put(cid: str, status: str, detail: str) -> None:
            c[cid] = {"status": status, "detail": detail}

        frac = lambda n, d: MET if d and n == d else PARTIAL if n else NOT_MET
        put("A01", frac(rec["implemented"], rec["required"]), f"{rec['implemented']} of {rec['required']} required modules implemented")
        put("A02", frac(rec["lessons_substantive"], rec["required"]), f"{rec['lessons_substantive']} of {rec['required']} lessons substantive and executed ({rec['lesson_sections']} numbered sections, {rec['executed_blocks']} executed blocks)")
        if rec["source_pages"]:
            put("A03", frac(rec["source_pages_with_disposition"], rec["source_pages"]), f"{rec['source_pages_with_disposition']} of {rec['source_pages']} source pages have a recorded disposition in a built module's source map")
        else:
            put("A03", "NOT_APPLICABLE", "the course has no legacy source PDF")
        stage_b = "PENDING (not executable before " + STAGE_B_DATE + ")"
        put("A04", PARTIAL if rec["changes_verified"] else NOT_MET, f"{rec['changes_verified']} of {rec['changes_total']} change records EXECUTED or RESEARCH_VERIFIED, {rec['changes_open']} open; October 24 refresh {stage_b}")
        required_rt = self.scenarios["realtime_minimum_per_course"]
        put("A05", MET if rec["scenarios_required"] and rec["scenarios_verified"] == rec["scenarios_required"] and rec["realtime_verified"] >= required_rt else PARTIAL if rec["scenarios_verified"] else NOT_MET,
            f"{rec['scenarios_verified']} of {rec['scenarios_required']} operational scenarios technically verified; {rec['realtime_verified']} time-dependent scenario(s) verified (minimum {required_rt})")
        labs = rec["labs"]
        evidence_ok = all(m["evidence"]["valid"] for m in mods if STATES.index(m["state"]) >= 2)
        put("A06", MET if labs["verified_executable"] == labs["planned"] and evidence_ok and built else PARTIAL if labs["verified_executable"] else NOT_MET, f"{labs['verified_executable']} of {labs['planned']} planned labs verified executable")
        outs = rec["outcomes"]
        put("A07", MET if outs["outcomes_assessed"] == outs["outcomes_total"] and built else PARTIAL if outs["outcomes_assessed"] else NOT_MET, f"{outs['outcomes_assessed']} of {outs['outcomes_total']} outcomes assessed")
        put("A08", MET if rec["capstone_state"] and STATES.index(rec["capstone_state"]) >= 3 else NOT_MET, f"capstone module {rec['capstone'] or 'not defined'}: {rec['capstone_state'] or 'n/a'}")
        qa_ok = bool(self.qa) and all(r["status"] == "PASS" for r in self.qa["results"])
        no_skips = bool(self.matrix) and self.matrix.get("private_instructor_pack_present", False) and all(not i["skipped"] for i in self.matrix["interpreters"] if i["status"] != "NOT_EXECUTED")
        neg = all(m["evidence"]["negative_controls"] for m in mods if STATES.index(m["state"]) >= 2)
        put("A09", (MET if (qa_ok and (no_skips or not str(mods[0]["id"]).startswith("PY-")) and neg and rec["implemented"] == rec["required"]) else PARTIAL if built and qa_ok and neg else NOT_MET) if built else NOT_ASSESSED,
            "recorded automated QA run all PASS, negative controls present for built modules" if built and qa_ok else "no built content to assess" if not built else "recorded QA run not all PASS")
        privacy_open = [i for i in rec["incidents"] if i["kind"] in ("PRIVACY",)]
        put("A10", (NOT_MET if privacy_open else MET) if built or privacy_open else NOT_ASSESSED, "open privacy incident " + ", ".join(i["id"] for i in privacy_open) if privacy_open else "no open privacy or security incident applies" if built else "no built content to assess")
        ip = rec["ip"]
        put("A11", MET if ip["status"] == "MET" else NOT_MET, f"IP/licensing {ip['status']}" + (f" (blockers {', '.join(ip.get('blockers', []))})" if ip.get("blockers") else ""))
        editions = sum(1 for m in mods if m["edition_config"] and STATES.index(m["state"]) >= 2)
        put("A12", MET if editions == rec["required"] and rec["course_pdf"] else PARTIAL if editions else NOT_MET, f"{editions} of {rec['required']} module student-edition configs; complete course edition {'present' if rec['course_pdf'] else 'absent'}")
        private_ok = all(m["private_pack_local"] for m in mods if STATES.index(m["state"]) >= 2) and built
        d8_open = any(i["decision"] == "D8" and i["status"] != "CLOSED" for i in self.incidents)
        put("A13", MET if private_ok and not d8_open and rec["implemented"] == rec["required"] else PARTIAL if private_ok else NOT_MET if built else NOT_ASSESSED,
            f"private packs present locally for {sum(1 for m in mods if m['private_pack_local'])} modules; private repository (D8) {'NOT created' if d8_open else 'in place'}")
        cp = rec["course_pdf"]
        put("A14", MET if cp and cp.get("passed") and set(cp.get("modules", [])) >= set(rec["modules"]) else NOT_MET, "complete course edition validated" if cp and cp.get("passed") else "no complete course edition has been built; module previews are not course editions")
        ed_ok = sum(1 for m in mods if m["edition"] and m["edition"].get("passed"))
        put("A15", MET if ed_ok == rec["required"] and cp else PARTIAL if ed_ok else NOT_MET, f"{ed_ok} of {rec['required']} module editions pass the accessibility and structure gates")
        blockers = [d for d in rec["defects"] if d["severity"] in ("P0", "P1")]
        put("A16", NOT_MET if blockers else MET, f"{len(blockers)} open P0/P1 defects apply: " + ", ".join(d["id"] for d in blockers[:6]) + (" ..." if len(blockers) > 6 else "") if blockers else "none open")
        ap = rec["approvals"]
        put("A17", MET if ap["SME"] and ap["EDITORIAL"] else NOT_MET, f"SME review {'recorded' if ap['SME'] else 'not recorded'}; editorial review {'recorded' if ap['EDITORIAL'] else 'not recorded'}")
        put("A18", MET if ap["LEARNER_PILOT"] else NOT_MET, "learner pilot " + ("recorded" if ap["LEARNER_PILOT"] else "not recorded"))
        put("A19", MET if ap["OWNER_ACCEPTANCE"] else NOT_MET, "owner acceptance " + ("recorded" if ap["OWNER_ACCEPTANCE"] else "not recorded"))
        return c

    def scores_for(self, rec: dict, mods: list[dict]) -> dict[str, dict]:
        dims = {d["id"]: d for d in self.criteria["quality_dimensions"]}
        n = rec["required"]
        verified_mods = sum(1 for m in mods if STATES.index(m["state"]) >= 3)
        change_frac = rec["changes_verified"] / rec["changes_total"] if rec["changes_total"] else 1.0
        negative = sum(1 for m in mods if STATES.index(m["state"]) >= 2 and m["evidence"]["negative_controls"])
        editions_ok = sum(1 for m in mods if m["edition"] and m["edition"].get("passed"))
        labs = rec["labs"]
        outs = rec["outcomes"]
        capstone = 1.0 if rec["capstone_state"] and STATES.index(rec["capstone_state"]) >= 3 else 0.0
        no_open_blockers = 0.0 if any(d["severity"] in ("P0", "P1") for d in rec["defects"]) else 1.0
        pages = rec["source_pages_with_disposition"] / rec["source_pages"] if rec["source_pages"] else (rec["implemented"] / n if n else 0.0)
        raw = {
            "technical_accuracy_currency": (verified_mods / n) * change_frac,
            "curriculum_completeness": rec["implemented"] / n,
            "operational_relevance": rec["scenarios_verified"] / rec["scenarios_required"] if rec["scenarios_required"] else 0.0,
            "labs_reproducibility": labs["verified_executable"] / labs["planned"],
            "assessment_capstone": 0.7 * (outs["outcomes_assessed"] / outs["outcomes_total"]) + 0.3 * capstone,
            "security_reliability": 0.7 * (negative / n) + 0.3 * no_open_blockers,
            "clarity_accessibility": editions_ok / n,
            "pdf_integrity": 1.0 if rec["course_pdf"] and rec["course_pdf"].get("passed") else 0.0,
            "traceability_maintainability": pages,
        }
        return {k: {"name": dims[k]["name"], "weight": dims[k]["weight"], "fraction": round(v, 4), "points": round(dims[k]["weight"] * v, 2)} for k, v in raw.items()}

    # ------------------------------------------------------------------------------------------ portfolio summary
    def totals(self) -> dict:
        courses = list(self.courses.values())
        mods = list(self.modules.values())
        scenarios = self.scenarios["scenarios"]
        sc_states = Counter(self.scenario_state(s) for s in scenarios)
        return {
            "courses": len(courses),
            "modules_required": len(mods),
            "modules_implemented": sum(1 for m in mods if STATES.index(m["state"]) >= 2),
            "modules_verified": sum(1 for m in mods if STATES.index(m["state"]) >= 3),
            "module_states": dict(Counter(m["state"] for m in mods)),
            "course_states": dict(Counter(c["state"] for c in courses)),
            "go": sum(1 for c in courses if c["state"] == "TRAINING_CONTENT_GO"),
            "review_required": sum(1 for c in courses if c["state"] == "REVIEW_REQUIRED"),
            "courses_with_release_blockers": sum(1 for c in courses if any(x["status"] == NOT_MET for x in c["criteria"].values() if x is not None) and (c["incidents"] or c["defects"])),
            "labs_planned": sum(c["labs"]["planned"] for c in courses), "labs_verified": sum(c["labs"]["verified_executable"] for c in courses),
            "outcomes_total": sum(c["outcomes"]["outcomes_total"] for c in courses), "outcomes_assessed": sum(c["outcomes"]["outcomes_assessed"] for c in courses),
            "scenarios_required": len(scenarios), "scenarios_verified": sc_states.get("TECHNICALLY_VERIFIED", 0), "scenario_states": dict(sc_states),
            "realtime_courses_ok": sum(1 for c in courses if c["realtime_verified"] >= self.scenarios["realtime_minimum_per_course"]),
            "source_pages": sum(c["source_pages"] for c in courses), "source_pages_with_disposition": sum(c["source_pages_with_disposition"] for c in courses),
            "lessons_substantive": sum(c["lessons_substantive"] for c in courses),
            "course_pdfs_required": len(courses), "course_pdfs_validated": sum(1 for c in courses if c["course_pdf"] and c["course_pdf"].get("passed")),
            "module_editions_passing": sum(1 for m in mods if m["edition"] and m["edition"].get("passed")),
            "open_p0": sum(1 for d in self.defects if d["status"] != "CLOSED" and d["severity"] == "P0"), "open_p1": sum(1 for d in self.defects if d["status"] != "CLOSED" and d["severity"] == "P1"),
            "reviews_recorded": len(self.reviews),
        }


def claims_exceed_evidence(p: Portfolio) -> list[str]:
    """Problems for the validator: a catalog release_status or module status that claims more than the evidence supports."""
    problems = []
    for cid, rec in p.courses.items():
        if rec["release_status_claimed"] == "TRAINING_CONTENT_GO" and rec["state"] != "TRAINING_CONTENT_GO":
            failed = [k for k, v in rec["criteria"].items() if v["status"] not in (MET, "NOT_APPLICABLE")]
            problems.append(f"{cid}: catalog claims TRAINING_CONTENT_GO but Gate A computes {rec['state']} (criteria not met: {', '.join(failed)}; score {rec['score']})")
        if rec["release_status_claimed"] == "PRODUCTION_GO":
            problems.append(f"{cid}: PRODUCTION_GO is retired by the three-gate model; use TRAINING_CONTENT_GO (content), COMMERCIAL_GO or ACADEMY_LIVE_GO")
    for mid, m in p.modules.items():
        if m["catalog_status"] in ("BUILT", "BUILT_PILOT") and m["missing_files"]:
            problems.append(f"{mid}: catalog says {m['catalog_status']} but required files are missing: {', '.join(m['missing_files'])}")
        if m["catalog_status"] in ("BUILT", "BUILT_PILOT") and not m["evidence"]["valid"]:
            problems.append(f"{mid}: catalog says {m['catalog_status']} but there is no passing recorded execution evidence ({m['evidence']['detail']})")
    return problems


if __name__ == "__main__":
    pf = Portfolio()
    print(json.dumps(pf.totals(), indent=1))
