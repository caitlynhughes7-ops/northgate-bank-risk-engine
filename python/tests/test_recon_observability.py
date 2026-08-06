import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

from ecl.recon_observability import recon_observability


def _frames(drawn=(100.0, 100.0), ead=(100.0, 100.0), stage=(1, 1)):
    return (
        pd.DataFrame({"DRAWN_BAL": drawn}),
        pd.DataFrame({"EAD": ead, "ECL": [1.0] * len(ead), "STAGE": stage}),
    )


def test_observability_breach_is_logged_without_batch_error():
    # A breach is visible but uses OBS:, not the shell's ERROR: signal.
    tape, account = _frames(drawn=(100.0, 100.0), ead=(110.0, 110.0))
    lines = []
    artifact = recon_observability(tape, account, env="prod", emit=lines.append)
    assert artifact["control_1"]["env_tolerance_breach"] is True
    assert artifact["control_1"]["spec_section_8_tolerance_breach"] is True
    assert all(not line.startswith("ERROR:") for line in lines)
    assert any(line.startswith("OBS: [ECL]") for line in lines)


def test_observability_non_breach_and_not_evaluable_control():
    # Matching totals do not breach and prior-month coverage remains unavailable.
    tape, account = _frames()
    artifact = recon_observability(tape, account, emit=lambda _: None)
    assert artifact["control_1"]["env_tolerance_breach"] is False
    assert artifact["control_3"]["status"] == "not_evaluable"


def test_observability_missing_and_zero_totals_are_non_failing():
    # Missing and zero denominators produce null differences and breach flags.
    tape = pd.DataFrame({"DRAWN_BAL": [np.nan]})
    account = pd.DataFrame({"EAD": [np.nan], "ECL": [np.nan], "STAGE": [1]})
    artifact = recon_observability(tape, account, emit=lambda _: None)
    control = artifact["control_1"]
    assert control["relative_difference"] is None
    assert control["env_tolerance_breach"] is None


def test_observability_threshold_comes_from_config(monkeypatch):
    # Control 2 uses the configured threshold rather than a model-code literal.
    tape, account = _frames(stage=(None, 1))
    monkeypatch.setattr(
        "ecl.recon_observability._rules",
        lambda: {
            "default_env": "uat",
            "spec_section_8_tolerance": "0.0001",
            "null_stage_error_threshold": "1",
        },
    )
    artifact = recon_observability(tape, account, emit=lambda _: None)
    assert artifact["control_2"]["breach"] is False


def test_observability_artifact_is_strict_json_and_no_official_paths(tmp_path):
    # The tool writes only observability output under the supplied temporary root.
    import shutil

    shutil.copytree(Path(__file__).resolve().parents[2] / "data/input", tmp_path / "data/input")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "python")
    completed = subprocess.run(
        [
            sys.executable,
            "tools/recon_observability.py",
            "--period",
            "202409",
            "--root",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    artifact_path = tmp_path / "data/output/observability/recon_observability_202409.json"
    artifact = json.loads(artifact_path.read_text())
    assert artifact["control_3"]["status"] == "not_evaluable"
    assert not list(tmp_path.rglob("ecl_by_segment_202409.csv"))
    assert not list(tmp_path.rglob("ECL_GL_FEED_202409.txt"))


def test_observability_tool_returns_zero_on_breach():
    # A breached candidate control is observability only and cannot abort the tool.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "python")
    completed = subprocess.run(
        [sys.executable, "tools/recon_observability.py", "--period", "202409"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0


def test_degraded_observability_artifact_identifies_exception(tmp_path):
    # Input failures remain non-fatal but identify their exception type.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "python")
    completed = subprocess.run(
        [
            sys.executable,
            "tools/recon_observability.py",
            "--period",
            "202409",
            "--root",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    artifact = json.loads(
        (tmp_path / "data/output/observability/recon_observability_202409.json").read_text()
    )
    assert artifact["exception_type"] == "FileNotFoundError"
