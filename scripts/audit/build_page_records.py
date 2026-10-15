#!/usr/bin/env python3
"""Build the page-level audit record for EVERY page of the ten source PDFs.

For each page the record carries the sixteen fields required by the modernization directive
(source_pdf, source_page, chapter, lesson, topic, technology, original_claim, evidence, issue_type, severity,
modernization_action, source_url, source_date, verification_status, destination_file, test_evidence) plus
machine-confidence fields. Nothing here claims a page was read by a person: a page cited by a finding in
docs/audits/data/findings.yaml is marked as read in context by the AI model (never as human review); every other page is `MACHINE_SCANNED_*`,
`MACHINE_FLAGGED_REVIEW_REQUIRED` or `VISUAL_REVIEW_REQUIRED`.

Inputs  : the ten PDFs (read-only), docs/audits/data/source_inventory.json, docs/research/technology_registry.yaml,
          docs/research/deprecation_rules.yaml, catalog/source_mapping.yaml, catalog/courses.yaml,
          docs/research/data/*_2026-10-14.json, docs/audits/data/findings.yaml, docs/research/research_register.yaml
Outputs : docs/audits/data/page_records/<SOURCE_ID>.partNN.jsonl  (<=500 pages each, compact JSON lines)
          docs/audits/data/page_records/INDEX.json                (parts, counts, sha256)
          docs/audits/data/page_audit_summary.json                (aggregates used by the generated reports)
          docs/audits/data/lesson_inventory/<SOURCE_ID>.json      (chapter/lesson -> page ranges, module, action)
          docs/audits/data/technology_index.json                  (technology -> pages per source)
Run     : .venv/bin/python scripts/audit/build_page_records.py [--check]
Source text is cached only under .work/ (git-ignored) and is never written to tracked files except for short matched
snippets (<=120 characters, credential-redacted) that evidence a flagged pattern.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "inventory"))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
from common import SOURCE_IDS, extract_pages, list_pdfs, read_outline  # noqa: E402
import forensics_lib as fx  # noqa: E402
from validate_catalog import load_yaml  # noqa: E402

DATA = ROOT / "docs" / "audits" / "data"
OUT = DATA / "page_records"
RESEARCH = ROOT / "docs" / "research"
AS_OF = "2026-10-14"
PART_SIZE = 500
MAJOR = re.compile(r"(?i)^\W*(?:module|volume|phase|part|chapter|project|pillar|stage|section)\b")
CODE_LINE = re.compile(r"^\s*(?:def |class |import |from \w[\w.]* import |for .+ in .+:|if .+:|elif |else:|try:|except|with .+:|return |print\(|public |private |@Test|@\w+|\w[\w.\[\]]*\s*=\s*\S|\w+\([^)]*\)\s*;?$|//|#\s)")
CURRENCY_ISSUES = {"OBSOLETE_API", "RETIRED_MODEL", "END_OF_LIFE_VERSION", "SUPERSEDED_PRODUCT", "SUPERSEDED_STANDARD", "OLD_BASELINE", "STANDARD_VERSION_UNVERIFIED"}
SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "NONE": 9}
SECURITY_PATTERNS = {k: v for k, v in fx.PY_SECURITY_PATTERNS.items() if k in {
    "eval_exec", "shell_true", "verify_false", "pickle_load", "yaml_unsafe", "os_system", "hardcoded_secret", "md5_sha1_use", "input_to_sql", "debug_true", "ssh_autoadd_hostkey", "weak_default_password"}}
SECURITY_SEVERITY = {"eval_exec": "P2", "verify_false": "P2", "hardcoded_secret": "P2", "weak_default_password": "P2", "ssh_autoadd_hostkey": "P2", "yaml_unsafe": "P2", "input_to_sql": "P2"}
CLAIM_SEVERITY = {"guarantee": "P2", "job_placement": "P2", "top_percent": "P3", "salary": "P3", "percent_stat": "P3", "expert_promise": "P3", "certification_claim": "P3"}


def clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&/:.,'()+\-]", "", t.replace("​", ""))).strip()[:120]


def snippet(text: str, m: re.Match, width: int = 110) -> str:
    s = max(0, m.start() - 25)
    return fx.redact_credentials(re.sub(r"\s+", " ", text[s: m.end() + width - 25]).strip())[:120]


def compress_ranges(pages: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for p in sorted(set(pages)):
        if out and p == out[-1][1] + 1:
            out[-1][1] = p
        else:
            out.append([p, p])
    return out


class Context:
    def __init__(self) -> None:
        self.inventory = json.loads((DATA / "source_inventory.json").read_text(encoding="utf-8"))
        self.pages_by_source = {d["source_id"]: d["pages"] for d in self.inventory["documents"]}
        self.path_by_source = {d["source_id"]: d["path"] for d in self.inventory["documents"]}
        reg = load_yaml(RESEARCH / "technology_registry.yaml")["technologies"]
        self.techs = []
        for t in reg:
            flags = 0 if t.get("detect_case_sensitive") else re.I
            self.techs.append({"id": t["id"], "rx": re.compile(t["detect"], flags), "domain": t["domain"], "docs": t.get("official_docs", "")})
        snap = json.loads((RESEARCH / "data" / f"registry_snapshot_{AS_OF}.json").read_text(encoding="utf-8"))
        self.baseline: dict[str, dict] = {}
        for r in snap["records"]:
            if r.get("status") == "OK" and r.get("current"):
                self.baseline.setdefault(r["tech_id"], {"version": r["current"].get("version"), "date": r["current"].get("date"), "url": r.get("url", ""), "kind": r["kind"]})
        probes = json.loads((RESEARCH / "data" / f"api_probes_{AS_OF}.json").read_text(encoding="utf-8"))
        self.probe_ids = {p["id"] for p in probes["probes"]}
        research = load_yaml(RESEARCH / "research_register.yaml")["register"]
        self.research = {r["id"]: r for r in research}
        rules = load_yaml(RESEARCH / "deprecation_rules.yaml")["rules"]
        self.rules = []
        for r in rules:
            self.rules.append({**r, "rxc": re.compile(r["rx"], re.I | re.M), "unlessc": re.compile(r["unless"], re.I | re.M) if r.get("unless") else None})
        mapping = load_yaml(ROOT / "catalog" / "source_mapping.yaml")["sources"]
        self.mapping = {}
        for sid, m in mapping.items():
            self.mapping[sid] = {"course": m["course"], "default": m["default"], "rules": [{**r, "rxc": re.compile(r["rx"], re.I)} for r in m["rules"]],
                                 "container_defaults": [{**r, "rxc": re.compile(r["rx"], re.I)} for r in m.get("container_defaults", [])]}
        catalog = load_yaml(ROOT / "catalog" / "courses.yaml")["courses"]
        self.module_info: dict[str, dict] = {}
        for c in catalog:
            for m in c["modules"]:
                self.module_info[m["id"]] = {"course": c["id"], "slug": c["slug"], "status": m["status"], "title": m["title"]}
        findings = load_yaml(DATA / "findings.yaml")["findings"]
        self.finding_pages: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
        for f in findings:
            for ev in f.get("evidence", []):
                pg = ev.get("page")
                nums: list[int] = []
                if isinstance(pg, int):
                    nums = [pg]
                elif isinstance(pg, str):
                    nums = [int(x) for x in re.findall(r"\d+", pg)][:2]
                    if len(nums) == 2 and nums[1] >= nums[0] and nums[1] - nums[0] < 40:
                        nums = list(range(nums[0], nums[1] + 1))
                for n in nums:
                    self.finding_pages[f["source_id"]][n].append(f["id"])
        self.finding_severity = {f["id"]: f["severity"] for f in findings}

    def evidence_url(self, ev_ids: list[str]) -> tuple[str, str]:
        for e in ev_ids:
            if e.startswith("R-") and e in self.research:
                r = self.research[e]
                return r["url"], str(r.get("verified_on", AS_OF))
        for e in ev_ids:
            if e.startswith("probe:"):
                return f"docs/research/data/api_probes_{AS_OF}.json#{e[6:]}", AS_OF
            if e.startswith("snapshot:"):
                b = self.baseline.get(e[9:])
                if b:
                    return b["url"], b.get("date") or AS_OF
        return "", ""


TOP = re.compile(r"(?i)^\W*(?:module|volume|phase)\b")


def heading_state(outline: list[dict], n_pages: int) -> tuple[list[dict], list[int]]:
    """Walk the bookmark outline once and produce, for every page, the heading context in force at its END.

    container = latest VOLUME/MODULE/PHASE heading; chapter = latest CHAPTER/PART/PROJECT/... heading; chapter_title = the first
    ordinary heading after it (Google-Docs exports put the descriptive title on the line after 'CHAPTER 3'); lesson/topic follow.
    """
    by_page: dict[int, list[dict]] = defaultdict(list)
    for e in outline:
        if e["page"]:
            by_page[e["page"]].append(e)
    container = chapter = chapter_title = lesson = topic = ""
    need_title = False
    out = []
    heads = []
    for p in range(1, n_pages + 1):
        for e in by_page.get(p, []):
            t = clean_title(e["title"])
            if len(t) < 2:
                continue
            if MAJOR.match(t) and e["level"] <= 2:
                if TOP.match(t):
                    container, chapter, chapter_title, lesson, topic = t, "", "", "", t
                else:
                    chapter, chapter_title, lesson, topic = t, "", "", t
                need_title = True
            elif e["level"] <= 2:
                if need_title:
                    chapter_title, need_title = t, False
                lesson, topic = t, t
            else:
                topic = t
        chap = " > ".join(x for x in (container, chapter, chapter_title) if x)[:170]
        out.append({"container": container, "chapter": chap, "lesson": lesson or chapter_title or chapter or container, "topic": topic or lesson or chapter_title or chapter})
        heads.append(len(by_page.get(p, [])))
    return out, heads


TECH_DEFECTS = {"OBSOLETE_API", "RETIRED_MODEL", "SUPERSEDED_PRODUCT", "SECURITY_ANTIPATTERN", "INCORRECT_CLAIM"}


def map_page(ctx: Context, sid: str, path_text: str, container: str = "") -> dict:
    m = ctx.mapping[sid]
    for r in m["rules"]:
        if r["rxc"].search(path_text):
            return {"module": r.get("module"), "action": r["action"], "basis": r["id"]}
    for r in m.get("container_defaults", []):
        if container and r["rxc"].search(container):
            return {"module": r.get("module"), "action": r["action"], "basis": r["id"]}
    d = m["default"]
    return {"module": d["module"], "action": d["action"], "basis": "default"}


def action_for(rule_action: str, issues: list[dict], techs_unverified: bool, dup: bool, stub: bool) -> tuple[str, str]:
    types = {i["issue_type"] for i in issues}
    if types & {"OBSOLETE_API", "RETIRED_MODEL", "SUPERSEDED_PRODUCT", "SECURITY_ANTIPATTERN", "INCORRECT_CLAIM"}:
        if rule_action == "REMOVE":
            return "REMOVE", "RULE"
        return "REPLACE", "RULE_AND_EVIDENCE"
    if rule_action == "REMOVE":
        return "REMOVE", "RULE"
    if "PERSONAL_DATA_RISK" in types:
        return "UPDATE", "PERSONAL_DATA_REVIEW"
    if stub:
        return "EXPAND", "LENGTH"
    if dup:
        return "MERGE", "REPETITION"
    if rule_action in ("MERGE", "REPLACE", "EXPAND"):
        return rule_action, "RULE"
    if types & CURRENCY_ISSUES or techs_unverified:
        return "UPDATE", "CURRENCY"
    if "UNSUPPORTED_CLAIM" in types:
        return "UPDATE", "CLAIM_TEXT_TO_REMOVE"
    return ("KEEP", "CANDIDATE") if rule_action in ("UPDATE", "KEEP") else (rule_action, "RULE")


def build_source(ctx: Context, pdf: Path) -> tuple[list[dict], dict]:
    sid = SOURCE_IDS[pdf.name]
    n_pages = ctx.pages_by_source[sid]
    pages = extract_pages(pdf)
    pages = pages + [""] * (n_pages - len(pages))
    outline = read_outline(pdf)
    states, heads = heading_state(outline, n_pages)
    fp = fx.line_fingerprints(pages, min_len=60)
    repeat_lines: dict[int, list[bool]] = defaultdict(list)
    for key, pgs in fp.items():
        uniq = sorted(set(pgs))
        flag = 2 <= len(uniq) <= 6
        for p in uniq:
            repeat_lines[p].append(flag)
    findings_pages = ctx.finding_pages.get(sid, {})
    recs: list[dict] = []
    for idx, text in enumerate(pages, start=1):
        st = states[idx - 1]
        words = len(text.split())
        techs: Counter = Counter()
        for t in ctx.techs:
            n = len(t["rx"].findall(text)) if text else 0
            if n:
                techs[t["id"]] += n
        tech_ids = [k for k, _ in techs.most_common(12)]
        issues: list[dict] = []
        matched_rules: list[str] = []
        first_claim = ""
        for r in ctx.rules:
            m = r["rxc"].search(text) if text else None
            if not m or (r["unlessc"] and r["unlessc"].search(text)):
                continue
            matched_rules.append(r["id"])
            ev = r.get("evidence", [])
            url, date = ctx.evidence_url(ev)
            issues.append({"issue_type": r["issue"], "severity": r["severity"], "rule": r["id"], "label": r["label"], "evidence": ev, "url": url, "date": date, "snippet": snippet(text, m)})
        for k, rxs in fx.CLAIM_PATTERNS.items():
            if k == "internal_framework_branding" or not text:
                continue
            m = re.search(rxs, text, re.I)
            if m:
                issues.append({"issue_type": "UNSUPPORTED_CLAIM", "severity": CLAIM_SEVERITY.get(k, "P3"), "rule": f"CLAIM:{k}", "label": k, "evidence": [], "url": "", "date": "", "snippet": snippet(text, m)})
        code_lines = [ln for ln in text.split("\n") if CODE_LINE.match(ln)] if text else []
        if len(code_lines) >= 3:
            for k, rxs in SECURITY_PATTERNS.items():
                m = re.search(rxs, text, re.M)
                if m:
                    issues.append({"issue_type": "SECURITY_ANTIPATTERN", "severity": SECURITY_SEVERITY.get(k, "P3"), "rule": f"SEC:{k}", "label": k, "evidence": [], "url": "", "date": "", "snippet": snippet(text, m)})
        pii = fx.scan_pii([text]) if text and "@" in text or "+" in text else None
        if pii and (pii["email"]["review_needed"] or pii["phone_with_country_code"]["total"]):
            confirmed = "F-FE-001" in findings_pages.get(idx, [])
            issues.append({"issue_type": "PERSONAL_DATA_RISK", "severity": "P0" if confirmed else "P2", "rule": "PII",
                           "label": "third-party personal data confirmed by finding F-FE-001 (values not stored)" if confirmed else "e-mail address or phone number needing review: may be an organisational contact (values not stored)",
                           "evidence": ["F-FE-001"] if confirmed else [], "url": "", "date": "", "snippet": ""})
        md = len(re.findall(r"\*\*[^*\n]+\*\*", text)) + len(re.findall(r"^\s*#{1,6}\s+\S", text, re.M)) if text else 0
        if md >= 3:
            issues.append({"issue_type": "MARKDOWN_LEAK", "severity": "P4", "rule": "MD", "label": "raw Markdown markers in the PDF text", "evidence": [], "url": "", "date": "", "snippet": ""})
        stub = bool(text) and words < 35
        rl = repeat_lines.get(idx, [])
        dup = len(rl) >= 3 and sum(rl) / len(rl) >= 0.5
        if stub:
            issues.append({"issue_type": "STUB_PAGE", "severity": "P4", "rule": "STUB", "label": "fewer than 35 words", "evidence": [], "url": "", "date": "", "snippet": ""})
        if dup:
            issues.append({"issue_type": "DUPLICATE_CONTENT", "severity": "P3", "rule": "DUP", "label": "long lines repeated on 2-6 pages", "evidence": [], "url": "", "date": "", "snippet": ""})
        if not text.strip():
            issues.append({"issue_type": "NO_TEXT_LAYER", "severity": "P2", "rule": "NOTEXT", "label": "no extractable text", "evidence": [], "url": "", "date": "", "snippet": ""})
        path_text = f"{st['chapter']} | {st['lesson']} | {st['topic']}".lower()
        mp = map_page(ctx, sid, path_text, st['container'].lower())
        if mp["action"] == "REMOVE" and any(i["issue_type"] in TECH_DEFECTS for i in issues):
            # A technical defect on a page whose heading says "remove" usually means the bookmark outline ended before the
            # page (code listings at the end of a volume inherit the last heading). Map by the page's own lesson/topic instead.
            alt = map_page(ctx, sid, f"{st['lesson']} | {st['topic']}".lower(), "")
            if alt["action"] != "REMOVE":
                mp = {**alt, "basis": f"{alt['basis']}+HEADING_OVERRIDE"}
        unverified = any(t not in ctx.baseline for t in tech_ids if not t.startswith(("social", "ransom")))
        action, action_basis = action_for(mp["action"], issues, unverified and bool(tech_ids), dup, stub and not any(i["issue_type"] == "NO_TEXT_LAYER" for i in issues))
        if not text.strip():
            action = mp["action"] if mp["action"] in ("REMOVE", "REPLACE") else "REPLACE"
        sev = min((i["severity"] for i in issues), key=lambda s: SEV_ORDER[s]) if issues else "NONE"
        cur_flag = any(i["issue_type"] in CURRENCY_ISSUES for i in issues)
        if cur_flag:
            currency = "CURRENCY_FLAGGED"
        elif tech_ids and all(t in ctx.baseline for t in tech_ids):
            currency = "BASELINE_AVAILABLE"
        elif tech_ids:
            currency = "UNVERIFIED_CURRENCY"
        else:
            currency = "NO_TECHNOLOGY_DETECTED"
        fids = sorted(set(findings_pages.get(idx, [])))
        if fids:
            # A page cited as evidence for a finding is never a "keep" candidate and never rated below the worst cited finding.
            worst = min((ctx.finding_severity[f] for f in fids), key=lambda s: SEV_ORDER[s])
            if sev == "NONE" or SEV_ORDER[worst] < SEV_ORDER[sev]:
                sev = worst
            if action == "KEEP":
                action, action_basis = "UPDATE", "FINDING_CITED"
        if not text.strip():
            status = "VISUAL_REVIEW_REQUIRED"
        elif fids:
            status = "MODEL_READ_FINDING_CITED"
        elif issues and any(i["issue_type"] not in ("STUB_PAGE", "MARKDOWN_LEAK") for i in issues):
            status = "MACHINE_FLAGGED_REVIEW_REQUIRED"
        elif words < 5:
            status = "MACHINE_SCANNED_NEAR_BLANK"
        else:
            status = "MACHINE_SCANNED_NO_FLAGS"
        top = sorted(issues, key=lambda i: SEV_ORDER[i["severity"]])
        url = date = ""
        for i in top:
            if i["url"]:
                url, date = i["url"], i["date"]
                break
        if not url and tech_ids:
            for t in tech_ids:
                if t in ctx.baseline:
                    url, date = ctx.baseline[t]["url"], ctx.baseline[t].get("date") or AS_OF
                    break
        module = mp["module"]
        mi = ctx.module_info.get(module) if module else None
        if module and not mi:
            raise SystemExit(f"{sid} p{idx}: mapping rule {mp['basis']} names unknown module {module}")
        dest_file = f"courses/{mi['slug']}/modules/{module}/" if mi else ""
        dest_state = ("BUILT" if mi["status"] != "PLANNED" else "PLANNED") if mi else "NOT_CARRIED_FORWARD"
        if module == "SOC-M04":
            dest_file = "courses/soc-analyst/lessons/m04-auth-detection/lesson.md"
        probe_ids = sorted({e[6:] for i in issues for e in i["evidence"] if e.startswith("probe:")})
        if probe_ids:
            test_ev = "EXECUTED: " + ", ".join(f"docs/research/data/api_probes_{AS_OF}.json#{p}" for p in probe_ids)
        elif dest_state == "BUILT":
            test_ev = "tests/pilot/ (SOC-M04 destination is built and tested; this page's content is not copied)"
        else:
            test_ev = "NONE: machine pattern scan only (scripts/audit/build_page_records.py); no code executed for this page"
        first_issue = top[0] if top else None
        claim = first_issue["snippet"] if first_issue and first_issue["snippet"] else ""
        recs.append({
            "source_pdf": pdf.name, "source_id": sid, "source_page": idx,
            "chapter": st["chapter"], "lesson": st["lesson"], "topic": st["topic"],
            "technology": tech_ids, "original_claim": claim,
            "evidence": {"words": words, "text_sha256_16": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else "", "extraction": "pdftotext-layout" if text.strip() else "none",
                         "headings_on_page": heads[idx - 1], "code_like_lines": len(code_lines), "rules": sorted(set(matched_rules))},
            "issue_type": sorted({i["issue_type"] for i in issues}) or ["NONE"], "severity": sev,
            "modernization_action": action, "action_basis": action_basis,
            "source_url": url, "source_date": date,
            "verification_status": status, "currency_status": currency,
            "destination_module": module or "", "destination_file": dest_file, "destination_state": dest_state, "mapping_basis": mp["basis"],
            "test_evidence": test_ev, "finding_ids": fids, "confidence": "CONFIRMED_BY_FINDING" if fids else "MACHINE",
        })
    return recs, {"sid": sid, "pdf": pdf.name, "pages": n_pages}


def write_outputs(ctx: Context, all_recs: dict[str, list[dict]], dry: bool) -> dict[str, str]:
    files: dict[str, str] = {}
    index = {"as_of": AS_OF, "part_size": PART_SIZE, "parts": []}
    for sid, recs in sorted(all_recs.items()):
        for n, start in enumerate(range(0, len(recs), PART_SIZE), start=1):
            chunk = recs[start: start + PART_SIZE]
            body = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n" for r in chunk)
            rel = f"docs/audits/data/page_records/{sid}.part{n:02d}.jsonl"
            files[rel] = body
            index["parts"].append({"file": rel, "source_id": sid, "first_page": chunk[0]["source_page"], "last_page": chunk[-1]["source_page"], "records": len(chunk), "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    files["docs/audits/data/page_records/INDEX.json"] = json.dumps(index, indent=1) + "\n"

    # lesson inventory
    for sid, recs in sorted(all_recs.items()):
        groups: dict[tuple[str, str], dict] = {}
        for r in recs:
            key = (r["chapter"], r["lesson"])
            g = groups.setdefault(key, {"chapter": r["chapter"], "lesson": r["lesson"], "pages": [], "modules": Counter(), "actions": Counter(), "issues": Counter()})
            g["pages"].append(r["source_page"])
            g["modules"][r["destination_module"] or "-"] += 1
            g["actions"][r["modernization_action"]] += 1
            for it in r["issue_type"]:
                if it != "NONE":
                    g["issues"][it] += 1
        rows = []
        for g in groups.values():
            rows.append({"chapter": g["chapter"], "lesson": g["lesson"], "pages": compress_ranges(g["pages"]), "module": g["modules"].most_common(1)[0][0], "actions": dict(g["actions"].most_common()), "issues": dict(g["issues"].most_common())})
        rows.sort(key=lambda x: x["pages"][0][0])
        files[f"docs/audits/data/lesson_inventory/{sid}.json"] = json.dumps({"source_id": sid, "lessons": rows}, ensure_ascii=False, separators=(",", ":")) + "\n"

    # technology index
    tix: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for sid, recs in all_recs.items():
        for r in recs:
            for t in r["technology"]:
                tix[t][sid].append(r["source_page"])
    tech_out = {t: {sid: compress_ranges(p) for sid, p in sorted(d.items())} for t, d in sorted(tix.items())}
    files["docs/audits/data/technology_index.json"] = json.dumps({"as_of": AS_OF, "technologies": tech_out}, separators=(",", ":")) + "\n"

    # summary
    summary: dict = {"as_of": AS_OF, "sources": {}, "totals": {}}
    tot = Counter()
    for sid, recs in sorted(all_recs.items()):
        c = {"pages": len(recs), "status": Counter(r["verification_status"] for r in recs), "action": Counter(r["modernization_action"] for r in recs),
             "severity": Counter(r["severity"] for r in recs), "currency": Counter(r["currency_status"] for r in recs),
             "issue_pages": Counter(it for r in recs for it in r["issue_type"] if it != "NONE"),
             "mapping": Counter("source_default" if r["mapping_basis"] == "default" else ("container_default" if r["mapping_basis"].startswith("C-") else "keyword_rule") for r in recs),
             "mapping_no_destination": sum(1 for r in recs if not r["destination_module"]),
             "destination": Counter(r["destination_module"] or "-" for r in recs),
             "rule_hits": Counter(x for r in recs for x in r["evidence"]["rules"]),
             "model_read_pages": sum(1 for r in recs if r["verification_status"] == "MODEL_READ_FINDING_CITED"),
             "top_technologies": Counter(t for r in recs for t in r["technology"]).most_common(15)}
        summary["sources"][sid] = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in c.items()}
        tot["pages"] += len(recs)
        for k in ("status", "action", "severity", "currency"):
            for kk, vv in c[k].items():
                tot[f"{k}:{kk}"] += vv
    summary["totals"] = dict(tot)
    files["docs/audits/data/page_audit_summary.json"] = json.dumps(summary, indent=1, sort_keys=True) + "\n"
    if not dry:
        for rel, body in files.items():
            p = ROOT / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if committed outputs differ from a fresh build")
    ap.add_argument("--only", help="comma-separated source ids (debugging; do not commit partial outputs)")
    a = ap.parse_args()
    ctx = Context()
    only = set(a.only.split(",")) if a.only else None
    all_recs: dict[str, list[dict]] = {}
    for pdf in list_pdfs():
        sid = SOURCE_IDS[pdf.name]
        if only and sid not in only:
            continue
        recs, meta = build_source(ctx, pdf)
        all_recs[sid] = recs
        c = Counter(r["verification_status"] for r in recs)
        dflt = sum(1 for r in recs if r["mapping_basis"] == "default")
        print(f"{sid:22} pages={meta['pages']:5} source-default-mapped={dflt:5}  " + "  ".join(f"{k[:14]}={v}" for k, v in sorted(c.items())))
    if only:
        write_outputs(ctx, all_recs, dry=True)
        return 0
    files = write_outputs(ctx, all_recs, dry=a.check)
    if a.check:
        stale = [rel for rel, body in files.items() if not (ROOT / rel).exists() or (ROOT / rel).read_text(encoding="utf-8") != body]
        if stale:
            print("page records out of date:\n  - " + "\n  - ".join(stale[:10]))
            return 1
        print(f"page records up to date ({len(files)} files)")
        return 0
    total = sum(len(v) for v in all_recs.values())
    print(f"wrote {len(files)} files; {total} page records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
