from __future__ import annotations

import stat
from io import StringIO
from pathlib import Path

import pytest

from ecl import job
@pytest.fixture(autouse=True)
def sas_directory(tmp_path: Path) -> None:
    (tmp_path / "sas").mkdir()


class _Bootstrap:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_missing_period_uses_legacy_usage_and_exit_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert job.main(["monthly_ecl_py.sh"]) == 2
    assert capsys.readouterr().err == "usage: monthly_ecl_py.sh <YYYYMM> [prod|uat]\n"


@pytest.mark.parametrize("args", [("202409",), ("202409", "prod"), ("202409", "PROD")])
def test_period_and_environment_are_passed_in_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, args: tuple[str, ...]
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    calls: list[tuple[str, str, Path]] = []
    sysparms: list[str] = []
    monkeypatch.setattr(
        job, "bootstrap", lambda sysparm, base: sysparms.append(sysparm) or _Bootstrap()
    )

    def fake_engine(period: str, root: Path):
        calls.append((period, str(Path.cwd()), root))

    monkeypatch.setattr(job.engine, "run", fake_engine)
    env = args[1] if len(args) > 1 else "uat"
    assert (
        job.run(args[0], env, stdout=StringIO(), stderr=StringIO())
        == 0
    )
    assert sysparms == [f"{args[0]} {env}"]
    assert calls == [(args[0], str(tmp_path / "sas"), tmp_path)]
    assert (tmp_path / "logs" / f"ecl_{args[0]}_{env}.log").exists()


def test_default_environment_comes_from_bootstrap_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(job, "bootstrap", lambda sysparm, base: seen.append(sysparm) or _Bootstrap())
    monkeypatch.setattr(job.engine, "run", lambda period, root: None)
    assert job.main(["prog", "202409"]) == 0
    assert seen == ["202409 uat"]


def test_paths_use_repo_logs_and_ignore_trailing_arguments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(job, "bootstrap", lambda sysparm, base: seen.append(sysparm) or _Bootstrap())
    monkeypatch.setattr(job.engine, "run", lambda period, root: None)
    assert job.main(["prog", "not-a-period", "prod", "ignored"]) == 0
    assert seen == ["not-a-period prod"]
    assert (tmp_path / "logs" / "ecl_not-a-period_prod.log").exists()


def test_error_scan_is_line_start_only_and_bare_count_is_printed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    monkeypatch.setattr(job, "bootstrap", lambda *a, **k: _Bootstrap())

    def fake_engine(period: str, root: Path):
        print("ERROR: at line start")
        print("message ERROR: in the middle")

    monkeypatch.setattr(job.engine, "run", fake_engine)
    stdout, stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == "1\n"
    assert stderr.getvalue() == "ECL run reported errors, see log\n"
    assert (tmp_path / "logs" / "ecl_202409_uat.log").read_text() == (
        "ERROR: at line start\nmessage ERROR: in the middle\n"
    )


def test_empty_log_is_clean_and_prints_bare_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    monkeypatch.setattr(job, "bootstrap", lambda *a, **k: _Bootstrap())
    monkeypatch.setattr(job.engine, "run", lambda period, root: None)
    stdout, stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=stdout, stderr=stderr) == 0
    assert stdout.getvalue() == "0\nECL run complete for 202409 (uat)\n"
    assert stderr.getvalue() == ""


def test_each_run_replaces_stale_log_contents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    monkeypatch.setattr(job, "bootstrap", lambda *a, **k: _Bootstrap())
    calls = 0

    def fake_engine(period: str, root: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            print("ERROR: first run failure")

    monkeypatch.setattr(job.engine, "run", fake_engine)
    first_stdout, first_stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=first_stdout, stderr=first_stderr) == 1
    assert first_stdout.getvalue() == "1\n"
    assert first_stderr.getvalue() == "ECL run reported errors, see log\n"

    second_stdout, second_stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=second_stdout, stderr=second_stderr) == 0
    assert second_stdout.getvalue() == "0\nECL run complete for 202409 (uat)\n"
    assert second_stderr.getvalue() == ""
    assert (tmp_path / "logs" / "ecl_202409_uat.log").read_text() == ""


def test_missing_log_matches_set_e_exemption_and_reports_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    monkeypatch.setattr(job, "bootstrap", lambda *a, **k: _Bootstrap())

    def fake_engine(period: str, root: Path):
        (tmp_path / "logs" / "ecl_202409_uat.log").unlink()

    monkeypatch.setattr(job.engine, "run", fake_engine)
    stdout, stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=stdout, stderr=stderr) == 0
    assert stdout.getvalue() == "ECL run complete for 202409 (uat)\n"
    assert "grep:" in stderr.getvalue()


def test_engine_failure_is_nonzero_without_scan_or_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(job, "ROOT", tmp_path)
    monkeypatch.setattr(job, "bootstrap", lambda *a, **k: _Bootstrap())
    monkeypatch.setattr(job.engine, "run", lambda period, root: (_ for _ in ()).throw(RuntimeError("failed")))
    stdout, stderr = StringIO(), StringIO()
    assert job.run("202409", "uat", stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    log = (tmp_path / "logs" / "ecl_202409_uat.log").read_text()
    assert "Traceback (most recent call last):" in log
    assert "RuntimeError: failed" in log


def test_python_wrapper_is_executable() -> None:
    mode = Path("jobs/monthly_ecl_py.sh").stat().st_mode
    assert mode & stat.S_IXUSR
    assert mode & stat.S_IXGRP
    assert mode & stat.S_IXOTH
