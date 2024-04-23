"""CLI for tools."""

from collections.abc import Collection
from pathlib import Path
from re import finditer
from typing import NamedTuple

from cyclopts import App

from copier_python_tools.sync import (
    COMPS,
    PLATFORM,
    VERSION,
    escape,
    get_all_comp_names,
    get_comp_key,
    synchronize,
)

APP = App(help_format="markdown")
"""CLI."""


def main():  # noqa: D103
    APP()


class Comp(NamedTuple):
    """Dependency compilation."""

    low: Path
    """Path to the lowest direct dependency compilation."""
    high: Path
    """Path to the highest dependency compilation."""


@APP.command
def sync():
    """Prepare a compilation.

    Args:
        get: Get the compilation rather than compile it.
    """
    COMPS.mkdir(exist_ok=True, parents=True)
    for comp_names, comps in zip(get_all_comp_names(), synchronize(), strict=True):
        comp_paths = Comp(
            COMPS / f"{comp_names.low}.txt", COMPS / f"{comp_names.high}.txt"
        )
        platform, version = get_comp_key(comp_names.low).split("_")
        if platform == PLATFORM and version == VERSION:
            log(comp_paths)
        for name, comp in zip(comp_names, comps, strict=True):
            (COMPS / f"{name}.txt").write_text(encoding="utf-8", data=comp)


@APP.command
def get_actions():
    """Get actions used by this repository.

    For additional security, select "Allow <user> and select non-<user>, actions and
    reusable workflows" in the General section of your Actions repository settings, and
    paste the output of this command into the "Allow specified actions and reusable
    workflows" block.

    Args:
        high: Highest dependencies.
    """
    actions: list[str] = []
    for contents in [
        path.read_text("utf-8") for path in Path(".github/workflows").iterdir()
    ]:
        actions.extend([
            f"{match['action']}@*,"
            for match in finditer(r'uses:\s?"?(?P<action>.+)@', contents)
        ])
    log(sorted(set(actions)))


def log(obj):
    """Send object to `stdout`."""
    match obj:
        case str():
            print(obj)  # noqa: T201
        case Comp():
            for comp in obj:
                log(comp)
        case Collection():
            for o in obj:
                log(o)
        case Path():
            log(escape(obj))
        case _:
            print(obj)  # noqa: T201


if __name__ == "__main__":
    main()
