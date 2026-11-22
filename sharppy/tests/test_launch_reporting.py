"""Exercise the executable entry point without starting Qt or using real settings."""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ENTRY_POINT = Path(__file__).resolve().parents[2] / "runsharp" / "SHARPpy.py"


def test_executable_preserves_startup_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    log = tmp_path / ".sharppy" / "sharppy-crash.log"
    log.parent.mkdir()
    log.write_text("previous crash\n", encoding="utf-8")

    def fail_startup():
        raise RuntimeError("interrupted startup download")

    monkeypatch.setitem(sys.modules, "full_gui", SimpleNamespace(main=fail_startup))
    with pytest.raises(RuntimeError, match="interrupted startup download"):
        runpy.run_path(str(ENTRY_POINT), run_name="__main__")

    saved = log.read_text(encoding="utf-8")
    assert saved.startswith("previous crash\n")
    assert "RuntimeError: interrupted startup download" in saved
    assert "fail_startup" in saved


def test_executable_does_not_report_success_as_a_crash(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = []
    monkeypatch.setitem(sys.modules, "full_gui", SimpleNamespace(main=lambda: calls.append(True)))

    runpy.run_path(str(ENTRY_POINT), run_name="__main__")

    assert calls == [True]
    assert not (tmp_path / ".sharppy" / "sharppy-crash.log").exists()


def test_unwritable_crash_log_preserves_original_error(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".sharppy").write_text("blocks the log directory", encoding="utf-8")

    def fail_startup():
        raise RuntimeError("original startup failure")

    monkeypatch.setitem(sys.modules, "full_gui", SimpleNamespace(main=fail_startup))
    with pytest.raises(RuntimeError, match="original startup failure"):
        runpy.run_path(str(ENTRY_POINT), run_name="__main__")
