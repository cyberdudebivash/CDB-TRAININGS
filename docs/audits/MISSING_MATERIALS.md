# Missing Materials and Owner Inputs

## 1. Reconciliation of the intended corpus

All **10 of 10** documents named in the owner's screenshot are present in the repository, readable, unencrypted and not
LFS pointers (`SOURCE_INVENTORY.md`). **No source is `BLOCKED_SOURCE_PENDING` at document level.**

Presence of a PDF is not completeness of the course it names. The sections below list material that the PDFs *describe or
depend on* but that does not exist in the repository. Each item blocks only the work that needs it.

## 2. Components described by the sources but not present

| # | Missing item | Described at | Needed for | Status |
|---|---|---|---|---|
| 1 | Preconfigured OSINT virtual machine (VirtualBox/VMware) | OSINT pp. 7, 13-14 | OSINT labs as described | BLOCKED_SOURCE_PENDING |
| 2 | "OSINT Playbook (PDF, 300+ Pages)" | OSINT p. 8 | OSINT curriculum source | BLOCKED_SOURCE_PENDING |
| 3 | 10+ MP4 video tutorials | OSINT p. 9 | OSINT delivery | BLOCKED_SOURCE_PENDING |
| 4 | OSINT hands-on labs and datasets | OSINT p. 9 | OSINT labs | BLOCKED_SOURCE_PENDING (replace with synthetic labs) |
| 5 | Splunk / ELK dashboards; daily CVE and IOC feeds; Python launcher; reporting templates; Dark-Web guide | OSINT pp. 10-13, 16 | OSINT product claims | BLOCKED_SOURCE_PENDING (do not advertise) |
| 6 | "CyberDudeBivash Attack Surface Template (provided later)" | Mega P1 pp. 15, 1246 | Mega lab 1 | BLOCKED_SOURCE_PENDING |
| 7 | Companion repository for "Complete GitHub Automation Framework (Repo + Code)" | Automation pp. 200, 502 | Automation labs | BLOCKED_SOURCE_PENDING (rebuild; see PA track) |
| 8 | Seven lab repositories `github.com/YOUR_ORG/01-...07-...` | AI Bundle pp. 351-430 | AI labs | PLACEHOLDER URLs (learner-created); rebuild as tested repos |
| 9 | Repository layout referenced by CI examples (`02-bigquery/raw-to-curated/incremental_merge.sql`, etc.) | GCP pp. 179-182 | GCP labs | BLOCKED_SOURCE_PENDING |
| 10 | Companion code for the Java framework | Java (none referenced) | Java capstone | NOT_REFERENCED; build new |
| 11 | Ecosystem frontend stack and repositories | Frontend pp. 1, 17 | Frontend alignment | NEEDS_OWNER_INPUT (outside repository scope) |
| 12 | Ecosystem pages linked from the SOC playbook (`cyberdudebivash.github.io/...`) | SOC pp. 40-42 | Cross-links only | NOT_VERIFIED (not fetched) |
| 13 | Instructor material, answer keys, rubrics, solutions for **any** course | - | Assessment integrity | DID_NOT_EXIST; built only for the pilot (kept private, see below) |

## 3. Decisions and inputs needed from the owner

| # | Decision | Why it blocks | Urgency |
|---|---|---|---|
| D1 | **Third-party personal data in the public Frontend PDF (pp. 357, 360).** Confirm consent or remove the file/pages; if removal is chosen, history purging is a repository-owner action. | Privacy/legal exposure is live now because the repository is public. | **Immediate** |
| D2 | Origin of the "INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK": whose internal practices does it describe, and may they be published/sold? | Confidentiality and IP; accuracy of "internal" claims. | High |
| D3 | OSINT bundle: legal review of redistributing GPL tools under a proprietary licence (and Maltego CE / SpiderFoot HX terms). | Blocks any VM or bundle distribution. | High |
| D4 | Which entity owns the copyright and may license the training content (CyberDudeBivash Pvt. Ltd. vs individual authors)? Add a LICENSE. | The repository has no licence; default is all rights reserved but the intent for a public repo is unclear. | High |
| D5 | Qualified subject-matter reviewers (name and credentials) per course. | No course can be SME_REVIEWED without them. | Medium |
| D6 | Target Academy platform constraints (LMS/hosting), payment and delivery stack. | Needed before any fulfilment work (see `docs/commercial/COMMERCIAL_READINESS.md` section 4). | Medium |
| D7 | Approved budget for any paid cloud/API usage (current policy: none). | GCP and AI labs default to local-first, free alternatives. | Low |
| D8 | Approve using a private repository for instructor packs (answer keys, solutions). | Repository is public. | Medium |

## 4. Instructor pack for the pilot (kept out of the public repository)

The SOC pilot unit has an instructor pack (quiz answer key, reference solution for the independent lab, grading notes).
Because this repository is public it is **not committed**: `courses/*/instructor/` is git-ignored except its README.
The pack was delivered to the owner separately at the end of the session and must be placed in a private repository
(suggested: `cdb-trainings-instructor`). Tests that need it skip with an explicit `SKIPPED_PRIVATE_MATERIALS` message.
Until the owner confirms receipt, the instructor artefacts are ephemeral.
