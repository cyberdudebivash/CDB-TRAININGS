# SOC Analyst Professional Pathway (`COURSE-SOC`)

**Status: `REENGINEERING` - pilot. Not for sale or distribution as a finished product.**
One module (SOC-M04) is built and machine-verified; the other eleven are planned in [`catalog/courses.yaml`](../../catalog/courses.yaml).
No SME review has taken place.

## What this course is for

Develop analysts from a supported start (telemetry, triage) to independent professional practice (detection engineering, investigation, reporting). Completion is
awarded only for **demonstrated** competence: automated lab checks plus rubric-based review. It never promises employment, certification success or earnings.

## What exists today

| Module | State | Artefacts |
|---|---|---|
| SOC-M04 Authentication-attack detection and triage | **Built (pilot)** | [lesson](lessons/m04-auth-detection/lesson.md), [guided lab](labs/m04-guided/README.md), [independent lab](labs/m04-independent/README.md), [quiz](assessments/m04/quiz.md), [rubric](assessments/m04/rubric.yaml), [outcome map](curriculum/outcomes.yaml), [source map](curriculum/source-map.yaml), tests in `tests/pilot/` |
| SOC-M01..M03, M05..M12 | Planned | see the catalog |

## Layout

```
courses/soc-analyst/
  lessons/        lesson text (Markdown with front matter)
  labs/           soc_lab harness (Python package) + guided and independent labs
  assessments/    quiz (questions only) and the public rubric
  curriculum/     outcomes.yaml (traceability) and source-map.yaml (what happened to the original PDF)
  student/        student-edition build configuration
  instructor/     README only; the private pack is NOT stored in this public repository
```

## Run the checks

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/pilot -q
```

## Provenance

Replaces the ideas (not the text) of [`SOC Analyst Survival Playbook (2026 Edition).pdf`](../../SOC%20Analyst%20Survival%20Playbook%20%282026%20Edition%29.pdf), which is preserved
unchanged. The audit is in [`docs/audits/courses/soc-analyst-audit.md`](../../docs/audits/courses/soc-analyst-audit.md).
