"""Check npm for a newer Pele release or vendor it for a reviewable update."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from packaging.version import Version
from vendor_pele import ROOT, download, vendor


def current_version() -> str:
    manifest = ROOT / "src/pele_python/_vendor/manifest.json"
    return json.loads(manifest.read_text("utf-8"))["version"]


def latest_version() -> str:
    metadata = json.loads(download("https://registry.npmjs.org/pele/latest"))
    return str(Version(metadata["version"]))


def check() -> None:
    current, latest = current_version(), latest_version()
    result = {
        "current": current,
        "latest": latest,
        "update_available": Version(latest) > Version(current),
    }
    print(json.dumps(result, indent=2))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in result.items():
                stream.write(f"{key}={str(value).lower()}\n")


def bump(target: str | None = None) -> None:
    current = current_version()
    target = target or latest_version()
    if Version(target) <= Version(current):
        print(f"Pele {current} is already at or above {target}; nothing to update.")
        return
    vendor(target)
    readme = ROOT / "README.md"
    readme.write_text(readme.read_text("utf-8").replace(current, target), "utf-8")
    changelog = ROOT / "CHANGELOG.md"
    changelog.write_text(
        changelog.read_text("utf-8").replace(
            "## Unreleased\n",
            f"## Unreleased\n\n- Update bundled Pele from {current} to {target}.",
            1,
        ),
        "utf-8",
    )
    print(f"Updated Pele {current} -> {target}. Review the changes and run the Pixi checks.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Compare the bundled version with npm's latest release")
    update = commands.add_parser("bump", help="Vendor the latest or specified newer release")
    update.add_argument("--version", help="Exact newer release; defaults to npm's latest")
    arguments = parser.parse_args()
    if arguments.command == "check":
        check()
    else:
        bump(arguments.version)
