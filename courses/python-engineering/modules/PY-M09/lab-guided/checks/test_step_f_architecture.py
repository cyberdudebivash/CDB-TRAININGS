"""Step F - the edge: the core computes, the edge reads files and writes streams. The core can be tested without a file and the edge swapped without touching the core."""
from __future__ import annotations

import ast
import builtins
import io
import io as io_module
import re

import pytest

CORE = ("parse_line", "unique_ips", "failures_by_ip", "bursts", "top_users", "render", "analyze", "run")
FORBIDDEN_NAMES = {"open", "print", "input", "exit", "quit", "os", "pathlib", "subprocess", "socket", "argparse", "FileSource", "ListSource", "main"}
FORBIDDEN_SYS = {"stdout", "stderr", "stdin", "argv", "exit"}

LOG = "\n".join(
    ["2026-10-14T12:00:0%dZ 10.0.0.1 mallory FAIL" % i for i in range(6)]
    + ["2026-10-14T12:00:10Z 10.0.0.2 alice OK", "2026-10-14T12:00:11Z 10.0.0.2 bob FAIL", "not a log line"]
) + "\n"


def test_the_core_does_no_input_or_output_and_does_not_know_the_edge(pk):
    tree = ast.parse(open(pk.__file__, encoding="utf-8").read())
    found = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in CORE}
    assert set(found) == set(CORE), f"missing: {sorted(set(CORE) - set(found))}"
    for name, node in found.items():
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in FORBIDDEN_NAMES:
                pytest.fail(f"core function {name} uses {sub.id!r} (line {sub.lineno})")
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "sys" and sub.attr in FORBIDDEN_SYS:
                pytest.fail(f"core function {name} uses sys.{sub.attr} (line {sub.lineno})")


def test_a_list_source_gives_the_lines_it_was_given(pk):
    assert list(pk.ListSource(["a", "b"]).lines()) == ["a", "b"]
    assert pk.run(pk.ListSource(LOG.splitlines())) == pk.render(pk.analyze(LOG.splitlines()))


def test_a_file_source_is_lazy_and_reports_a_missing_file_when_it_is_read(pk, tmp_path):
    source = pk.FileSource(str(tmp_path / "missing.log"))                    # constructing it opens nothing and raises nothing
    with pytest.raises(FileNotFoundError):
        next(iter(source.lines()))


def test_a_file_source_yields_lines_without_their_line_endings(pk, tmp_path):
    path = tmp_path / "x.log"
    path.write_bytes("first\r\nsecond\nthird é\r\n\r\nlast".encode("utf-8"))
    assert list(pk.FileSource(str(path)).lines()) == ["first", "second", "third é", "", "last"]


def test_a_file_source_opens_as_utf8_and_closes_the_file_when_the_generator_is_closed(pk, tmp_path, monkeypatch):
    path = tmp_path / "x.log"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    opened = []
    real = builtins.open

    def recording(*args, **kwargs):
        handle = real(*args, **kwargs)
        opened.append((handle, kwargs))
        return handle

    monkeypatch.setattr(builtins, "open", recording)
    monkeypatch.setattr(io_module, "open", recording)
    gen = pk.FileSource(str(path)).lines()
    assert opened == []                                                       # nothing opened yet
    assert next(gen) == "one"
    assert len(opened) == 1 and not opened[0][0].closed
    assert str(opened[0][1].get("encoding", "")).lower().replace("-", "") == "utf8"
    gen.close()
    assert opened[0][0].closed


def test_a_file_source_closes_the_file_when_it_is_exhausted(pk, tmp_path, monkeypatch):
    path = tmp_path / "x.log"
    path.write_text("one\ntwo\n", encoding="utf-8")
    opened = []
    real = builtins.open
    monkeypatch.setattr(builtins, "open", lambda *a, **k: opened.append(real(*a, **k)) or opened[-1])
    monkeypatch.setattr(io_module, "open", builtins.open)
    assert list(pk.FileSource(str(path)).lines()) == ["one", "two"]
    assert opened and all(h.closed for h in opened)


def run_main(pk, argv):
    out, err = io.StringIO(), io.StringIO()
    code = pk.main(argv, out, err)
    return code, out.getvalue(), err.getvalue()


def test_main_writes_the_report_to_the_given_stream(pk, tmp_path, capsys):
    path = tmp_path / "x.log"
    path.write_text(LOG, encoding="utf-8")
    code, out, err = run_main(pk, [str(path)])
    assert code == 0 and err == ""
    assert out == pk.render(pk.analyze(LOG.splitlines()))
    assert "flagged: 10.0.0.1" in out and "malformed: 1" in out
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""                         # nothing leaked to the real streams


def test_main_options_change_the_analysis(pk, tmp_path):
    path = tmp_path / "x.log"
    path.write_text(LOG, encoding="utf-8")
    code, out, _ = run_main(pk, [str(path), "--threshold", "7", "--top", "1", "--window", "2"])
    assert code == 0 and "flagged: none" in out and out.count("\nuser ") == 1
    assert run_main(pk, [str(path), "--top", "0"])[1].count("\nuser ") == 0


@pytest.mark.parametrize("argv", [[], ["--threshold", "3"], ["x.log", "--bogus"], ["x.log", "--threshold", "abc"], ["x.log", "--window", "0"], ["x.log", "--threshold", "-1"], ["x.log", "--top", "-2"], ["a.log", "b.log"]])
def test_a_usage_error_returns_2_with_a_message_and_no_report(pk, argv):
    code, out, err = run_main(pk, argv)
    assert code == 2 and out == "" and "usage" in err.lower()


def test_an_unreadable_file_returns_1_with_one_line_and_no_traceback(pk, tmp_path):
    code, out, err = run_main(pk, [str(tmp_path / "missing.log")])
    assert code == 1 and out == ""
    assert err.startswith("perfkit: cannot read ") and err.count("\n") == 1 and "Traceback" not in err


def test_a_directory_is_not_a_log_file(pk, tmp_path):
    code, out, err = run_main(pk, [str(tmp_path)])
    assert code == 1 and out == "" and "perfkit: cannot read" in err


def test_the_report_text_has_the_documented_shape(pk):
    text = pk.render(pk.Report(10, 2, 4, 3, ("1.1.1.1", "2.2.2.2"), (("a", 3), ("b", 1))))
    assert text == "attempts: 10\nmalformed: 2\nfailures: 4\nunique ips: 3\nflagged: 1.1.1.1, 2.2.2.2\nuser a: 3\nuser b: 1\n"
    assert pk.render(pk.Report(0, 0, 0, 0, (), ())) == "attempts: 0\nmalformed: 0\nfailures: 0\nunique ips: 0\nflagged: none\n"
