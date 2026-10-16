"""Process-environment guard shared by the long-running validation scripts (run_lab_matrix.py, run_qa.py)."""
from __future__ import annotations

import signal


def restore_default_sigint() -> bool:
    """A process started in the background of a non-interactive shell (`( cmd & )`, a scheduler, some CI runners) inherits an IGNORED SIGINT, and so does every process below it:
    Python then installs no KeyboardInterrupt handler, and every test that sends Ctrl-C to a program under test (PY-M11's interrupt checks and lesson block) hangs or fails.
    That would make the evidence depend on how the run was started, so the long runs restore the default first. Returns True when it had to."""
    if signal.getsignal(signal.SIGINT) is signal.SIG_IGN:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        return True
    return False
