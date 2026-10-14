"""Your regression tests for the PY-M07 guided lab. Run:  python -m pytest student_tests

One regression test (or more) per vulnerability: it must FAIL if the vulnerability is put back. The lab README says how the tests are graded.
"""
import json  # noqa: F401
import os  # noqa: F401
import pickle  # noqa: F401
import sqlite3  # noqa: F401
import ssl  # noqa: F401

import pytest  # noqa: F401

import helpdesk  # noqa: F401

# TODO V1 calculate(): arithmetic works, everything else raises ValueError.
# TODO V2 find_users(): quote characters in a name are data, never SQL.
# TODO V3 list_files(): shell metacharacters in a directory name are never executed.
# TODO V4 read_attachment(): neither ../ nor an absolute path nor a symlink may leave the attachment folder.
# TODO V5 load_session(): attacker-supplied bytes are never executed (check for a side effect, not just an exception).
# TODO V6 load_config(): a YAML tag must not run code (again check for a side effect).
# TODO V7 make_tls_context(): certificates and host names are verified.
# TODO V8 hash_password(): two hashes of the same password differ.
