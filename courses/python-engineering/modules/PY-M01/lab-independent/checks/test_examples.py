"""Runs examples.md as a doctest against the learner's logkit.py. These are the *visible* examples; instructors hold a larger hidden suite."""
from __future__ import annotations

import doctest
import os
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"


def test_the_published_examples_pass(logkit):
    result = doctest.testfile(str(LAB / "starter" / "examples.md"), module_relative=False, globs={}, optionflags=doctest.ELLIPSIS, verbose=False)
    assert result.attempted >= 10, "the examples file was not run"
    assert result.failed == 0, f"{result.failed} of {result.attempted} examples fail (run `python -m doctest starter/examples.md` for details)"
