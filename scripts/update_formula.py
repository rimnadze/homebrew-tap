#!/usr/bin/env python3
"""Update homebrew-tap formula with latest PyPI versions.

Usage:
    python scripts/update_formula.py

Fetches the latest published version of link-project-to-chat from PyPI,
updates URLs and hashes for the main package and all dependencies,
and writes the result to Formula/link-project-to-chat.rb.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

FORMULA_PATH = Path(__file__).parent.parent / "Formula/link-project-to-chat.rb"
PACKAGE_NAME = "link-project-to-chat"


def parse_dependencies(formula: str) -> list[str]:
    """Extract resource names from the formula."""
    return re.findall(r'resource "([^"]+)" do', formula)


def pypi_sdist(name: str, version: str | None = None) -> tuple[str, str]:
    """Fetch (url, sha256) for the sdist of a package from PyPI."""
    api = f"https://pypi.org/pypi/{name}/json" if not version else f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(api) as resp:
        data = json.loads(resp.read())
    for f in data["urls"]:
        if f["packagetype"] == "sdist":
            return f["url"], f["digests"]["sha256"]
    raise ValueError(f"No sdist found for {name} {version or '(latest)'}")


def pypi_version(name: str) -> str:
    """Get the latest version of a package from PyPI."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as resp:
        data = json.loads(resp.read())
    return data["info"]["version"]


def update_main_package(formula: str, url: str, sha256: str) -> str:
    # Replace the url line before `sha256 ... license`
    formula = re.sub(
        r'(  url ")[^"]+(")',
        rf'\g<1>{url}\g<2>',
        formula,
        count=1,
    )
    # Replace the sha256 line before `license`
    formula = re.sub(
        r'(  sha256 ")[^"]+("\n  license)',
        rf'\g<1>{sha256}\g<2>',
        formula,
    )
    return formula


def update_resource(formula: str, name: str, url: str, sha256: str) -> str:
    return re.sub(
        rf'(resource "{re.escape(name)}" do\s+url ")[^"]+("\s+sha256 ")[^"]+(")',
        rf'\g<1>{url}\g<2>{sha256}\g<3>',
        formula,
        flags=re.DOTALL,
    )


def main() -> None:
    version = pypi_version(PACKAGE_NAME)
    print(f"Updating formula to v{version}")

    formula = FORMULA_PATH.read_text()

    # Main package
    url, sha256 = pypi_sdist(PACKAGE_NAME, version)
    formula = update_main_package(formula, url, sha256)
    print(f"  {PACKAGE_NAME} {version}")

    # Dependencies — parsed from formula, updated to latest
    for dep in parse_dependencies(formula):
        try:
            dep_version = pypi_version(dep)
            url, sha256 = pypi_sdist(dep, dep_version)
            formula = update_resource(formula, dep, url, sha256)
            print(f"  {dep} {dep_version}")
        except Exception as e:
            print(f"  WARNING: skipping {dep}: {e}", file=sys.stderr)

    FORMULA_PATH.write_text(formula)
    print(f"\nWritten to {FORMULA_PATH}")


if __name__ == "__main__":
    main()
