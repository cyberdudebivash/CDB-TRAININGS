# Independent lab SOC-M04-L2 - Detect, triage and defend a tuning decision

| | |
|---|---|
| **Module** | SOC-M04 Authentication-attack detection and triage |
| **Outcomes assessed** | LO3, LO4, LO5 (and LO1, LO2, LO6 through the report) |
| **Level / duration** | 2 / about 2 hours |
| **Cost** | **$0**, offline |
| **Prerequisite** | Guided lab completed (you will reuse its tools and ideas) |
| **Grading** | Rubric `../../assessments/m04/rubric.yaml` - automated must-pass checks plus a human review |

## 1. Scenario

You inherit the detections from the guided lab on a **different day with different data**. The same SIEM has been in place for a week. The previous analyst left a
note: "the spray rules work, the VPN rule is fine." Management asks whether the detections would have caught what happened on 2026-03-09 and whether the noise is under control.

## 2. Your inputs

```bash
cd courses/soc-analyst/labs && . .venv/bin/activate        # from the guided lab setup
export WORK=../../../.work/soc-m04-ind
python -m soc_lab generate --profile independent --out $WORK/data --with-truth
python -m soc_lab enrich --events $WORK/data/events.jsonl --context $WORK/data/context.json --out $WORK/data/events.enriched.jsonl
```

This is **practice** data (a published seed). Formal assessments use an instructor-chosen seed, so do not memorise scenario details - learn the method.
`truth/` is the scoring key for practice runs: look at it only to check yourself **after** you have submitted your own conclusions.

Start by running the **guided solution unchanged** on the new data (`--rules m04-guided/solution/rules`) and read the report. What fails? That is your work list.

## 3. Deliverables (put them in one folder, for example `$WORK/submission/`)

1. `rules/` - your Sigma detection and correlation rules (valid under `soc_lab lint`, every rule has a description and ATT&CK tag).
2. `exceptions.yml` - suppressions you decided to keep. Each must be narrow, owned, justified and expiring (`lint` enforces the mechanical part).
3. `triage/*.json` - one record for every alert that needs a decision on a **compromise** or on a **false positive you tune** (the checker lists which scenarios are still missing a record).
4. `REPORT.md` (about 400-700 words) with these headings:
   - **Coverage** - which attack behaviour each rule catches and *what it would miss* (state at least two limits honestly);
   - **Tuning decisions** - for each exception, the evidence, the risk you accepted and when it expires;
   - **Evidence** - the commands you ran and the numbers they printed (recall, precision, suppressed alerts);
   - **Mapping** - ATT&CK technique IDs with the ATT&CK version, and which CSF 2.0 Functions your detections and actions serve;
   - **Next step** - one thing you would do next and why.

## 4. Constraints

- Use only `soc_lab` and the supported Sigma subset (see `lint` messages). Do not edit `soc_lab/`.
- No exception may use wildcards, last longer than 90 days or match on fields other than a source address and/or an account name alone.
- Every attack scenario must be detected. A suppression that hides real attack alerts fails the lab regardless of other results.

## 5. Self-check (not the grade)

```bash
python -m soc_lab lint --rules submission/rules --exceptions submission/exceptions.yml
python -m soc_lab detect --rules submission/rules --exceptions submission/exceptions.yml --events $WORK/data/events.enriched.jsonl --out $WORK/alerts.json
python -m soc_lab evaluate --alerts $WORK/alerts.json --truth $WORK/data/truth
python -m soc_lab check-triage --records submission/triage --alerts $WORK/alerts.json --events $WORK/data/events.jsonl --truth $WORK/data/truth
```

The graded decision is made on the **rubric** (`../../assessments/m04/rubric.yaml`): the must-pass criteria are measured by these commands; the rest is judged by a human
reviewer from your report and your rules. Independence matters: you may discuss concepts but must write your own rules, records and report.

## 6. Security boundaries and integrity

Same as the guided lab: synthetic data only, no network scanning. Instructors validate solutions with a private pack; the grader accepts instructor-chosen seeds so published
practice results cannot be reused for a graded attempt.

## 7. Cleanup

```bash
rm -rf $WORK
```
