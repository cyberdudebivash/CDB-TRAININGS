# Google Cloud Data Engineering Pathway

**Course ID:** `COURSE-GCP-DE`  
**Development state:** `STARTER_LAB_IMPLEMENTED` — NOT a completed course, NOT `TRAINING_CONTENT_GO`, NOT approved for sale or Academy publication.  
**Planned parent modules:** GCP-M01 / GCP-M02 / GCP-M03  
**Legacy source:** GCP-DATA-ENGINEER-TRAINING.pdf

## Current usable training artifact

[Zero-cloud-cost ingestion quality gate](labs/batch-quality/README.md) is a standalone, locally testable operational starter. Its synthetic customer scenario is: A data engineer inspects synthetic order CSV rows before an approved future Cloud Storage to BigQuery pipeline ingests them.

**Outcomes from this starter:** Data quality, invalid row quarantine, cost-safe dry-run planning. The lab establishes a concrete exercise with positive and negative cases and requires no paid cloud/API subscriptions.

## How this fits the professional curriculum

This starter is an early work product aligned to the existing `catalog/courses.yaml` pathway, **not** an implemented catalog module. Do not change any module to `BUILT` based solely on the presence of this exercise. The complete course requires its full source-PDF semantic audit (where applicable), curriculum modules, lessons, graded independent assessments, operational scenarios, capstone, research currency verification, protected instructor materials, a validated course PDF and documented approvals.

## Operational and release limitations

This is a local pre-ingestion validation. It does not execute Cloud Storage, BigQuery, Dataflow, Pub/Sub, IAM, or billed GCP workloads.

Full source traceability and author permissions remain governed by the portfolio release gates. No claim of customer system integration has been made. **The legacy source PDF remains unchanged.**

## Immediate next work

- Expand the mapped module into a comprehensive lesson with instructional examples, source-to-new-content mapping, assessment and independent lab.
- Confirm technology baselines against official sources and document dated evidence.
- Exercise a clean learner environment and review security/privacy/IP applicability.
- Add content-bound execution evidence to the existing Gate A system **only after** all module-required artifacts and tests are complete.
