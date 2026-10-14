# Examples for logkit

Run them against your module from the lab folder: `python -m pytest` (the check `test_examples.py` runs this file as a doctest).

```
>>> from logkit import parse_log_line, count_levels, top_messages, busiest_hour, mask_ips
>>> parse_log_line("2026-10-14 12:00:01 ERROR payment failed for order 7")
('2026-10-14 12:00:01', 'ERROR', 'payment failed for order 7')
>>> parse_log_line("2026-02-30 12:00:01 INFO impossible date")
Traceback (most recent call last):
    ...
ValueError: invalid log line: 2026-02-30 12:00:01 INFO impossible date
>>> lines = [
...     "2026-10-14 12:00:01 INFO started",
...     "2026-10-14 12:10:00 ERROR disk full",
...     "",
...     "garbage",
...     "2026-10-14 13:00:00 ERROR disk full",
...     "2026-10-14 12:30:00 INFO started",
... ]
>>> count_levels(lines)
{'INFO': 2, 'ERROR': 2, 'INVALID': 1}
>>> top_messages(lines, 1)
[('disk full', 2)]
>>> busiest_hour(lines)
'2026-10-14 12'
>>> busiest_hour(["nothing valid"]) is None
True
>>> mask_ips("from 192.168.1.25 and 10.0.0.1.")
'from 192.168.1.x and 10.0.0.x.'
>>> mask_ips("version 1.2.3 build 999.1.1.1")
'version 1.2.3 build 999.1.1.1'

```
