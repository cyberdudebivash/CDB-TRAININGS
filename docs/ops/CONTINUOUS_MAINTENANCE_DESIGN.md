# Continuous Maintenance Design

> **Status: DESIGN ONLY.** No scheduler, workflow trigger, monitor or alert exists in this repository or its environment. Nothing here has been enabled, and no claim of automated monitoring is made. Enabling any part of it needs the owner's explicit approval (cost and permissions: see section 5).

## 1. Goal

Keep every course's technical claims current without relying on memory: detect that a fact the courses depend on changed, show exactly which lesson, lab or page it affects, and make the update a reviewed change instead of a surprise.

## 2. What already exists (mechanisms, run by a person today)

| Mechanism | Command | What it detects |
|---|---|---|
| Registry snapshot | `python scripts/research/fetch_registry_versions.py --cutoff <date>` | New releases and lifecycle changes for 334 registered technologies (GitHub-only entries excluded) |
| Snapshot diff | `python scripts/research/diff_snapshots.py <old> <new>` | Which technologies' current versions changed |
| Executed probes | `python scripts/research/api_probes.py --cutoff <date> --work-dir <outside the repo>` | Whether a pattern the sources teach still works on the current release |
| Deprecation rules | `docs/research/deprecation_rules.yaml` applied by `build_page_records.py` | Which source pages teach a removed, superseded or end-of-life pattern |
| Lab matrix | `python scripts/validation/run_lab_matrix.py` | Whether built labs still pass on every supported interpreter |
| Generated-document checks | `python scripts/validation/run_qa.py` | Documents that drifted from their data |

## 3. Proposed cadence

| Trigger | Action | Owner |
|---|---|---|
| Monthly (first working day) | Registry snapshot, diff, probes, lab matrix; open a pull request with the diff and the regenerated documents | Maintainer |
| Python, Node.js, JDK, Kubernetes minor release or end-of-life date (dates are in the snapshot) | Re-run the matrix on the new interpreter or toolchain; update lifecycle statements | Maintainer |
| Vendor deprecation notices (OpenAI, Anthropic, Google, Microsoft) | Re-read the notice pages recorded in the register; update model-lifecycle and service-name content | Maintainer |
| Standards releases (OWASP, ATT&CK, NIST, CVSS) | Re-read the page, add a register entry, update cited versions | Maintainer |
| Quarterly | Review `NEEDS_VERIFICATION`, `SECONDARY_ONLY` and `MACHINE_ONLY` change records and the open items list in the Stage B checklist | Maintainer plus SME |
| Before any sale or edition build | Full refresh; readiness report regenerated; owner approval recorded | Owner |

## 4. Proposed automation (not enabled)

A scheduled GitHub Actions workflow could run the monthly row of section 3 on a fixed date, upload the diff as a pull request, and fail visibly when a probe or lab regresses. A sketch of what it would do (not committed as a workflow file):

1. Set up Python 3.13, install `requirements.txt` and `courses/python-engineering/labs/requirements.txt`.
2. Run the snapshot fetch with today's cutoff and the diff against the latest committed snapshot.
3. Run the probes in a temporary directory and the lab matrix (the `uv` interpreters download from the network).
4. Run `scripts/validation/run_qa.py --skip-build`.
5. Open a pull request containing the new data files and regenerated documents, labelled for human review; never merge automatically.

## 5. Cost, permissions and risk

- A public repository's standard GitHub-hosted runners have no per-minute charge, but the account's policy can change and a private repository would be billed; the existing `.github/workflows/validate.yml` is therefore manual-only. The owner must decide before a schedule is added (D7: any paid-resource budget is currently zero).
- The scripts need outbound HTTPS to package registries and vendor pages and no credentials. GitHub release data requires a token with access to public repositories and stays off unless the owner enables it.
- Automation cannot verify a *page's meaning*: a changed deprecation notice still needs a person to read it. The design deliberately stops at "open a reviewed pull request".

## 6. What to monitor, concretely

The register entries whose method is `OFFICIAL_PAGE_SUMMARY` name the exact pages; the Stage B checklist lists dated facts; the snapshot lists lifecycle end dates. These three files are the monitoring configuration. Adding a technology means adding it to `docs/research/technology_registry.yaml` with a detection pattern and a version source.
