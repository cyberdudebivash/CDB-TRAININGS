# SOC-M04 knowledge check (10 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO2 | A Windows 4625 event shows LogonType 10. How was the logon attempted? | A) Interactively at the machine's keyboard. B) From the network, for example to a file share. C) Through Remote Desktop / Terminal Services (RemoteInteractive). D) By a service started by the Service Control Manager. |
| Q2 | LO2 | Which Sub Status value documented by Microsoft indicates that the user name does NOT exist? | A) 0xC000006A. B) 0xC0000064. C) 0xC0000234. D) 0xC0000072. |
| Q3 | LO1 | An attacker tries the same two passwords against 400 accounts, one attempt per account every 30 minutes. Which ATT&CK sub-technique best describes this? | A) T1110.001 Password Guessing. B) T1110.002 Password Cracking. C) T1110.003 Password Spraying. D) T1110.004 Credential Stuffing. |
| Q4 | LO3 | Which correlation design detects password spraying from a single source address? | A) `event_count` grouped by `TargetUserName`. B) `value_count` of `TargetUserName` grouped by `IpAddress`. C) `event_count` grouped by `Computer`. D) `value_count` of `EventID` grouped by `LogonType`. |
| Q5 | LO3 | Why does a rule that counts more than 5 failures per (source, account, host) in 5 minutes miss a password spray? | A) Its threshold is too high for a busy domain controller. B) A spray produces only one or two failures per account, so no per-account group reaches the threshold. C) Windows does not log failed logons from external addresses. D) Five minutes is longer than most sprays. |
| Q6 | LO4 | A spray alert fires for source X. Which single follow-up check most strongly changes the severity? | A) Whether the failures used the bad-password sub-status. B) Whether a successful logon (4624) from X follows for one of the failed accounts. C) How many distinct accounts were tried. D) What time of day it happened. |
| Q7 | LO5 | Which suppression is acceptable for a noisy service account? | A) Ignore all failures from 10.0.0.0/8. B) Ignore all 4625 events with LogonType 3. C) Ignore failures for that account from its one expected host for 7 days, with an owner and a ticket. D) Disable the spray rule until the noise stops. |
| Q8 | LO5 | After adding a suppression, what must you re-measure before you trust it? | A) The number of rules in the repository. B) That every attack scenario is still detected and no suppressed alert was a real attack. C) The CPU time of the evaluator. D) The length of the correlation timespan. |
| Q9 | LO6 | Under NIST CSF 2.0, analysing a detected anomaly to decide whether it is a cybersecurity incident belongs to which Function? | A) Identify. B) Protect. C) Detect. D) Recover. |
| Q10 | LO6 | NIST SP 800-61 Revision 3 organises incident response recommendations around which structure? | A) Four phases ending in post-incident activity. B) Six numbered phases from Preparation to Lessons Learned. C) The six CSF 2.0 Functions. D) The seven stages of the cyber kill chain. |

**Scoring:** instructors apply the key; 8/10 is the formative checkpoint. A miss on Q3-Q6 should trigger the remediation in the instructor notes before the independent lab.
