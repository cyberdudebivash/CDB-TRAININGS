---
id: FND-M01
title: "Operating systems, files and permissions"
course: COURSE-FND-DIGITAL
level: 0
audience: "Entry-level technical learners and support staff with basic computer literacy"
prerequisites:
  - "Windows 10/11 or Linux with access to a disposable practice directory"
  - "Python 3.11+ for the optional guided lab"
estimated_time_hours: {lesson: 1.5, guided_lab: 1.25, independent_lab: 1.25, total: 4.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "Python 3.11+ standard library; tested locally on 3.13.5 only", linux: "POSIX permissions concepts, distribution differences apply", windows: "Windows 10/11 concepts; not executed on Windows"}
last_verified: 2026-10-15
---

# FND-M01 — Operating systems, files and permissions

## Learning objectives

| ID | You can... |
|---|---|
| **LO1** | Identify local OS path conventions and distinguish absolute and relative paths without privileged operations. |
| **LO2** | Explain files, directories, symbolic links and content hashes, and verify changes in a synthetic file inventory. |
| **LO3** | Interpret basic POSIX permissions and distinguish them from Windows ACLs using a bounded simulated access policy. |
| **LO4** | Collect and document evidence of a synthetic file change without modifying customer data or live access settings. |

This is a foundational training module—not qualification to administer a production operating system or investigate real customer evidence. Every experiment must use local synthetic data. The lesson, formative quiz and exercises are only a portion of the six-module Digital Foundations pathway. No qualified human reviewer or actual learner has yet approved this content.

## 1. Operating systems, processes, and paths (LO1)

An operating system provides services that applications rely upon to run: creating processes, allocating memory, exposing storage and network interfaces, and checking access. When an editor reads a document it generally requests access through operating-system facilities rather than commanding a disk directly. That distinction is useful when troubleshooting. A document may exist but remain inaccessible because the user identity lacks permission, the application selected a different location, or an intermediate folder cannot be traversed. An error about access must not be treated as permission to change access controls.

Windows frequently presents drives and paths such as C:\Users\Student\Documents. Linux exposes a single root / and paths such as /home/student/Documents. A Windows-style drive is a namespace feature, not proof of a physical drive. Network shares, mounted devices and virtualized environments complicate the picture. Beginners should understand the difference without trying to manipulate system storage. Use the home directory belonging to your own learner account. Avoid system directories and all folders belonging to other users.

An absolute path points from a root or drive. A relative path is interpreted from a process's current working directory. If a scheduled task runs with a different working directory from your interactive terminal, relative filenames can resolve to the wrong location. Before running any file-modifying command, confirm the current folder. In Windows PowerShell, `Get-Location` prints the current location and `Get-ChildItem` lists immediate children. In Linux, `pwd` and `ls` provide comparable observations, subject to shell configuration. These commands are observational; changing access rights is not part of this lesson.

Python's pathlib offers operations for constructing paths without manually joining separator characters. In the following code, no file is opened. A path is only a description until the program asks the filesystem for something.

```python run
from pathlib import Path
record = Path('reports') / 'status.txt'
assert not record.is_absolute()
assert record.name == 'status.txt'
assert record.parent.name == 'reports'
```

A path can be syntactically valid yet refer to no current file. Checking that a path exists and having permission to use it are independent concerns. Also remember that the filesystem is dynamic: an entry can disappear after you check it. Never build a security assumption solely on an earlier existence check. If a support technician reports a missing file, first record the intended location, the actual working directory, and a sanitized error message.

The distinction between Windows paths and POSIX paths can be studied without needing both systems. These pure path classes parse textual conventions without performing filesystem access.

```python run
from pathlib import PureWindowsPath, PurePosixPath
a = PureWindowsPath(r'C:\Practice\logs\day1.txt')
b = PurePosixPath('/practice/logs/day1.txt')
assert a.name == b.name == 'day1.txt'
assert str(b).startswith('/')
```

The appropriate implementation uses the semantics of the actual host operating system. A syntactically valid path to a device, a shared folder, or a mounted volume might require additional security review in real operations. Our beginner lab deliberately avoids all such paths.

## 2. Files, metadata, symbolic links, and hashes (LO2)

A regular file contains bytes. A directory contains named entries. A symbolic link references another path; following one can lead outside the folder you intended to inspect. Extensions such as .log and .pdf are conventions, not validation of content type or safety. Renaming a program from one extension to another does not make it benign. When receiving a diagnostic bundle, inspect it within authorized boundaries rather than assuming each file is trustworthy.

File metadata can include size, modification time, ownership, and permissions. These attributes help an analyst describe a state, but modification times are not perfect evidence of origin or integrity. A clock may be inaccurate. Some file copying tools update timestamps. An application may write temporary versions while saving a document. Therefore a professional report distinguishes observations from conclusions. Saying "the file changed" is different from saying who changed it, whether a change was legitimate, or why it happened.

A cryptographic hash is a fixed-size representation derived from file contents. SHA-256 is useful for comparing two versions of an artifact. If two computed digests match a previously trusted reference, the bytes almost certainly match. But a checksum alone does not authenticate the author, prove that data is malware-free, or establish consent to access it. If the same actor can modify both a file and its comparison manifest, a matching hash offers weak protection against deliberate tampering. A trustworthy process also protects the reference record.

```python run
import hashlib
original = b'synthetic diagnostic event A'
modified = b'synthetic diagnostic event B'
assert hashlib.sha256(original).hexdigest() != hashlib.sha256(modified).hexdigest()
assert len(hashlib.sha256(original).hexdigest()) == 64
```

Text bytes can vary even when a page looks identical to a human. The distinction between a line-feed and a carriage-return/line-feed pair is one example. Character encoding can also change the byte representation of visible text. Those changes correctly produce different content hashes. In an investigation, do not overwrite original data just to normalize hashes. Instead record exact acquisition conditions and compare deliberately.

Reading a whole multi-gigabyte file into memory is unnecessary. A file-inventory utility can hash bounded chunks. Our existing guided reference under the Digital Foundations starter pathway demonstrates that technique on temporary local files. It intentionally rejects symbolic links because they can resolve elsewhere. However its directory inspection is only a teaching example: race conditions between checking a path and opening the object can still occur. Do not advertise it as a forensic-grade acquisition utility.

## 3. Users, roles, POSIX bits, and Windows ACLs (LO3)

Permissions express which identity may take which action on a resource. On a common POSIX filesystem, read, write and execute are represented by r, w and x. For a regular file, read permits inspection of bytes and write permits modification, subject to surrounding system controls. Execute is relevant to program execution. On a directory, execute typically means search or traverse—necessary to access a known entry within it. Listing names additionally depends on directory read permission. These differences frequently explain why a file with a readable mode still cannot be reached.

The mode displayed as -rw-r----- describes a regular file that its owner may read and write, whose group may read, and to which others are not granted those permissions by these mode bits. The first character indicates object type; subsequent positions correspond to owner, group and other access. This is an introductory interpretation, not an exhaustive access decision. ACLs, parent directories, mount flags, mandatory policies, privileged identities and running process credentials can affect actual authorization.

```python run
import stat
mode = 0o640
assert bool(mode & stat.S_IRUSR)
assert bool(mode & stat.S_IWUSR)
assert bool(mode & stat.S_IRGRP)
assert not bool(mode & stat.S_IROTH)
```

Never solve an access error by blindly granting everyone permission. A command such as chmod 777 can expand access much more widely than intended and may create a confidentiality problem. Start with a documented business purpose: who is authorized, what operation is necessary, and which administrator may change the policy. A beginner in this course observes permissions; they do not modify shared or customer-owned access controls.

Windows uses ACLs: lists of rules for security principals, often with inheritance and deny entries. These are richer than three Unix mode digits and cannot be understood simply by translating an octal value. On a Windows practice machine, observe permitted information in File Explorer under a file's Security properties, or use Get-Acl in an authorized PowerShell session. Do not assume observed ACL entries equal effective access in every scenario; account tokens, inherited rules and shared-folder controls can matter.

The independent lab deliberately does not model Windows authorization or a complete Unix security subsystem. It implements a small role-to-operation table with exact matching and fail-closed input validation. This teaches the discipline of stating a limited contract. A toy algorithm that decides "allow" must never be wired into real customer access until an appropriate threat model, security architecture and review establish what the system must enforce.

## 4. Controlled file evidence and incident hygiene (LO4)

A support workflow separates observation from modification. First establish the approved scope and operator identity. Second create a disposable synthetic dataset and describe where it resides. Third record the names, sizes and hashes of the files. Fourth store the reference manifest outside the directory being measured. Finally compare a second inventory after one intentional, controlled change. The output supports a claim that a difference was observed; it does not automatically establish malicious intent.

Avoid placing a reference manifest inside the monitored directory because it becomes another file in the next snapshot and changes the inventory. Avoid saving credentials, real addresses, customer identifiers, or protected content in a learning submission. A professional evidence handoff should contain the task scope, operating-system version, exact commands, results and limitations. Any unexecuted check must be marked NOT_EXECUTED rather than reported as passing.

```python run
from pathlib import Path
import hashlib
import tempfile
with tempfile.TemporaryDirectory() as folder:
    artifact = Path(folder) / 'synthetic.txt'
    artifact.write_bytes(b'before')
    digest_before = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.write_bytes(b'after')
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() != digest_before
```

A concurrent program may modify a file while you enumerate and hash its directory. Your recorded inventory could reflect different moments for different entries. This is a classic consistency limitation. Real evidence acquisition may require snapshots, access isolation, audit trails and a documented chain of custody. The guided starter does not provide them. A team must select an approved evidence-handling procedure for genuine incidents.

The next sections connect the principles to technical execution and professional communication. The work is not an exercise in memorizing terminology. You must make testable predictions about the synthetic data, execute checks and interpret their output, then explain what is out of scope.

## 5. Guided operational exercise (LO1, LO2, LO4)

Imagine a fictional support customer reporting that a diagnostic folder changed after transfer. You are authorized to use only the sample folder created locally for this exercise. In the guided lesson, first record the current directory and runtime. Run the shared offline integrity tests. Create one synthetic artifact in a temporary folder and save its SHA-256 digest somewhere outside the monitored folder. Modify the artifact and prove that a later checksum differs. Then add another file and explain why a full directory inventory no longer matches the original.

Follow the steps in [the guided lab](lab-guided/README.md). Record any skipped symlink test when the host denies symlink creation. Do not disable endpoint security, change permissions, install unapproved software or use administrative rights to force success. Successful code execution is one part of the practical result. A complete learner submission must also explain why a matching checksum does not establish business authorization and why a live filesystem is not a consistent snapshot.

The provided integrity reference checks filenames, sizes and digests. It is not a production chain-of-custody system and should never be presented as a customer deployment. The grader will judge whether you describe the limitations accurately.

## 6. Independent access simulation (LO3, LO4)

You have a fictional report resource and a role policy mapping roles to operations. Your task is to complete a small Python function that decides whether an explicitly valid synthetic request is granted. It must use exact strings, reject malformed inputs and return false when a valid role lacks permission. It must not query system users, touch actual ACLs, modify file modes, or connect to any network service.

Start by predicting results for an allowed request, a denied request and an invalid request. Then read [the independent exercise](lab-independent/README.md). The student starter intentionally raises NotImplementedError until it is implemented. Test failures at that point are expected. Once the published tests pass, add one additional negative test in your own practice branch.

Explain two facts in your submission. First, a test double for authorization is not effective OS authorization. Second, an operating system permitting file access is not itself proof the company's business policy allows an employee to view the information. Permission design combines technical controls with human-approved scope.

## 7. Troubleshooting and limitations (LO1, LO2, LO3, LO4)

If your script reports FileNotFoundError, inspect the practice folder and your current working directory. If it reports PermissionError, do not widen access first; determine which account, path and operation were involved and whether the exercise scope is correct. If a test imports the wrong Python module, confirm which interpreter and package directory are being used. Distinguish failures in your implementation from failures to configure the learning environment.

If an expected checksum differs, compare exact file bytes and account for line endings or encoding. If a symlink test is skipped on Windows, record the skip; do not claim that cross-platform symlink behavior has been fully verified. If a synthetic access request is rejected, inspect the exact role and operation rather than adding a permissive wildcard to make tests green.

A critical professional skill is explaining uncertainty. The exercises use artificial resources with bounded contracts. Neither a green unittest report nor a successful PDF build would establish that a system is secure, commercially suitable, or operationally ready for customer workloads. The release process additionally requires human subject-matter review, learner validation, source traceability where applicable, accessible materials and complete pathway coverage.

## 8. Knowledge check and operational handoff (LO1, LO2, LO3, LO4)

Complete the eight-item knowledge check and both labs. Submit a sanitized summary that includes your operating system, interpreter version, commands, test counts, important observations, and limitations. Be explicit about any unsuccessful test. Never paste real personal information or confidential corporate paths into a public issue or assignment.

A strong handoff would let another authorized learner reproduce the synthetic scenario without inventing missing setup details. Include what you did not verify—for example Windows ACL enforcement, production-grade evidence preservation, or live multi-user concurrency. The instructor uses both technical checks and the public rubric; quiz success alone does not grant credit for practical competency. This entire Digital Foundations pathway remains under construction and must not be published as a completed Academy course.
