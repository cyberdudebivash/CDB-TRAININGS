# P0 — Public source PDF quarantine proposal

**Incident:** INC-001 / DEF-001, with related confidentiality issue INC-002.  
**Classification:** proposed containment only; owner decision and historical remediation remain open.  
**Date:** 2026-10-16.

## Confirmed exposure

The repository is public. Its original Frontend onboarding PDF, as documented in the incident register, contains third-party personal contact information on two pages. This PR deliberately does **not** reproduce that information, render the affected pages or add an alternative copy.

Existing `check_privacy.py` only searches text files and deliberately excludes source PDFs. A passing text-only scan therefore did not contradict the original PDF exposure.

## Containment change in this branch

- Remove the affected original PDF from the current Git tree. No replacement is published.
- Add `check_public_source_exposure.py`: fail closed if the original filename, a casefold-equivalent variant, or the exact known Git blob is staged for distribution again; inspect untracked nonignored files too.
- Add automated negative controls with synthetic content; never include third-party identities.
- Add a manual validation-workflow step. No automatic workflow triggers, paid runners, or deployment are introduced.

## Optional protected-source audit reproduction

The historical audit must not silently lose its affected source. When and only when the owner has the legal right and authorization to retain the original, place an approved copy **outside the Git checkout** in a protected directory with a restrictive access policy. Do not commit it, upload it as a GitHub artifact, or include it in CI logs.

The shared `scripts/inventory/common.py::list_pdfs` now accepts `CDB_PRIVATE_SOURCE_DIR` as an *explicit* offline input. It combines the nine remaining public PDFs with exactly the quarantined source from that external directory. The directory must not be a symlink or reside inside this repository, and the source file cannot be a symlink. It does not accept private files for other courses, nor does it create or manage private storage.

For an authorized operator in a protected POSIX environment:

```sh
export CDB_PRIVATE_SOURCE_DIR=/secure/external/source-directory
python scripts/validation/check_public_source_exposure.py
python scripts/audit/build_page_records.py --check
```

The private directory must contain the original file under its recorded filename. The example path is an illustrative placeholder; no such protected storage is asserted to exist. For PowerShell, set `$env:CDB_PRIVATE_SOURCE_DIR` to the authorized external folder and execute the corresponding Python commands.

The public-source guard should pass only when the known source is absent from the current distributable Git index. The page-audit check must fail when the external input is unavailable or differs from the recorded pages. Re-running `build_inventory.py` changes `tracked_in_git` to false for that original, so generated inventory evidence may need an explicit, reviewed source-location provenance update rather than blindly overwriting historical records.

```text
python -m pytest -q tests/test_public_source_quarantine.py tests/test_private_source_intake.py
```

These tests use fabricated bytes only; they do not inspect the affected person's data. This mechanism does **not** authenticate original document provenance, define retention policy, or address historical Git exposure.

## Mandatory limits

Removing a file from the default branch **does not delete its historical Git objects**, PR refs, forks, external clones, third-party caches or mirrors. GitHub history repair and repository visibility require explicit owner action and coordination with downstream clones. GitGuardian passing is not evidence that history has been remediated. Also, this specific filename/blob rule cannot discover other PDFs containing private information; independent content review remains necessary.

**This PR intentionally breaks the old all-ten-source regeneration workflow** if merged without a private authorised replacement. `scripts/inventory/build_inventory.py` will show a source missing, and `scripts/audit/build_page_records.py --check` cannot rebuild the affected 441-page extraction from a source that is no longer present. Keep the pre-existing audit records clearly identified as historical, do not silently delete them and do not claim that the original complete audit can be reproduced. A subsequent source-storage integration must make encrypted/authorized private input available to trusted builders, with fail-closed behavior when absent. No private archive location is assumed to exist.

## Required owner-controlled sequence

1. Decide whether to immediately change repository visibility to private while remediation proceeds; this is strongly recommended. This PR cannot perform that change.
2. Preserve an authorized original only in protected, access-controlled storage after confirming rights and retention purpose.
3. Review and merge the quarantine change, understanding the source-rebuild limitation and its implications for QA.
4. With owner approval, coordinate a full Git-history rewrite, force-push plan, fork/clone remediation, and GitHub Support cache cleanup. A branch deletion by itself is insufficient.
5. Confirm closure via a trusted check of current tree, reachable history and GitHub-hosted surfaces; independently review the document's provenance and third-party rights.
6. Update INC-001 / DEF-001 **only with evidence** of the actual action. Human authorization cannot be fabricated.

Until those conditions are met, privacy incident INC-001 remains OPEN_OWNER_ACTION and `TRAINING_CONTENT_GO`, `COMMERCIAL_GO` and `ACADEMY_LIVE_GO` remain blocked as applicable.
