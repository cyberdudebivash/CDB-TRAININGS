#!/usr/bin/env python3
"""Reproducible version/lifecycle snapshot for every technology in docs/research/technology_registry.yaml.

Sources (all free, unauthenticated, read-only):
  pypi         https://pypi.org/pypi/<name>/json
  npm          https://registry.npmjs.org/<name>
  maven        https://repo.maven.apache.org/maven2/<group>/<artifact>/maven-metadata.xml  (Maven Central; POM Last-Modified = upload date)
  endoflife    https://endoflife.date/api/<product>.json   (aggregates vendor lifecycle pages; cross-check official docs for decisions)
  github       https://api.github.com/repos/<repo>/releases (and /tags when a project publishes no releases); OFF by default, enable with --allow-github
               on a machine whose network policy permits it. A session scoped to one repository (as in the Claude Code cloud environment) must not use it.

Date integrity: only releases published on or before --cutoff are considered "current".  Newer
releases are recorded separately as `after_cutoff` so a later refresh (for example 2026-10-24) can be
diffed against this one without back-dating anything.  Every record carries the UTC retrieval time.

This script is run by a person (or a scheduler the owner configures); nothing in the repository runs it automatically.

Usage:
  python scripts/research/fetch_registry_versions.py --cutoff 2026-10-14
  python scripts/research/fetch_registry_versions.py --cutoff 2026-10-24 --only python,react
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "research" / "technology_registry.yaml"
OUT_DIR = ROOT / "docs" / "research" / "data"
UA = "cdb-trainings-research/1.0 (+https://github.com/cyberdudebivash/CDB-TRAININGS; read-only version audit)"
PRE = re.compile(r"(?i)(alpha|beta|rc|dev|preview|snapshot|milestone|canary|nightly|next|experimental|\.m\d+$|-m\d+$|\bpre\b|a\d+$|b\d+$)")


def http_json(url: str, timeout: int = 40, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https hosts from the registry
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 429):  # not transient: fail fast so rate limits and scope blocks are visible
                raise
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def vkey(v: str) -> tuple:
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts[:6]) or (0,)


def is_stable(v: str) -> bool:
    return not PRE.search(v)


def day(iso: str | None) -> str | None:
    return iso[:10] if iso else None


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------------------- adapters
def pick(releases: list[tuple[str, str]], cutoff: str) -> tuple[dict, list[dict]]:
    """releases: [(version, YYYY-MM-DD)] stable only. Returns (current, after_cutoff list)."""
    before = [(v, d) for v, d in releases if d <= cutoff]
    after = [(v, d) for v, d in releases if d > cutoff]
    cur = max(before, key=lambda x: vkey(x[0])) if before else None
    return ({"version": cur[0], "date": cur[1]} if cur else {}), [{"version": v, "date": d} for v, d in sorted(after, key=lambda x: x[1])][-5:]


def fetch_pypi(spec: dict, cutoff: str) -> dict:
    name = spec["name"]
    data = http_json(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json")
    stable, pre = [], []
    for v, files in data["releases"].items():
        files = [f for f in files if not f.get("yanked")]
        if not files:
            continue
        d = min(day(f["upload_time_iso_8601"]) for f in files)
        (stable if is_stable(v) else pre).append((v, d))
    cur, after = pick(stable, cutoff)
    out = {"package": name, "current": cur, "after_cutoff": after, "url": f"https://pypi.org/project/{name}/"}
    if cur:
        info = http_json(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/{cur['version']}/json")["info"]
        out["requires_python"] = info.get("requires_python")
        out["summary"] = (info.get("summary") or "")[:160]
        out["license"] = (info.get("license_expression") or info.get("license") or "")[:80]
        if info.get("yanked"):
            out["yanked"] = True
    newer_pre = [{"version": v, "date": d} for v, d in pre if d <= cutoff and cur and d > cur["date"]]
    if newer_pre:
        out["newer_prerelease"] = sorted(newer_pre, key=lambda x: x["date"])[-1]
    return out


def fetch_npm(spec: dict, cutoff: str) -> dict:
    name = spec["name"]
    data = http_json(f"https://registry.npmjs.org/{name.replace('/', '%2F')}", timeout=90)
    times = data.get("time", {})
    stable = [(v, day(t)) for v, t in times.items() if v not in ("created", "modified") and is_stable(v)]
    cur, after = pick(stable, cutoff)
    out = {"package": name, "current": cur, "after_cutoff": after, "dist_tag_latest": data.get("dist-tags", {}).get("latest"), "url": f"https://www.npmjs.com/package/{name}"}
    if cur:
        meta = data.get("versions", {}).get(cur["version"], {})
        out["engines"] = meta.get("engines")
        if meta.get("deprecated"):
            out["deprecated"] = str(meta["deprecated"])[:300]
        out["license"] = str(meta.get("license", ""))[:60]
    return out


def http_text(url: str, timeout: int = 40, method: str = "GET", patience: int = 4):
    """Plain-text / header fetch that waits out Maven Central's per-IP rate limit (HTTP 429) politely."""
    for attempt in range(patience):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https hosts
                return r.read().decode("utf-8", "replace") if method == "GET" else dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == patience - 1:
                raise
            time.sleep(20 * (attempt + 1))


def fetch_maven(spec: dict, cutoff: str) -> dict:
    """Maven Central via maven-metadata.xml (the search API returns incomplete version lists) plus the POM's Last-Modified header for dates."""
    g, a = spec["coord"].split(":")
    base = f"https://repo.maven.apache.org/maven2/{g.replace('.', '/')}/{a}"
    xml = http_text(f"{base}/maven-metadata.xml")
    versions = re.findall(r"<version>([^<]+)</version>", xml)
    stable = sorted((v for v in versions if is_stable(v)), key=vkey, reverse=True)
    cur, after, dated = {}, [], 0
    for v in stable[:12]:
        time.sleep(0.8)
        hdr = http_text(f"{base}/{v}/{a}-{v}.pom", method="HEAD")
        lm = hdr.get("Last-Modified") or hdr.get("last-modified")
        if not lm:
            continue
        d = dt.datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")
        dated += 1
        if d <= cutoff:
            cur = {"version": v, "date": d}
            break
        after.append({"version": v, "date": d})
        time.sleep(1.0)
    return {"coordinate": spec["coord"], "current": cur, "after_cutoff": after[-5:], "versions_listed": len(versions), "metadata_latest": (re.search(r"<latest>([^<]+)</latest>", xml) or [None, None])[1],
            "date_basis": "Last-Modified of the .pom on Maven Central (upload time, not necessarily the project's announcement date)", "url": f"https://central.sonatype.com/artifact/{g}/{a}"}


def fetch_eol(spec: dict, cutoff: str) -> dict:
    prod = spec["product"]
    cycles = http_json(f"https://endoflife.date/api/{prod}.json")
    supported, ended = [], []
    for c in cycles:
        eol = c.get("eol")
        row = {"cycle": str(c.get("cycle")), "latest": c.get("latest"), "latest_release_date": c.get("latestReleaseDate"), "release_date": c.get("releaseDate"), "eol": eol, "lts": c.get("lts"), "support": c.get("support")}
        if c.get("releaseDate") and c["releaseDate"] > cutoff:
            continue
        alive = (eol is False) or (isinstance(eol, str) and eol > cutoff)
        (supported if alive else ended).append(row)
    cur = supported[0] if supported else (ended[0] if ended else {})
    return {"product": prod, "current": {"version": cur.get("latest"), "date": cur.get("latest_release_date")}, "supported_cycles": supported[:8], "recently_ended_cycles": ended[:4], "url": f"https://endoflife.date/{prod}"}


def fetch_github(spec: dict, cutoff: str) -> dict:
    repo = spec["repo"]
    rels = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=40")
    stable = [(r["tag_name"], day(r["published_at"])) for r in rels if not r.get("draft") and not r.get("prerelease") and r.get("published_at") and is_stable(r["tag_name"])]
    source = "releases"
    if not stable:
        tags = http_json(f"https://api.github.com/repos/{repo}/tags?per_page=30")
        stable = []
        for t in tags:
            if not is_stable(t["name"]):
                continue
            commit = http_json(t["commit"]["url"])
            stable.append((t["name"], day(commit["commit"]["committer"]["date"])))
        source = "tags"
    cur, after = pick(stable, cutoff)
    # repositories tag by date or by version; prefer chronological for the "current" pick
    if stable:
        before = [(v, d) for v, d in stable if d <= cutoff]
        if before:
            v, d = max(before, key=lambda x: (x[1], vkey(x[0])))
            cur = {"version": v, "date": d}
    return {"repo": repo, "source": source, "current": cur, "after_cutoff": after, "url": f"https://github.com/{repo}/releases"}


ADAPTERS = {"pypi": fetch_pypi, "npm": fetch_npm, "maven": fetch_maven, "endoflife": fetch_eol, "github": fetch_github}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cutoff", default="2026-10-14", help="only releases on or before this UTC date are 'current'")
    ap.add_argument("--only", help="comma-separated registry ids")
    ap.add_argument("--out", help="output JSON (default docs/research/data/registry_snapshot_<cutoff>.json)")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--merge", action="store_true", help="with --only: replace just those technologies' records inside the existing snapshot")
    ap.add_argument("--allow-github", action="store_true", help="query api.github.com (off by default: restricted sessions only allow their own repositories)")
    a = ap.parse_args()
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["technologies"]
    only = set(a.only.split(",")) if a.only else None
    started = utcnow()
    results, errors = [], []
    for tech in reg:
        if only and tech["id"] not in only:
            continue
        for spec in tech.get("fetch", []):
            rec = {"tech_id": tech["id"], "kind": spec["kind"], "spec": {k: v for k, v in spec.items() if k != "kind"}, "retrieved_utc": utcnow()}
            if spec["kind"] == "github" and not a.allow_github:
                rec["status"] = "SKIPPED_GITHUB_NOT_ENABLED"
                results.append(rec)
                continue
            try:
                rec.update(ADAPTERS[spec["kind"]](spec, a.cutoff))
                rec["status"] = "OK" if rec.get("current") else "NO_RELEASE_BEFORE_CUTOFF"
            except urllib.error.HTTPError as e:
                rec["status"] = "NOT_FOUND" if e.code == 404 else f"HTTP_{e.code}"
                errors.append((tech["id"], spec, rec["status"]))
            except Exception as e:  # noqa: BLE001
                rec["status"] = "ERROR"
                rec["error"] = str(e)[:300]
                errors.append((tech["id"], spec, rec["status"]))
            results.append(rec)
            time.sleep(a.sleep)
    out = Path(a.out) if a.out else OUT_DIR / f"registry_snapshot_{a.cutoff}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.merge and out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        keep = [r for r in old["records"] if r["tech_id"] not in {x["tech_id"] for x in results}]
        results = keep + results
        started = old.get("started_utc", started)
    doc = {"cutoff_date": a.cutoff, "started_utc": started, "finished_utc": utcnow(), "script": "scripts/research/fetch_registry_versions.py", "records": results}
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"{ok}/{len(results)} lookups OK -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    for tid, spec, st in errors:
        print(f"  {st:20} {tid} {spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
