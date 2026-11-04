# Contributing

Use [Pixi](https://pixi.sh/) **0.77.0**, the version pinned in CI. The committed
`pixi.lock` resolves the development tools and test environments for Linux x64,
Windows x64, and macOS ARM64. Package installation is managed through Pixi.

```sh
pixi install --locked
pixi run --locked test
pixi run --locked lint
pixi run --locked workflow-check
pixi run --locked gate
pixi run --locked version-check
```

The shared `test` feature owns pytest, Git for source version inference, the editable local package installation,
and the `test` task. Each `py310` through `py315` environment combines it with
one Python version, without inheriting the development environment's packages:

```sh
pixi run --locked -e py310 test
pixi run --locked -e py311 test
pixi run --locked -e py312 test
pixi run --locked -e py313 test
pixi run --locked -e py314 test
pixi run --locked -e py315 test
```

The `dev` environment retains JupyterLab and ipykernel for notebook work:

```sh
pixi run --locked -e dev jupyter lab examples/quickstart.ipynb
```

The default development environment uses Python 3.12. CI runs the complete
suite on Linux with Python 3.10–3.15, and on Windows x64 and macOS ARM64 with
Python 3.14. A lockfile solve alone does not establish runtime compatibility;
the corresponding CI tests must pass. Intel macOS is outside the supported matrix.

## Rendering and package checks

```sh
pixi run --locked -e browser browser-install
pixi run --locked -e browser browser-check
pixi run --locked build
pixi run --locked package-check
pixi run --locked acceptance
```

The browser installation is optional development tooling. It downloads a
workspace-local Chromium headless engine, uses a temporary profile, and writes
screenshots/reporting to `build/browser`. It does not use your system browser.
On Linux, the host needs the shared libraries required by Playwright's Chromium;
the CI workflow uses GitHub's Ubuntu 24.04 runner image.

The package check validates both distributions, their metadata, licenses,
vendored assets, and the version resolved by the build backend, then writes `dist/SHA256SUMS`. The
acceptance check rebuilds an identical wheel from the sdist and installs it in
a separate Pixi workspace before running isolated, offline rendering checks.
Old-version distributions left in `dist` cause validation to fail; move them out
before building a new release version.

## Changing dependencies or bundled Pele

Change dependencies through `pixi add`, or edit the manifest and run `pixi lock`.
Commit the updated manifest and lockfile together. Use ordinary CPython builds;
the selected QuickJS stable-ABI wheels are not free-threaded Python wheels.

Runtime dependencies belong in `pyproject.toml`. Keep the runtime pin exact until
the full test and acceptance checks validate another version. Keep the Hatchling
version in `pixi.toml` aligned with `[build-system]` so builds use the tested backend.
The same applies to the pinned `hatch-vcs` plugin. Package versions come from
Git tags; neither manifest contains a manually maintained package version.
Use a full clone with tags. `pixi run version-check` verifies clean tags,
development builds, wrapper revision tags, and Git-free sdist rebuilding in
disposable repositories. See [the release guide](docs/releasing.md) for the tag policy.
Review [vendoring instructions](docs/vendoring.md) before updating the bundled JavaScript.

GitHub Actions dependencies use exact version tags, with monthly Dependabot
updates. Update the pinned Pixi version in CI and this guide together. Conda/PyPI
lockfile changes are reviewed manually with `pixi update`; package builds and
runtime installation never run the vendoring procedure.

## Pull requests

Describe the concrete problem, resulting behavior, and relevant validation.
Add meaningful regression coverage for behavior changes and update the example
notebook when its demonstrated API changes. Record user-visible changes under
`Unreleased` in [CHANGELOG.md](CHANGELOG.md). Report vulnerabilities using
[SECURITY.md](SECURITY.md).

All CI jobs must pass. The aggregate **Required CI** check covers the eight test
jobs, lint/format and workflow validation, runtime feasibility, package checks,
and the local headless browser check.
