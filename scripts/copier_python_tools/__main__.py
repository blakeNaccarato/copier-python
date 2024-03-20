"""CLI for tools."""

import json
import tomllib
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from json import dumps
from pathlib import Path
from platform import platform
from re import sub
from shlex import join, split
from subprocess import run
from sys import executable, stdout, version_info
from typing import TypeAlias

from cyclopts import App

APP = App()
"""CLI."""


def main():
    """Invoke the CLI."""
    APP()


# ! For local dev config tooling
PYRIGHTCONFIG = Path("pyrightconfig.json")
"""Resulting pyright configuration file."""
PYTEST = Path("pytest.ini")
"""Resulting pytest configuration file."""

# ! Dependencies
PYPROJECT = Path("pyproject.toml")
"""Path to `pyproject.toml`."""
REQS = Path("requirements")
"""Requirements."""
SYNC = REQS / "sync.in"
"""Core dependencies for syncing."""
DEV = REQS / "dev.in"
"""Other development tools and editable local dependencies."""
NODEPS = REQS / "nodeps.in"
"""Dependencies appended to locks without compiling their dependencies."""

# ! Platform
PLATFORM = platform(terse=True)
"""Platform identifier."""
match PLATFORM.casefold().split("-")[0]:
    case "macos":
        _runner = "macos-13"
    case "windows":
        _runner = "windows-2022"
    case "linux":
        _runner = "ubuntu-22.04"
    case _:
        raise ValueError(f"Unsupported platform: {PLATFORM}")
RUNNER = _runner
"""Runner associated with this platform."""
match version_info[:2]:
    case (3, 8):
        _python_version = "3.8"
    case (3, 9):
        _python_version = "3.9"
    case (3, 10):
        _python_version = "3.10"
    case (3, 11):
        _python_version = "3.11"
    case (3, 12):
        _python_version = "3.12"
    case (3, 13):
        _python_version = "3.13"
    case _:
        _python_version = "3.11"
VERSION = _python_version
"""Python version associated with this platform."""

# ! Compilation and locking
COMPS = Path(".comps")
"""Platform-specific dependency compilations."""
COMPS.mkdir(exist_ok=True, parents=True)
LOCK = Path("lock.json")
"""Locked set of dependency compilations for different runner/Python combinations."""


@APP.command()
def get_comp(high: bool = False) -> Path:
    """Compile dependencies for a system.

    Args:
        high: Highest dependencies.
    """
    if LOCK.exists():
        comp = get_comp_path(high)
        if existing_comp := json.loads(LOCK.read_text("utf-8")).get(comp.stem):
            comp.write_text(encoding="utf-8", data=existing_comp)
            return comp
    return compile(high)


@APP.command()
def compile(high: bool = False) -> Path:  # noqa: A001
    """Recompile dependencies for a system.

    Args:
        high: Highest dependencies.
    """
    sep = " "
    result = run(
        args=split(
            sep.join([
                f"{Path(executable).as_posix()} -m uv",
                f"pip compile --python-version {VERSION}",
                f"--resolution {'highest' if high else 'lowest-direct'}",
                f"--exclude-newer {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}",
                "--all-extras",
                sep.join([p.as_posix() for p in [PYPROJECT, DEV, SYNC]]),
            ])
        ),
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    comp = get_comp_path(high)
    comp.write_text(
        encoding="utf-8",
        data=(
            "\n".join([
                *[r.strip() for r in [result.stdout]],
                *[
                    line.strip()
                    for line in NODEPS.read_text("utf-8").splitlines()
                    if not line.strip().startswith("#")
                ],
            ])
            + "\n"
        ),
    )
    return log(comp)


@APP.command()
def lock() -> Path:
    """Lock all local dependency compilations."""
    LOCK.write_text(
        encoding="utf-8",
        data=json.dumps(
            indent=2,
            sort_keys=True,
            obj={
                **(json.loads(LOCK.read_text("utf-8")) if LOCK.exists() else {}),
                **{
                    comp.stem.removeprefix("requirements_"): comp.read_text("utf-8")
                    for comp in COMPS.iterdir()
                },
            },
        )
        + "\n",
    )
    return log(LOCK)


def get_comp_path(high: bool) -> Path:
    """Get a dependency compilation.

    Args:
        high: Highest dependencies.
    """
    return COMPS / f"{get_comp_name(high)}.txt"


def get_comp_name(high: bool) -> str:
    """Get name of a dependency compilation.

    Args:
        high: Highest dependencies.
    """
    return "_".join(["requirements", RUNNER, VERSION, *(["high"] if high else [])])


def log(obj):
    """Send an object to `stdout` and return it."""
    print(obj, file=stdout)  # noqa: T201
    return obj


@APP.command()
def sync_local_dev_configs():
    """Synchronize local dev configs to shadow `pyproject.toml`, with some changes.

    Duplicate pyright and pytest configuration from `pyproject.toml` to
    `pyrightconfig.json` and `pytest.ini`, respectively. These files shadow the
    configuration in `pyproject.toml`, which drives CI or if shadow configs are not
    present. Shadow configs are in `.gitignore` to facilitate local-only shadowing.

    Concurrent test runs are disabled in the local pytest configuration which slows down
    the usual local, granular test workflow.
    """
    config = tomllib.loads(PYPROJECT.read_text("utf-8"))
    # Write pyrightconfig.json
    pyright = config["tool"]["pyright"]
    data = dumps(pyright, indent=2)
    PYRIGHTCONFIG.write_text(encoding="utf-8", data=f"{data}\n")
    # Write pytest.ini
    pytest = config["tool"]["pytest"]["ini_options"]
    pytest["addopts"] = disable_concurrent_tests(pytest["addopts"])
    PYTEST.write_text(
        encoding="utf-8",
        data="\n".join(["[pytest]", *[f"{k} = {v}" for k, v in pytest.items()], ""]),
    )


Leaf: TypeAlias = int | float | bool | date | time | str
"""Leaf node."""
Node: TypeAlias = Leaf | Sequence["Node"] | Mapping[str, "Node"]
"""General node."""


def disable_concurrent_tests(addopts: str) -> str:
    """Normalize `addopts` string and disable concurrent pytest tests.

    Normalizes `addopts` to a space-separated one-line string.

    Args:
        addopts: Pytest `addopts` value.

    Returns:
        Modified `addopts` value.
    """
    return sub(pattern=r"-n\s*[^\s]+", repl="-n 0", string=join(split(addopts)))


if __name__ == "__main__":
    main()