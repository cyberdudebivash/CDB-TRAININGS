# Competency Pathways

Data source: `catalog/learning-pathways.yaml` (validated by `scripts/validation/validate_catalog.py`). Generated regions below are rendered by `scripts/build/render_program_docs.py`.

## 1. What a level means

Levels describe **evidence collected inside this academy**. They are not job titles, salary bands, or claims of equivalence to any external certification. A learner "at Level 2" has produced Level 2 evidence for a skill; the same person may be Level 0 elsewhere.

<!-- BEGIN GENERATED: levels -->
| Level | Name | What the learner can do | Evidence collected | Supervision |
|---:|---|---|---|---|
| L0 | Foundations | Completes guided tasks in a safe, prepared environment by following written steps. | Automated checks pass on small guided exercises; learner can restate what each step did. | Every task is scaffolded; learner is expected to ask for help. |
| L1 | Guided practitioner | Performs routine tasks from a documented procedure and recognises when a result looks wrong. | Rubric-scored short artefacts (a parsed log, a unit-tested function, a defect report) built from provided starters. | Output is reviewed before it is relied on. |
| L2 | Independent practitioner | Completes standard tasks without a starter, justifies trade-offs, and validates their own work against data or tests. | Independent labs graded by automated checks plus a rubric; learner measures precision/recall, coverage or runtime rather than asserting them. | Self-checked; periodic review. |
| L3 | Advanced practitioner | Handles ambiguous, multi-step problems that cross domains; designs, evaluates and documents solutions for others to use. | Capstone with a reproducible repository or case file, a written decision record, and an evaluation against stated acceptance criteria. | Reviews others' work; owns outcomes. |
<!-- END GENERATED: levels -->

### Progression rules

1. A learner moves up a level **per skill area**, not per course: evidence of the previous level in that area is required.
2. Level evidence is an automated check **and** a rubric-scored artefact where judgement is involved. Seat time and page counts are not evidence.
3. Level 3 evidence is a capstone with a reproducible repository or case file, a written decision record, and an evaluation against stated acceptance criteria.
4. Prerequisites are enforced in the catalog: a pathway cannot include a course before its prerequisite courses, and a reusing module cannot precede the module it reuses.

## 2. Modules per level

<!-- BEGIN GENERATED: level-matrix -->
| Course | L0 | L1 | L2 | L3 |
|---|---:|---:|---:|---:|
| `COURSE-FND-DIGITAL` | 6 | · | · | · |
| `COURSE-SOC` | · | 3 | 5 | 6 |
| `COURSE-PY-ENG` | · | 2 | 7 | 2 |
| `COURSE-PY-AUTO` | · | · | 5 | 5 |
| `COURSE-JAVA-QA` | · | 3 | 4 | 3 |
| `COURSE-AI-ENG` | · | 1 | 4 | 7 |
| `COURSE-OSINT` | · | 3 | 9 | · |
| `COURSE-GCP-DE` | · | · | 4 | 7 |
| `COURSE-FE-ONBOARD` | · | 3 | 6 | 2 |
| `COURSE-CYBER-MEGA` | · | 2 | 5 | 7 |
<!-- END GENERATED: level-matrix -->

## 3. Pathways

<!-- BEGIN GENERATED: pathways -->
| Pathway | Modules | Planning hours | Capstone | Courses in order |
|---|---:|---:|---|---|
| **SOC analyst** (`PATH-SOC-ANALYST`) | 22 | 156 | `SOC-M14` | `FND-DIGITAL` → `PY-ENG`* → `SOC` |
| **Detection engineer** (`PATH-DETECTION-ENGINEER`) | 18 | 132 | `CYB-M11` | `FND-DIGITAL` → `PY-ENG`* → `SOC`* → `CYBER-MEGA`* |
| **Python engineer** (`PATH-PYTHON-ENGINEER`) | 17 | 124 | `PY-M11` | `FND-DIGITAL` → `PY-ENG` |
| **Automation engineer (Python)** (`PATH-AUTOMATION-ENGINEER`) | 21 | 145 | `PA-M10` | `FND-DIGITAL` → `PY-ENG`* → `PY-AUTO` |
| **Test automation engineer (Java)** (`PATH-TEST-AUTOMATION-JAVA`) | 16 | 124 | `JQA-M10` | `FND-DIGITAL` → `JAVA-QA` |
| **Applied AI / LLM engineer** (`PATH-AI-ENGINEER`) | 29 | 238 | `AI-M12` | `FND-DIGITAL` → `PY-ENG` → `AI-ENG` |
| **AI security practitioner** (`PATH-AI-SECURITY`) | 19 | 148 | `AI-M07` | `FND-DIGITAL` → `PY-ENG`* → `AI-ENG`* → `CYBER-MEGA`* |
| **Data engineer (Google Cloud)** (`PATH-DATA-ENGINEER-GCP`) | 22 | 166 | `GCP-M11` | `FND-DIGITAL` → `PY-ENG`* → `GCP-DE` |
| **Frontend engineer** (`PATH-FRONTEND-ENGINEER`) | 17 | 124 | `FE-M11` | `FND-DIGITAL` → `FE-ONBOARD` |
| **Lawful OSINT analyst** (`PATH-OSINT-ANALYST`) | 18 | 98 | `OSINT-M12` | `FND-DIGITAL` → `OSINT` |
| **Cybersecurity generalist** (`PATH-SECURITY-GENERALIST`) | 20 | 220 | `CYB-M14` | `FND-DIGITAL` → `CYBER-MEGA` |

`*` = only the listed modules of that course. Hours are planning estimates.
<!-- END GENERATED: pathways -->

### Pathway detail

<!-- BEGIN GENERATED: pathway-detail -->
### SOC analyst (`PATH-SOC-ANALYST`)

_Audience:_ Learners aiming at Tier-1/Tier-2 security-operations work  
_Capstone evidence:_ `SOC-M14`  
_Total:_ 22 modules, 156 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): PY-M01, PY-M02 · 2 modules · 20 h — Python needed for the detection and triage labs
3. SOC Analyst Professional Pathway (`COURSE-SOC`): all modules · 14 modules · 104 h

### Detection engineer (`PATH-DETECTION-ENGINEER`)

_Audience:_ SOC analysts moving to detection engineering  
_Capstone evidence:_ `CYB-M11`  
_Total:_ 18 modules, 132 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): PY-M01, PY-M02, PY-M03, PY-M04 · 4 modules · 32 h
3. SOC Analyst Professional Pathway (`COURSE-SOC`): SOC-M02, SOC-M03, SOC-M04, SOC-M06, SOC-M07, SOC-M09 · 6 modules · 46 h
4. Cybersecurity Specialist Tracks (from the Mega Course) (`COURSE-CYBER-MEGA`): CYB-M10, CYB-M11 · 2 modules · 22 h

### Python engineer (`PATH-PYTHON-ENGINEER`)

_Audience:_ Developers and analysts who need production-quality Python  
_Capstone evidence:_ `PY-M11`  
_Total:_ 17 modules, 124 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): all modules · 11 modules · 92 h

### Automation engineer (Python) (`PATH-AUTOMATION-ENGINEER`)

_Audience:_ Operations, QA and security staff automating repeatable work  
_Capstone evidence:_ `PA-M10`  
_Total:_ 21 modules, 145 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): PY-M01, PY-M02, PY-M03, PY-M04, PY-M05 · 5 modules · 40 h
3. Python Automation Pathway (`COURSE-PY-AUTO`): all modules · 10 modules · 73 h

### Test automation engineer (Java) (`PATH-TEST-AUTOMATION-JAVA`)

_Audience:_ Manual testers and Java developers moving into test automation  
_Capstone evidence:_ `JQA-M10`  
_Total:_ 16 modules, 124 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Java Test Automation Engineer Pathway (`COURSE-JAVA-QA`): all modules · 10 modules · 92 h

### Applied AI / LLM engineer (`PATH-AI-ENGINEER`)

_Audience:_ Engineers building LLM-based applications  
_Capstone evidence:_ `AI-M12`  
_Total:_ 29 modules, 238 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): all modules · 11 modules · 92 h
3. Applied AI and LLM Engineering Pathway (`COURSE-AI-ENG`): all modules · 12 modules · 114 h

### AI security practitioner (`PATH-AI-SECURITY`)

_Audience:_ Security staff assessing AI-enabled systems  
_Capstone evidence:_ `AI-M07`  
_Total:_ 19 modules, 148 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): PY-M01, PY-M02, PY-M05, PY-M07 · 4 modules · 36 h
3. Applied AI and LLM Engineering Pathway (`COURSE-AI-ENG`): AI-M01, AI-M02, AI-M03, AI-M05, AI-M07, AI-M08, AI-M09, AI-M10 · 8 modules · 72 h
4. Cybersecurity Specialist Tracks (from the Mega Course) (`COURSE-CYBER-MEGA`): CYB-M13 · 1 modules · 8 h

### Data engineer (Google Cloud) (`PATH-DATA-ENGINEER-GCP`)

_Audience:_ Data and software engineers building pipelines on Google Cloud  
_Capstone evidence:_ `GCP-M11`  
_Total:_ 22 modules, 166 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Python Engineering Pathway (`COURSE-PY-ENG`): PY-M01, PY-M02, PY-M03, PY-M05, PY-M08 · 5 modules · 40 h
3. Google Cloud Data Engineering Pathway (`COURSE-GCP-DE`): all modules · 11 modules · 94 h

### Frontend engineer (`PATH-FRONTEND-ENGINEER`)

_Audience:_ New frontend engineers and backend developers moving to frontend  
_Capstone evidence:_ `FE-M11`  
_Total:_ 17 modules, 124 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Frontend Engineering Onboarding Pathway (`COURSE-FE-ONBOARD`): all modules · 11 modules · 92 h

### Lawful OSINT analyst (`PATH-OSINT-ANALYST`)

_Audience:_ Analysts, journalists and security staff who need defensible open-source research  
_Capstone evidence:_ `OSINT-M12`  
_Total:_ 18 modules, 98 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Lawful OSINT Investigation Pathway (`COURSE-OSINT`): all modules · 12 modules · 66 h

### Cybersecurity generalist (`PATH-SECURITY-GENERALIST`)

_Audience:_ Learners choosing a specialism or building a broad security base  
_Capstone evidence:_ `CYB-M14`  
_Total:_ 20 modules, 220 planning hours

1. Digital and Technical Foundations (`COURSE-FND-DIGITAL`): all modules · 6 modules · 32 h
2. Cybersecurity Specialist Tracks (from the Mega Course) (`COURSE-CYBER-MEGA`): all modules · 14 modules · 188 h
<!-- END GENERATED: pathway-detail -->

## 4. How pathways are validated

| Check | Where |
|---|---|
| Every course and module referenced exists and belongs to the stated course | `validate_pathways()` |
| Prerequisite courses appear earlier in the pathway | `validate_pathways()` |
| A module that `reuses` another is preceded by it | `validate_pathways()` |
| Modules are listed in catalog order | `validate_pathways()` |
| The capstone module belongs to the pathway and sits at the highest level the pathway reaches | `validate_pathways()` |

## 5. What this document does not claim

- No pathway has been completed by any learner; hours are planning estimates.
- No employer, certification body or market data was used to choose these pathways; they follow the source documents' subject areas and the dependency graph. Whether they match demand is a hypothesis for the commercial team (see `docs/commercial/COMMERCIAL_READINESS.md`).
