"""Shared loaders and reference resolvers for the October 2026 modernization renderers.

Deterministic, offline, read-only. Imported by render_audit_docs.py, render_research_docs.py and the tests.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "audits" / "data"
RESEARCH = ROOT / "docs" / "research"
CUTOFF = "2026-10-14"
REFRESH_TARGET = "2026-10-24"

SOURCE_TITLES = {
    "SRC-AI-BUNDLE": "Complete AI Training Bundle 2026",
    "SRC-PY-HANDBOOK": "CyberDudeBivash Python Engineering Handbook",
    "SRC-JAVA-AUTOTEST": "Java Automation Test Engineer Real-Time Job Training",
    "SRC-OSINT-STARTER": "OSINT Starter Bundle (FULL)",
    "SRC-PY-AUTOMATION": "Python Automation Training",
    "SRC-GCP-DATAENG": "GCP Data Engineer Training",
    "SRC-FRONTEND-ONBOARD": "Internal Frontend Developer Onboarding Playbook",
    "SRC-MEGA-P1": "Official Mega Course 2026, Part 1",
    "SRC-MEGA-P2": "Official Mega Course 2026, Part 2",
    "SRC-SOC-PLAYBOOK": "SOC Analyst Survival Playbook (2026 Edition)",
}


def load_yaml(rel: str):
    class L(yaml.SafeLoader):
        pass

    L.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))
    with (ROOT / rel).open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=L)  # noqa: S506


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def md(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def ranges(pages: list[int], limit: int | None = None) -> str:
    """Compress sorted page numbers into 'a-b, c' (optionally truncated with a count)."""
    pages = sorted(set(pages))
    out, i = [], 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    if limit and len(out) > limit:
        return ", ".join(out[:limit]) + f", ... (+{len(out) - limit} more ranges)"
    return ", ".join(out)


def counts_str(counter: dict, order: list[str] | None = None) -> str:
    keys = order or sorted(counter, key=lambda k: (-counter[k], k))
    return ", ".join(f"{k} {counter[k]:,}" for k in keys if counter.get(k))


class Data:
    """All inputs, loaded once."""

    def __init__(self) -> None:
        self.catalog = load_yaml("catalog/courses.yaml")
        self.courses = {c["id"]: c for c in self.catalog["courses"]}
        self.module_course: dict[str, str] = {}
        self.module_title: dict[str, str] = {}
        for c in self.catalog["courses"]:
            for m in c["modules"]:
                self.module_course[m["id"]] = c["id"]
                self.module_title[m["id"]] = m["title"]
        self.findings = {f["id"]: f for f in load_yaml("docs/audits/data/findings.yaml")["findings"]}
        self.register = {r["id"]: r for r in load_yaml("docs/research/research_register.yaml")["register"]}
        probes = load_json(f"docs/research/data/api_probes_{CUTOFF}.json")
        self.probe_meta = {k: v for k, v in probes.items() if k != "probes"}
        self.probes = {p["id"]: p for p in probes["probes"]}
        snap = load_json(f"docs/research/data/registry_snapshot_{CUTOFF}.json")
        self.snapshot_meta = {k: v for k, v in snap.items() if k != "records"}
        self.snapshot_all: dict[str, list[dict]] = defaultdict(list)
        for r in snap["records"]:
            self.snapshot_all[r["tech_id"]].append(r)
        # primary record per technology: first one that produced a version
        self.snapshot = {t: next((r for r in rs if r.get("current")), rs[0]) for t, rs in self.snapshot_all.items()}
        self.rules = load_yaml("docs/research/deprecation_rules.yaml")["rules"]
        self.registry = {e["id"]: e for e in load_yaml("docs/research/technology_registry.yaml")["technologies"]}
        self.changes = load_yaml("docs/audits/data/modernization_changes.yaml")["changes"]
        self.devs = load_yaml("docs/research/new_developments.yaml")["developments"]
        self.index = load_json("docs/audits/data/page_records/INDEX.json")
        self.summary = load_json("docs/audits/data/page_audit_summary.json")
        self.tech_index = load_json("docs/audits/data/technology_index.json")["technologies"]
        self._records: dict[str, list[dict]] | None = None

    # ---- page records (8 MB; loaded lazily)
    @property
    def records(self) -> dict[str, list[dict]]:
        if self._records is None:
            rec: dict[str, list[dict]] = defaultdict(list)
            for part in self.index["parts"]:
                with (ROOT / part["file"]).open(encoding="utf-8") as fh:
                    for line in fh:
                        r = json.loads(line)
                        rec[r["source_id"]].append(r)
            for v in rec.values():
                v.sort(key=lambda r: r["source_page"])
            self._records = dict(rec)
        return self._records

    def course_of_source(self, sid: str) -> str | None:
        for c in self.catalog["courses"]:
            if sid in (c.get("source_ids") or []):
                return c["id"]
        return None

    # ---- reference resolution
    def resolve(self, ref: str) -> dict:
        """Return {label, detail, url, ok} for an evidence reference."""
        if ref.startswith("R-"):
            r = self.register.get(ref)
            if not r:
                return {"label": ref, "detail": "UNRESOLVED", "url": "", "ok": False}
            return {"label": ref, "detail": f"{r['title']} ({r['publisher']}; {r['method']}; verified {r['verified_on']})",
                    "url": r.get("primary_url") or r.get("url", ""), "ok": True}
        if ref.startswith("F-"):
            f = self.findings.get(ref)
            if not f:
                return {"label": ref, "detail": "UNRESOLVED", "url": "", "ok": False}
            return {"label": ref, "detail": f"{f['severity']} {f['title']}", "url": "", "ok": True}
        if ref.startswith("probe:"):
            p = self.probes.get(ref[6:])
            if not p:
                return {"label": ref, "detail": "UNRESOLVED", "url": "", "ok": False}
            return {"label": ref, "detail": f"executed probe, status {p['status']}, {p['executed_utc']}, {p.get('python', '')}",
                    "url": "", "ok": True}
        if ref.startswith("snapshot:"):
            s = self.snapshot.get(ref[9:])
            if not s:
                return {"label": ref, "detail": "UNRESOLVED", "url": "", "ok": False}
            cur = s.get("current") or {}
            return {"label": ref, "detail": f"registry snapshot {s.get('kind')}: {cur.get('version', 'n/a')} ({cur.get('date', 'n/a')}), retrieved {s['retrieved_utc']}",
                    "url": "", "ok": True}
        return {"label": ref, "detail": "UNRESOLVED", "url": "", "ok": False}


def source_stats(records: list[dict]) -> dict:
    n = len(records)
    c = lambda key: Counter(r[key] for r in records)  # noqa: E731
    issues = Counter(i for r in records for i in r["issue_type"] if i != "NONE")
    return {
        "pages": n,
        "severity": c("severity"),
        "action": c("modernization_action"),
        "status": c("verification_status"),
        "currency": c("currency_status"),
        "issues": issues,
        "mapping": c("mapping_basis"),
        "module": c("destination_module"),
        "findings": sorted({f for r in records for f in r["finding_ids"]}),
    }


def tech_usage(d: "Data") -> dict[str, dict]:
    """Per technology: pages, courses and modules where the legacy sources mention it (from the page records)."""
    out: dict[str, dict] = {}
    for sid, recs in d.records.items():
        for r in recs:
            for t in r["technology"]:
                u = out.setdefault(t, {"pages": 0, "sources": Counter(), "modules": Counter(), "courses": Counter()})
                u["pages"] += 1
                u["sources"][sid] += 1
                if r["destination_module"]:
                    u["modules"][r["destination_module"]] += 1
                    u["courses"][d.module_course.get(r["destination_module"], "?")] += 1
    return out
