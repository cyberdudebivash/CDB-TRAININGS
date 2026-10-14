# Guided lab SOC-M04-L1 - From raw failures to a validated detection

| Field | Value |
|---|---|
| **Module** | SOC-M04 Authentication-attack detection and triage |
| **Outcomes practised** | LO1, LO2, LO3, LO4, LO5, LO6 |
| **Level / duration** | 2 / about 90 minutes |
| **Cost** | **$0**. Fully offline after `pip install`; no cloud account, no API key, no network scanning |
| **Lab state** | See `docs/qa/AUTOMATED_QA_REPORT.md` (this lab is run end to end by `tests/pilot/test_guided_lab.py`) |
| **Reference outcomes** | Open (this is a guided lab): expected output is shown after each step |

## 1. Objective

Measure how well the playbook's brute-force rule performs on labelled telemetry, build three rules that do better, triage five alerts,
tune two false positives **without losing any attack**, and re-measure.

## 2. Prerequisites and environment

| Item | Requirement |
|---|---|
| Skills | Lesson SOC-M04 read; command line; YAML |
| Python | 3.11 or newer (tested on 3.13) |
| Packages | `PyYAML==6.0.1`, `jsonschema==4.26.0` (`requirements.txt`) |
| OS | Linux, macOS or Windows (commands shown for a POSIX shell) |
| Disk | under 5 MB |

## 3. Security boundaries

- All data is **synthetic**. Addresses use RFC 1918 (internal) and RFC 5737 documentation ranges (external); the domain is `corp.example`.
- The lab contains **no tool that sends network traffic**. Do not adapt it to guess credentials against any system you do not own or are not authorised in writing to test.
- Do not put real log data into this harness: it is a teaching evaluator, not a hardened parser.

## 4. Setup

Run all commands from `courses/soc-analyst/labs`.

```bash
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export WORK=../../../.work/soc-m04                    # any scratch directory works
python -m soc_lab generate --profile guided --out $WORK/data --with-truth
python -m soc_lab enrich --events $WORK/data/events.jsonl --context $WORK/data/context.json --out $WORK/data/events.enriched.jsonl
```

Expected: the first command prints `generated 1191 events (profile=guided, seed=20260302)`. Every learner gets identical data (fixed seed).
`truth/` holds the scenario labels the evaluator uses - **do not open it before you have written your rules**.

## 4a. Input data

`events.jsonl` is Windows-Security-style telemetry: 4624 successes and 4625 failures. `context.json` is the asset inventory, change calendar and
service-account list. `enrich` adds `SrcNet24` and `SrcRole` (an asset-inventory lookup, else `internal`/`external`).

## 5. Steps

### Step A - Look at the data (LO2)

```bash
python m04-guided/explore.py $WORK/data/events.enriched.jsonl
```

Expected (excerpt): `events: 1191`, `by EventID: {4624: 254, 4625: 937}`, and a table whose top rows include
`10.0.2.15 failures= 480 distinct_accounts= 1`, `203.0.113.77 failures= 88 distinct_accounts= 48` and
`10.0.9.5 failures= 31 distinct_accounts= 17`.

*Checkpoint:* which of these three sources would you worry about first, and which single fact about each would change your mind?

### Step B - Measure the playbook rule (LO1, LO3)

```bash
python -m soc_lab detect --rules m04-guided/rules/naive_playbook --events $WORK/data/events.enriched.jsonl --out $WORK/alerts_naive.json
python -m soc_lab evaluate --alerts $WORK/alerts_naive.json --truth $WORK/data/truth
```

Expected:

```text
Recall    : 1/5 attack scenarios detected  (missed: S2, S3, S4, S6)
Precision : 1/2 alerts are true positives
False-positive alerts: 1   by scenario: {'F1': 1}
```

*Checkpoint:* why does the rule catch `S1` but not `S2`? (Hint: what does `group-by` contain, and how many failures does one account see in a spray?)

### Step C - Build better rules (LO3)

1. Copy the templates: `cp -r m04-guided/starter/rules $WORK/my_rules`.
2. Complete `mr_bruteforce_single_account.yml` and `mr_spray_single_source.yml` (replace every `TODO`), then add a third rule for **distributed spraying from one external network**
   (group by `SrcNet24`, count distinct `TargetUserName` over several hours, on external sources only - you need a base rule that selects `SrcRole: external`).
3. Check the rules, run them and measure:

```bash
python -m soc_lab lint --rules $WORK/my_rules
python -m soc_lab detect --rules $WORK/my_rules --events $WORK/data/events.enriched.jsonl --out $WORK/alerts.json
python -m soc_lab evaluate --alerts $WORK/alerts.json --truth $WORK/data/truth
```

Target: **all five attack scenarios detected**. With a single spray threshold you will also see a third false positive from the morning VPN rush (`F4`:
14 users behind one NAT address). Fix it with a **role-aware threshold** (lesson section 4): add base rules that select failures *from* and *not from* `SrcRole: vpn_nat`,
point the 10-account spray rule at the second, and give the VPN gateway its own rule with a higher threshold. The two false positives that remain after that
(`F1`, `F2`) are expected - Steps D and E deal with them.
If you are stuck, compare with `m04-guided/solution/rules/` **after** a real attempt. With the reference rules you should see:

```text
Recall    : 5/5 attack scenarios detected
Precision : 6/8 alerts are true positives
False-positive alerts: 2   by scenario: {'F1': 1, 'F2': 1}
```

(The morning VPN rush is handled by the reference rules' role-aware threshold.)

### Step D - Triage five alerts (LO4)

```bash
python -m soc_lab alerts --alerts $WORK/alerts.json
python -m soc_lab inspect --events $WORK/data/events.jsonl --ip 203.0.113.88 --event 4624     # pivot: did anything succeed?
mkdir -p $WORK/triage && cp m04-guided/starter/triage/TEMPLATE.json $WORK/triage/s4.json      # then edit it
```

Write one triage record for each alert that came from: single-account guessing (`S1`), the spray with a later success (`S4`), the scanner outside its change window (`S6`),
the stale service credential (`F1`) and the scanner inside its change window (`F2`). Each record follows `starter/triage/TEMPLATE.json`. Check them:

```bash
python -m soc_lab check-triage --records $WORK/triage --alerts $WORK/alerts.json --events $WORK/data/events.jsonl --truth $WORK/data/truth
```

Expected when all five are correct: `Triage records passed: 5/5`. Each failure message names exactly what is wrong (unrelated evidence, missing context source, indefensible
decision, suppression too broad, ...). The checker cannot judge your reasoning - write the `rationale` as if a colleague on the next shift must act on it.

### Step E - Tune two false positives and re-measure (LO5)

Create `$WORK/exceptions.yml` with one **narrow, owned, justified, expiring** exception for each false positive (see lesson section 6, and `exceptions` keys: `id, rule, match, reason, ticket, owner, valid_from, valid_until`).

```bash
python -m soc_lab lint --rules $WORK/my_rules --exceptions $WORK/exceptions.yml
python -m soc_lab detect --rules $WORK/my_rules --exceptions $WORK/exceptions.yml --events $WORK/data/events.enriched.jsonl --out $WORK/alerts_tuned.json
python -m soc_lab evaluate --alerts $WORK/alerts_tuned.json --truth $WORK/data/truth
```

Expected with the reference rules and exceptions (`m04-guided/solution/`):

```text
Recall    : 5/5 attack scenarios detected
Precision : 6/6 alerts are true positives
False-positive alerts: 0   by scenario: none
Suppressed alerts: 2  (of which hid real attacks: 0)
```

**The trap:** change the scanner exception so that it covers the whole day (for example `valid_from: "2026-03-02T00:00:00Z"`, `valid_until: "2026-03-30T00:00:00Z"`) and re-run.
Expected: `Suppressed alerts: 3  (of which hid real attacks: 1)` and `Recall    : 4/5 attack scenarios detected  (missed: S6)`. Why does one broad exception cost you the 14:10 attack, and what does the lesson say instead?

## 6. Expected observable outcomes (summary)

| Stage | Recall | Alerts that are true positives | False positives |
|---|---|---|---|
| Playbook rule | 1/5 | 1/2 | F1 |
| Your rules (before tuning) | 5/5 | 6/8 | F1, F2 |
| Your rules + exceptions | 5/5 | 6/6 | none; 2 suppressed, 0 attacks hidden |

## 7. Verification

`python -m soc_lab evaluate ...` prints recall, precision, per-scenario time to detect and the number of suppressed alerts that hid real attacks. `check-triage` prints per-record pass/fail.
Your lab is complete when the last table row is reproduced **and** `Triage records passed: 5/5`.

## 8. Troubleshooting

See the lesson, section 11. Also: if `evaluate` reports `Precision : no alerts raised`, your rules did not load the enriched file; if a rule uses `SrcRole` or `SrcNet24` you must pass `events.enriched.jsonl`.

## 9. Cleanup

```bash
rm -rf $WORK .venv        # removes generated data and the virtual environment
```

## 10. Assessment

This guided lab is **formative** and not graded. The graded work is the independent lab (`../m04-independent/README.md`) assessed with `../../assessments/m04/rubric.yaml`.
