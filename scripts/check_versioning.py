"""Exercise Git-derived versions in disposable repositories and source archives."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from build.util import project_wheel_metadata
from packaging.version import Version

import build

ROOT = Path(__file__).resolve().parents[1]


def version(source: Path) -> Version:
    return Version(project_wheel_metadata(source, isolated=False)["Version"])


def without_git(command, cwd, extra_environ):
    environment = {**os.environ, **extra_environ, "PATH": ""}
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def main() -> None:
    if any(key.startswith("SETUPTOOLS_SCM_PRETEND_VERSION") for key in os.environ):
        raise SystemExit("Unset setuptools-scm version overrides to exercise Git inference")
    renderer = json.loads((ROOT / "src/pele_python/_vendor/manifest.json").read_text("utf-8"))
    release = renderer["version"]
    git = shutil.which("git")
    if git is None:
        raise SystemExit("Use the Pixi environment, which supplies Git for source versioning")

    with tempfile.TemporaryDirectory(prefix="pele-versioning-") as directory:
        temporary = Path(directory)
        source = temporary / "source"
        shutil.copytree(
            ROOT,
            source,
            ignore=shutil.ignore_patterns(
                ".git", ".pixi", "build", "dist", "__pycache__", ".pytest_cache", ".ruff_cache"
            ),
        )
        assert version(source) == Version("0.0.0.dev0")
        environment = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }

        def run_git(*arguments):
            subprocess.run(
                [
                    git,
                    "-c",
                    "user.name=Version Check",
                    "-c",
                    "user.email=version-check@example.invalid",
                    *arguments,
                ],
                cwd=source,
                env=environment,
                check=True,
                capture_output=True,
            )

        run_git("init", "--quiet")
        run_git("add", "--all")
        run_git("commit", "--quiet", "-m", "Versioning fixture")
        assert version(source).is_devrelease
        run_git("tag", f"v{release}")
        assert version(source) == Version(release)

        builder = build.ProjectBuilder(source)
        wheel = Path(builder.build("wheel", temporary / "tagged"))
        sdist = Path(builder.build("sdist", temporary / "tagged"))
        extracted = temporary / "extracted"
        with tarfile.open(sdist) as archive:
            archive.extractall(extracted, filter="data")
        archived_source = extracted / sdist.name.removesuffix(".tar.gz")
        archived_metadata = project_wheel_metadata(
            archived_source, isolated=False, runner=without_git
        )
        assert Version(archived_metadata["Version"]) == Version(release)
        rebuilt = Path(
            build.ProjectBuilder(archived_source, runner=without_git).build(
                "wheel", temporary / "rebuilt"
            )
        )
        assert (
            hashlib.sha256(wheel.read_bytes()).digest()
            == hashlib.sha256(rebuilt.read_bytes()).digest()
        )
        print(f"PASS: v{release} produces {release}; sdist preserves it without Git")

        readme = source / "README.md"
        readme.write_text(readme.read_text("utf-8") + "\nVersioning fixture.\n", "utf-8")
        assert version(source).is_devrelease
        run_git("add", "README.md")
        run_git("commit", "--quiet", "-m", "Wrapper fix fixture")
        development = version(source)
        assert development.public == f"{release}.post1.dev1", development
        revision = f"{release}.1"
        run_git("tag", f"v{revision}")
        assert version(source) == Version(revision)
        print(
            f"PASS: untagged/dirty builds are development versions; v{revision} yields {revision}"
        )
        run_git("commit", "--quiet", "--allow-empty", "-m", "Mismatched release fixture")
        run_git("tag", "v99.0.0")
        rejected = subprocess.run(
            [sys.executable, str(source / "scripts/check_package.py")],
            cwd=source,
            capture_output=True,
            text=True,
        )
        assert rejected.returncode != 0
        assert "Release tags must match bundled Pele" in rejected.stderr, rejected.stderr
        print("PASS: package checks reject a release tag that disagrees with bundled Pele")


if __name__ == "__main__":
    main()
