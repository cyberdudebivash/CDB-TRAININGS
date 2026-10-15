# FND-M01 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). 
The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | Which code constructs a relative path using local operating system semantics? | A) Path('logs') / 'status.txt'. B) eval('logs/status.txt'). C) chmod('/logs'). D) os.system('rm -rf /'). |
| Q2 | LO1 | Where is a relative filename normally resolved? | A) Against a fixed C: drive. B) Relative to the process working directory. C) Relative to CPU architecture. D) Within browser cache only. |
| Q3 | LO2 | Which claim can matching SHA-256 digests against a trusted reference support? | A) The author is authentic. B) The file is malware-free. C) The file bytes almost certainly match the reference. D) The user may access the file. |
| Q4 | LO2 | What is a symlink handling risk in a scoped file inventory? | A) It always contains malware. B) It may resolve outside the inspected directory. C) It always links to a regular file. D) It cannot exist on Windows. |
| Q5 | LO3 | What does execute permission on a POSIX directory ordinarily permit? | A) Traverse/search it. B) Copy every file automatically. C) Change its owner. D) Compile Python programs. |
| Q6 | LO3 | Why can Windows ACLs not be completely represented as POSIX octal mode bits? | A) Windows has no user accounts. B) Windows only allows read and write. C) Windows permissions do not exist. D) ACLs have richer entries and inheritance. |
| Q7 | LO4 | What is the appropriate first response to an unexplained access-denied error? | A) Grant Everyone full control. B) Disable endpoint protection. C) Verify authorized scope, account, path and operation. D) Delete the file. |
| Q8 | LO4 | Why is a live folder inventory not automatically a forensic-grade snapshot? | A) Hashes cannot run on Windows. B) Files can change while the inventory runs. C) Two distinct files always hash identically. D) Directories cannot contain symbolic links. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
