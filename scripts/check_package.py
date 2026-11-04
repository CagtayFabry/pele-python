"""Validate the current wheel/sdist, metadata, licenses, and vendored assets."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from email.parser import BytesParser
from functools import cache
from pathlib import Path

import tomllib
from build.util import project_wheel_metadata
from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("pele.global.js", "manifest.json", "LICENSE")


@cache
def project_metadata(root: Path = ROOT) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]
    # Ask the configured backend for the VCS-derived version. Use the current
    # Pixi build tools; metadata inspection must never install dependencies.
    project["version"] = str(Version(project_wheel_metadata(root, isolated=False)["Version"]))
    return project


def artifact_paths(root: Path = ROOT) -> tuple[Path, Path]:
    project = project_metadata(root)
    name = re.sub(r"[-_.]+", "_", project["name"]).lower()
    prefix = f"{name}-{Version(project['version'])}"
    wheel = root / "dist" / f"{prefix}-py3-none-any.whl"
    sdist = root / "dist" / f"{prefix}.tar.gz"
    if not wheel.is_file() or not sdist.is_file():
        raise SystemExit("Current artifacts are missing; run: pixi run build")
    stale = (set((root / "dist").glob("*.whl")) | set((root / "dist").glob("*.tar.gz"))) - {
        wheel,
        sdist,
    }
    if stale:
        raise SystemExit(f"Remove stale distributions before validation: {sorted(map(str, stale))}")
    return wheel, sdist


def inspect_metadata(data: bytes) -> None:
    project = project_metadata()
    metadata = BytesParser().parsebytes(data)
    assert metadata["Name"] == project["name"]
    assert metadata["Version"] == str(Version(project["version"]))
    assert metadata["Requires-Python"] == project["requires-python"]
    assert metadata["License-Expression"] == project["license"]
    assert set(metadata.get_all("License-File", [])) == set(project["license-files"])
    assert {str(Requirement(value)) for value in metadata.get_all("Requires-Dist", [])} == {
        str(Requirement(value)) for value in project["dependencies"]
    }
    assert set(metadata.get_all("Project-URL", [])) == {
        f"{label}, {url}" for label, url in project["urls"].items()
    }
    assert set(metadata.get_all("Classifier", [])) == set(project["classifiers"])


def inspect_wheel(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for asset in ASSETS:
            name = f"pele_python/_vendor/{asset}"
            assert archive.read(name) == (ROOT / "src" / name).read_bytes(), name
        assert "pele_python/py.typed" in names
        metadata_path = next(name for name in names if name.endswith(".dist-info/METADATA"))
        inspect_metadata(archive.read(metadata_path))
        license_prefix = metadata_path.removesuffix("METADATA") + "licenses/"
        for license_path in project_metadata()["license-files"]:
            assert archive.read(license_prefix + license_path) == (ROOT / license_path).read_bytes()
        assert not any(name.endswith((".so", ".dll", ".dylib", ".exe")) for name in names)
        wheel_metadata = archive.read(metadata_path.removesuffix("METADATA") + "WHEEL")
        assert b"Root-Is-Purelib: true" in wheel_metadata
        assert b"Tag: py3-none-any" in wheel_metadata
    print(f"PASS: pure Python wheel contents and metadata ({wheel.stat().st_size:,} bytes)")


def inspect_sdist(sdist: Path) -> str:
    prefix = sdist.name.removesuffix(".tar.gz")
    with tarfile.open(sdist) as archive:
        for asset in ASSETS:
            relative = f"src/pele_python/_vendor/{asset}"
            member = archive.extractfile(f"{prefix}/{relative}")
            assert member is not None
            assert member.read() == (ROOT / relative).read_bytes()
        for relative in (
            *project_metadata()["license-files"],
            "examples/quickstart.ipynb",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CHANGELOG.md",
        ):
            assert f"{prefix}/{relative}" in archive.getnames(), relative
        metadata = archive.extractfile(f"{prefix}/PKG-INFO")
        assert metadata is not None
        inspect_metadata(metadata.read())
    print(f"PASS: source distribution contents and metadata ({sdist.stat().st_size:,} bytes)")
    return prefix


def main() -> None:
    version = Version(project_metadata()["version"])
    vendor = json.loads((ROOT / "src/pele_python/_vendor/manifest.json").read_text("utf-8"))
    if not version.is_prerelease:
        assert version.release[:3] == Version(vendor["version"]).release, (
            "Release tags must match bundled Pele, with an optional fourth wrapper revision"
        )
    wheel, sdist = artifact_paths()
    inspect_wheel(wheel)
    inspect_sdist(sdist)
    subprocess.run(
        [sys.executable, "-m", "twine", "check", "--strict", str(wheel), str(sdist)], check=True
    )
    checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (wheel, sdist)
    }
    (ROOT / "dist/SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in checksums.items()), "utf-8"
    )
    print("PASS: strict package metadata validation; wrote dist/SHA256SUMS")


if __name__ == "__main__":
    main()
