# authwatch 1.0 - specification

This is the contract of the application you build. The published checks (`checks/`) and the release gate (`tools/gate.py`) test parts of it; the instructors' suite tests every sentence. Where this text
says *must*, a conforming implementation has no choice; where it says nothing, you decide and document it in your README.

## 1. Purpose

`authwatch` reads authentication events and reports three patterns: **brute force** (many failed logins of one user from one address), **password spray** (failed logins against many users from one
address) and **compromise after failures** (a successful login right after a brute-force episode). It is a library and a command line.

## 2. Input

JSON Lines, UTF-8, one object per line. A byte-order mark at the very start of the input is ignored. A line ends with `\n` or `\r\n`; the last line needs no terminator. A line that is empty or only
white space is skipped and is not an error.

| Field | Type | Rule |
|---|---|---|
| `ts` | string | `YYYY-MM-DDTHH:MM:SS`, optionally followed by `.` and one to six digits, then `Z`. ASCII digits only; a real calendar date and time (no month 13, no 24:00, no second 60); no other offset |
| `user` | string | 1 to 64 characters of `A-Z a-z 0-9 _ . @ -` |
| `ip` | string | an IPv4 or IPv6 address in text form, **no** zone id (`%eth0`), no surrounding white space, no leading zeros in IPv4 octets. Stored in canonical form (`2001:DB8:0::1` becomes `2001:db8::1`; the text form of an IPv4-mapped address such as `::ffff:1.2.3.4` differs between Python releases, so it is not specified and not tested) |
| `outcome` | string | exactly `success` or `failure` |

Other keys are ignored. A value of the wrong JSON type (a number where a string is required, `null`, a boolean) is an error.

**Unusable lines.** Every other line is *unusable*. Its error has a **code** and a **line number** (counting from 1, blank lines included) and never contains any text of the line:

`bad_encoding` (not UTF-8) - `not_json` - `not_object` (valid JSON that is not an object) - `missing_field` - `bad_type` - `bad_timestamp` - `bad_user` - `bad_ip` - `bad_outcome` -
`line_too_long`.

When a line has more than one fault, which of the codes applies is not specified (the instructors' suite only uses lines with one fault). A line with a missing field is `missing_field`; a line whose field has the wrong type is `bad_type`; a string that breaks the rule of its field is `bad_user`, `bad_outcome`, `bad_timestamp` or `bad_ip`.

**Line length.** A line, including its terminator, may have at most 65 536 bytes (`MAX_LINE`). A longer line is one `line_too_long` error, and the rest of it is discarded without being kept in memory.

## 3. Library interface (importable as `authwatch`)

```text
__version__: str                                  the version, also printed by the command line and found in the package metadata
MAX_LINE: int                                     65536
Event(ts: datetime, user: str, ip: str, outcome: str)       frozen; ts is timezone-aware UTC
ParseError(code, line_no)                         a ValueError; .code, .line_no; str() is "line N: CODE"
TooManyErrors(count, limit)                       an Exception; .count, .limit
ConfigError(code, key=None)                       a ValueError; .code, .key; the message never shows a value
Rules(window_seconds=300, brute_force_failures=5, spray_users=5, compromise=True)   frozen, validated (section 5)
Finding(kind, severity, subject, first_ts, last_ts, count, ip, user, users)           frozen
Report(findings: tuple[Finding, ...], events: int, failures: int, out_of_order: int)  frozen

parse_line(raw: bytes, line_no: int) -> Event | None          None for a blank line; raises ParseError
read_events(stream, *, max_bad=100, on_bad=None) -> Iterator[Event]
parse_rules(text: str) -> Rules          load_rules(path) -> Rules
detect(events: Iterable[Event], rules: Rules) -> Report
render(report: Report, fmt: str = "text") -> str
```

**read_events.** `stream` is a binary file object (it has `readline(size)`). Lines are read one at a time with a bounded read (memory use does not depend on the size of the input). Every unusable line
is passed to `on_bad(error)` if it was given (`on_bad` may raise; the exception propagates). When more than `max_bad` lines were unusable, `TooManyErrors(count, limit)` is raised; `max_bad=None` means
no limit, `0` means the first error stops the reading. Events are yielded in the order of the stream.

## 4. Detection

Time is the `ts` of the events, never the clock of the machine. `detect` reads events in the order they arrive. Let *W* be `window_seconds`. A failure at time *t* **is inside a window that ends at
time t** if it happened strictly after *t - W* (a failure exactly *W* seconds old is outside).

- An event whose `ts` is **earlier than the `ts` of the event before it** (accepted or not - the comparison is with the newest `ts` seen so far) is *out of order*: it is skipped, counted in
  `Report.out_of_order`, and has no other effect. Equal timestamps are in order.
- **brute_force.** For each pair (user, ip): the failure that makes the number of the pair's failures inside the window reach `brute_force_failures` makes **one** finding (severity `medium`, subject
  `user@ip`, `first_ts` the oldest failure inside the window, `last_ts` this failure, `count` the number of failures inside the window). The pair is *in an episode* from then on; no further finding
  is made for it until a failure arrives after which fewer than `brute_force_failures` failures are inside the window; the next time the threshold is reached is a new episode and a new finding.
- **compromise_after_failures.** A success of a pair that has at least `brute_force_failures` failures inside the window (ending at the success) makes one finding (severity `high`, subject `user@ip`,
  `first_ts` the oldest of those failures, `last_ts` the time of the success, `count` their number), unless `Rules.compromise` is false. **Any** success of a pair - reported or not - ends the run of failures:
  the pair starts again from zero.
- **password_spray.** For each ip: the failure that makes the number of **distinct users** who failed from that address inside the window reach `spray_users` makes one finding (severity `medium`,
  subject = the address, `user` is `None`, `users` the sorted distinct users, `first_ts` the oldest failure of the address inside the window, `last_ts` this failure, `count` the number of failures of
  the address inside the window). Episodes work as for brute force (the address is in an episode until fewer than `spray_users` distinct users are inside the window after a failure).
- `Report.findings` is ordered by `(first_ts, kind, subject)`. `Report.events` counts every event given to `detect` (including out-of-order ones), `Report.failures` the failures that were not skipped.
- `detect` keeps state only for sources that were active within the last window: memory use does not grow with the number of events.

## 5. Rules

`window_seconds` is an `int` from 1 to 86 400; `brute_force_failures` and `spray_users` are `int`s from 2 to 1000; `compromise` is a `bool`. A `bool` is not an `int` here, a float is neither. Anything
else is `ConfigError` with code `bad_value` and the key. `Rules` is immutable.

`parse_rules(text)` reads YAML with a **safe** loader: nothing in the document is ever executed. An empty document (or only comments) means the defaults. Codes: `bad_yaml` (not valid YAML, or nested
so deeply that the parser fails), `not_a_mapping`, `unknown_key` (the message may name the key only if it is `[A-Za-z0-9_]{1,40}`, otherwise `?`), `bad_value`. `load_rules(path)` reads at most
65 536 bytes (`too_large` when the file is longer), `unreadable` when it cannot be read, `bad_yaml` when it is not UTF-8.

## 6. Output

`render(report, "json")` returns an object with sorted keys, indented by two spaces, ending with a newline:

```text
{"schema": 1, "summary": {"events": N, "failures": N, "out_of_order": N, "findings": N},
 "findings": [{"kind", "severity", "subject", "first_ts", "last_ts", "count", "ip", "user", "users"} ...]}
```

Times are written like the input (`...Z`, with a fraction only when it is not zero, then always six digits). `user` is `null` for a spray; `users` is a list. `render(report, "text")` writes one line
per finding - the severity in capitals, the kind, the subject, `first_ts..last_ts` and `count=N` - then a last line `events=N failures=N out_of_order=N findings=N`. The default format is `text`;
any other format is a `ValueError`. The output depends only on the report: the same report gives the same bytes.

## 7. Command line

`authwatch scan [options] [FILE ...]` and `python -m authwatch scan ...` behave identically. `authwatch --version` prints `authwatch <version>`.

| Option | Meaning |
|---|---|
| `FILE` | JSON Lines files, read in order as one stream. A name ending in `.gz` is decompressed while it is read. `-` or no file at all: standard input |
| `--rules FILE` | YAML rules (section 5) |
| `--format text\|json` | default `text` |
| `--output FILE` | write the report to this file **atomically** (a temporary file in the same directory, then a rename) with mode `0600`; a failed run leaves an existing file untouched and leaves no temporary file behind |
| `--max-bad N` | stop when more than N lines of the **whole run** are unusable (default 100) |
| `--fail-on-findings` | exit status 1 when there is at least one finding |
| `-v`, `--verbose` | structured diagnostics on standard error, one JSON object per line, never any content of the input: `{"event": "scan.file", "level": "info", "index": N, "stdin": bool}` for each input named on the command line (N counts from 0), `{"event": "scan.bad_line", "level": "info", "line": N, "code": CODE}` for each unusable line, and at the end `{"event": "scan.done", "level": "info", "events": N, "failures": N, "out_of_order": N, "findings": N}` |

**Streams.** The report goes to standard output (or `--output`); everything else goes to standard error. If any line was unusable, exactly one warning is written to standard error when the scan has finished: `authwatch: warning: N unusable input line(s) skipped (first: line L, CODE)`. Unusable rules are reported as `authwatch: configuration error: ` followed by the `ConfigError` message (its code and, when there is one, the key). No message ever contains input text. No traceback is ever shown for a failure listed below.

**Exit status.** 0 the scan finished; 1 it finished, there were findings and `--fail-on-findings` was given; 2 a wrong command line or unusable rules (nothing is read); 3 an unreadable or corrupt
input, a failed output, or too many unusable lines (no report is written); 130 interrupted by Ctrl-C. If the reader of standard output goes away (`authwatch scan ... | head -1`) the program ends
quietly: no traceback, no message.

## 8. The prototype

`prototype/authwatch_proto.py` is the script this application replaces. Where it disagrees with this specification, the specification is right: the prototype reads the whole file into memory, runs
`eval` on every line, hides every error, writes `utcnow()`-style naive times, measures time with `timedelta.seconds`, reports at six failures when the rule says five, reports each alert twice, passes
user names to a shell, and knows nothing of sprays, compromises, ordering or exit codes. Keep what is right (the idea, the thresholds' meaning), change the rest.
