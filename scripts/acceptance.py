"""Check release artifacts and install a built wheel using only Pixi."""

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

import build
from check_package import ROOT, artifact_paths, inspect_sdist, inspect_wheel, project_metadata


def main() -> None:
    wheel, sdist = artifact_paths()
    inspect_wheel(wheel)
    prefix = inspect_sdist(sdist)
    pixi = shutil.which("pixi")
    if pixi is None:
        raise SystemExit("Pixi must be available to install the clean test environment")
    sandbox = shutil.which("sandbox-exec") if sys.platform == "darwin" else None
    network_profile = "(version 1) (allow default) (deny network*)"

    def offline_build_runner(command, cwd, extra_environ):
        environment = {**os.environ, **extra_environ}
        if sandbox:
            command = [sandbox, "-p", network_profile, *command]
        subprocess.run(command, cwd=cwd, env=environment, check=True)

    with tempfile.TemporaryDirectory(prefix="pele-python-acceptance-") as directory:
        temporary = Path(directory)
        source_dir = temporary / "source"
        source_dir.mkdir()
        with tarfile.open(sdist) as archive:
            archive.extractall(source_dir, filter="data")

        # Build using the existing Pixi build tools, with no dependency installs,
        # no JS tools, and no retrieval of assets. Hatchling uses no network.
        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = ""
        try:
            rebuilt = Path(
                build.ProjectBuilder(source_dir / prefix, runner=offline_build_runner).build(
                    "wheel", temporary / "rebuilt"
                )
            )
        finally:
            os.environ["PATH"] = original_path
        inspect_wheel(rebuilt)
        assert (
            hashlib.sha256(rebuilt.read_bytes()).digest()
            == hashlib.sha256(wheel.read_bytes()).digest()
        ), "Rebuilt wheel differs from the release wheel"
        print("PASS: identical wheel rebuilt from sdist with empty PATH and no installs")

        # A new Pixi workspace installs the wheel and only its declared runtime.
        # Run outside both source trees with Python's isolated import mode.
        workspace = temporary / "consumer"
        workspace.mkdir()
        platform_name = subprocess.check_output([pixi, "info", "--json"], cwd=ROOT, text=True)
        platform_name = json.loads(platform_name)["platform"]
        manifest = workspace / "pixi.toml"
        manifest.write_text(
            '[workspace]\nname = "pele-consumer"\nchannels = ["conda-forge"]\n'
            f'platforms = ["{platform_name}"]\n\n'
            f'[dependencies]\npython = "{sys.version_info.major}.{sys.version_info.minor}.*"\n\n'
            "[pypi-dependencies]\n"
            f"{project_metadata()['name']} = {{ path = {json.dumps(str(wheel))} }}\n",
            encoding="utf-8",
        )
        for name, source in (
            ("smoke.py", ROOT / "scripts/installed_smoke.py"),
            ("diagrams.json", ROOT / "tests/fixtures/diagrams.json"),
        ):
            shutil.copyfile(source, workspace / name)
        subprocess.run(
            [pixi, "install", "--manifest-path", str(manifest)], cwd=workspace, check=True
        )
        smoke_command = ["python", "-I", "smoke.py", "diagrams.json"]
        smoke_environment = os.environ.copy()
        if sandbox:
            smoke_command = [sandbox, "-p", network_profile, *smoke_command]
            smoke_environment["PELE_ACCEPTANCE_OS_NETWORK_BLOCKED"] = "1"
        subprocess.run(
            [
                pixi,
                "run",
                "--manifest-path",
                str(manifest),
                "--frozen",
                "--offline",
                *smoke_command,
            ],
            cwd=workspace,
            env=smoke_environment,
            check=True,
        )
        print("PASS: minimal Pixi consumer installs the wheel without setup tasks")


if __name__ == "__main__":
    main()
