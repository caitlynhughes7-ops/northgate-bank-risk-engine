from pathlib import Path
from gc import collect

import pytest

from ecl import formats
from ecl.environment import (
    EnvironmentBootstrapError,
    FORMAT_REGISTRY,
    bootstrap,
    read_env_config,
    resolve_env,
    scan_sysparm_env,
)


ROOT = Path(__file__).resolve().parents[2]


def test_empty_sysparm_silently_selects_uat() -> None:
    with bootstrap(base=ROOT) as environment:
        assert environment.settings.env == "UAT"


@pytest.mark.parametrize(
    ("sysparm", "expected"),
    [
        ("202409 prod", "prod"),
        ("202409", ""),
        ("  202409   prod  ", "prod"),
        ("", ""),
        ("202409    prod extra", "prod"),
        ("202409\tprod", ""),
    ],
)
def test_scan_sysparm_matches_sas_scan(sysparm: str, expected: str) -> None:
    assert scan_sysparm_env(sysparm) == expected


def test_explicit_prod_selection_loads_all_environment_settings() -> None:
    with bootstrap("202409 prod", ROOT) as environment:
        assert environment.settings.env == "PROD"
        assert environment.settings.inbound == "/data/gcra/inbound"
        assert environment.settings.outbound == "/data/gcra/outbound"
        assert environment.settings.histlib == "/data/gcra/hist"
        assert environment.settings.recon_tol == "0.0005"
        assert environment.settings.recon_tolerance == 0.0005
        assert environment.settings.max_term_m == "120"
        assert environment.settings.max_term_months == 120
        assert environment.note == "NOTE: ECL engine initialised for environment PROD"


def test_environment_name_is_case_sensitive_and_not_normalised() -> None:
    assert resolve_env("") == "uat"
    assert resolve_env("UAT") == "UAT"
    with pytest.raises(EnvironmentBootstrapError, match="UAT.cfg"):
        bootstrap("202409 UAT", ROOT)


def test_env_config_parser_strips_comments_and_value_blanks(tmp_path: Path) -> None:
    config = tmp_path / "env.cfg"
    config.write_text("/* comment */\n%let X =  value  ;\n%let Y=two;")
    assert read_env_config(config) == {"X": "value", "Y": "two"}


def test_stg_is_ephemeral_and_distinct_per_bootstrap() -> None:
    first = bootstrap(base=ROOT)
    second = bootstrap(base=ROOT)
    first_path, second_path = first.stg.path, second.stg.path
    assert first_path.is_dir()
    assert second_path.is_dir()
    assert first_path != second_path
    first.close()
    second.close()
    assert not first_path.exists()
    assert not second_path.exists()


def test_stg_is_removed_when_environment_is_garbage_collected() -> None:
    environment = bootstrap(base=ROOT)
    stg_path = environment.stg.path
    assert stg_path.is_dir()
    del environment
    collect()
    assert not stg_path.exists()


def test_close_is_idempotent() -> None:
    environment = bootstrap(base=ROOT)
    stg_path = environment.stg.path
    environment.close()
    environment.close()
    assert not stg_path.exists()


def test_hist_is_assigned_but_unused_by_batch() -> None:
    with bootstrap(base=ROOT) as environment:
        assert environment.hist.path == Path(environment.settings.histlib)
        assert environment.hist.used_by_batch is False


def test_raw_library_is_readonly() -> None:
    with bootstrap(base=ROOT) as environment:
        assert environment.raw.access == "readonly"
        with pytest.raises(PermissionError):
            environment.raw.write_path()


def test_autocall_path_preserves_unresolvable_macro_prefix() -> None:
    with bootstrap(base=ROOT) as environment:
        assert environment.autocall_path == ROOT / "sas/macros"
        macro_files = list(environment.autocall_path.glob("m_*.sas"))
        assert macro_files
        for path in macro_files:
            macro_name = path.read_text().split("%macro ", 1)[1].split("(", 1)[0]
            assert not (environment.autocall_path / f"{macro_name}.sas").exists()


def test_wrong_cwd_bootstrap_raises_legacy_include_failure(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentBootstrapError, match="environment config"):
        bootstrap(base=tmp_path)


def test_unknown_environment_raises() -> None:
    with pytest.raises(EnvironmentBootstrapError, match="qa.cfg"):
        bootstrap("202409 qa", ROOT)


def test_format_registry_delegates_to_existing_format_functions() -> None:
    assert FORMAT_REGISTRY["$seg."] is formats.segment_label
    assert FORMAT_REGISTRY["stage."] is formats.stage_label
    assert FORMAT_REGISTRY["grade."] is formats.grade_label
