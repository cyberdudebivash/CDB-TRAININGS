"""soc_lab - a small, deterministic harness for the CDB Academy SOC pathway.

It provides:
  * generator  - seeded synthetic Windows Security telemetry with labelled scenarios (no real data),
  * sigma_lite - a *teaching* evaluator for a documented subset of Sigma 2.1.0 (rules + correlation),
  * evaluate   - precision / recall of alerts against the hidden scenario labels,
  * triage     - structural checks of analyst triage records.

It is NOT a SIEM. Unsupported Sigma features raise an error instead of being ignored (fail closed).
"""

__version__ = "0.1.0"
