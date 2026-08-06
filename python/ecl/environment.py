"""Behavioural equivalent of the SAS environment bootstrap."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import Callable, Mapping

from . import formats
from .config import table


class EnvironmentBootstrapError(RuntimeError):
    """Raised when the legacy bootstrap cannot initialise an environment."""


def scan_sysparm_env(sysparm: str) -> str:
    """Return the configured space-delimited SYSparm token, as ``%scan`` does."""
    tokens = [token for token in sysparm.split(" ") if token]
    position = int(_bootstrap_rules()["sysparm_env_position"])
    return tokens[position - 1] if len(tokens) >= position else ""


def _bootstrap_rules() -> dict[str, str]:
    rules = table("env_bootstrap.csv")
    return dict(zip(rules["KEY"].astype(str), rules["VALUE"].astype(str)))


def resolve_env(e: str) -> str:
    """Apply the configured SAS default without normalising case."""
    return e or _bootstrap_rules()["default_env"]


def read_env_config(path: Path) -> dict[str, str]:
    """Read SAS ``%let`` assignments from an environment config."""
    text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.DOTALL)
    assignments = re.findall(
        r"(?m)^\s*%let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*;",
        text,
    )
    return {name: value.strip() for name, value in assignments}


@dataclass(frozen=True)
class EnvironmentSettings:
    env: str
    inbound: str
    outbound: str
    histlib: str
    recon_tol: str
    max_term_m: str

    @property
    def recon_tolerance(self) -> float:
        return float(self.recon_tol)

    @property
    def max_term_months(self) -> int:
        return int(self.max_term_m)


@dataclass(frozen=True)
class Library:
    libref: str
    path: Path
    access: str
    persistence: str
    used_by_batch: bool
    note: str

    def write_path(self) -> Path:
        if self.access == "readonly":
            raise PermissionError(f"Library {self.libref} is read-only")
        return self.path


FormatFunction = Callable[[object], str]
FORMAT_REGISTRY: dict[str, FormatFunction] = {
    "$seg.": formats.segment_label,
    "stage.": formats.stage_label,
    "grade.": formats.grade_label,
}


@dataclass
class Environment:
    settings: EnvironmentSettings
    raw: Library
    stg: Library
    out: Library
    hist: Library
    autocall_path: Path
    base: Path
    note: str

    def close(self) -> None:
        if self.stg.persistence == "ephemeral":
            rmtree(self.stg.path, ignore_errors=True)

    def __enter__(self) -> Environment:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        self.close()


def _library(row: Mapping[str, object], settings: EnvironmentSettings, stg_path: Path) -> Library:
    source = str(row["SOURCE"])
    source_paths = {
        "INBOUND": Path(settings.inbound),
        "OUTBOUND": Path(settings.outbound),
        "HISTLIB": Path(settings.histlib),
        "WORK": stg_path,
    }
    return Library(
        libref=str(row["LIBREF"]),
        path=source_paths[source],
        access=str(row["ACCESS"]),
        persistence=str(row["PERSISTENCE"]),
        used_by_batch=str(row["USED_BY_BATCH"]).lower() == "true",
        note=str(row["NOTE"]),
    )


def bootstrap(sysparm: str = "", base: Path | None = None) -> Environment:
    """Initialise the four SAS libraries and included format definitions."""
    rules = _bootstrap_rules()
    root = base if base is not None else Path.cwd() / rules["base_relative_path"]
    env_name = resolve_env(scan_sysparm_env(sysparm))
    cfg_path = root / rules["config_env_dir"] / f"{env_name}{rules['config_env_suffix']}"
    if not cfg_path.is_file():
        raise EnvironmentBootstrapError(
            f"Unable to include environment config {cfg_path}; "
            "the legacy bootstrap is dependent on its run directory"
        )
    config = read_env_config(cfg_path)
    required = ("ENV", "INBOUND", "OUTBOUND", "HISTLIB", "RECON_TOL", "MAX_TERM_M")
    missing = [key for key in required if key not in config]
    if missing:
        raise EnvironmentBootstrapError(f"Environment config {cfg_path} is missing: {', '.join(missing)}")
    settings = EnvironmentSettings(*(config[key] for key in required))
    stg_path = Path(tempfile.mkdtemp(prefix="ecl-stg-"))
    library_rows = table("env_libraries.csv").to_dict("records")
    libraries = {
        str(row["LIBREF"]): _library(row, settings, stg_path) for row in library_rows
    }
    return Environment(
        settings=settings,
        raw=libraries["raw"],
        stg=libraries["stg"],
        out=libraries["out"],
        hist=libraries["hist"],
        autocall_path=root / rules["autocall_macro_dir"],
        base=root,
        note=f"NOTE: ECL engine initialised for environment {settings.env}",
    )
