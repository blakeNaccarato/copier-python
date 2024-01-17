"""Bump template `.pre-commit-config.yaml` and `requirements.txt`.

Synchronize `ruff` in pre-commit and `requirements.txt`.
"""

import re
from pathlib import Path

PRE_COMMIT = Path("template/.pre-commit-config.yaml")
REQUIREMENTS = Path("template/.tools/requirements/requirements_both.txt")

patterns = {
    "ruff": r"""
  - repo: "https:\/\/github\.com\/charliermarsh\/ruff-pre-commit"
    rev: "v?(?P<version>[\d.]+)"
"""
}

# Bump pre-commit
pre_commit_text = PRE_COMMIT.read_text(encoding="utf-8")
versions = {
    package: re.search(pattern, PRE_COMMIT.read_text(encoding="utf-8"))["version"]  # type: ignore
    for package, pattern in patterns.items()
}
# fmt: off
# Visually align these long lines before mapping them below
ruff_find =   '        additional_dependencies: ["ruff=='
ruff_repl =  f'        additional_dependencies: ["ruff=={versions["ruff"]}"]'
# fmt: on
pre_commit_lines = pre_commit_text.split("\n")
for line_number, line in enumerate(pre_commit_lines):
    if line.startswith(ruff_find):
        pre_commit_lines[line_number] = ruff_repl
PRE_COMMIT.write_text(encoding="utf-8", data="\n".join(pre_commit_lines))

# Bump requirements
requirements_lines = REQUIREMENTS.read_text(encoding="utf-8").split("\n")
for line_number, line in enumerate(requirements_lines):
    if line.startswith("ruff"):
        requirements_lines[line_number] = f"ruff=={versions['ruff']}"
REQUIREMENTS.write_text(encoding="utf-8", data="\n".join(requirements_lines))