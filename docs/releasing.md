# Preparing a release

CI builds and validates artifacts. GitHub Releases are published manually with
the validated wheel, source distribution, and `SHA256SUMS`; CI does not publish
releases or upload to PyPI. The repository is
<https://github.com/CagtayFabry/pele-python>.

## Initial GitHub upload

The repository is hosted on GitHub, including `pixi.toml`, `pixi.lock`, `.github`,
the vendored bundle/license/manifest, tests, docs, and the example notebook.
Keep `.pixi`, local browser binaries, caches, `build`, and `dist` out of Git;
the repository's `.gitignore` already covers them. Use `main` as the default branch
so the documentation links resolve.

After the first upload:

1. Confirm all eight test jobs and the three quality/package/browser jobs pass.
   Remote Linux and Windows results cannot be established by local macOS tests.
2. Enable a branch rule requiring the **Required CI** status check. This aggregate
   fails when any required dependency fails, is skipped, or is cancelled. The
   workflow also handles merge queues through `merge_group`.
3. Confirm Actions and Dependabot are enabled. CI uses read-only repository
   permissions; the daily Pele updater uses Contents/Pull requests write access
   and needs Actions PR creation enabled. See [update automation setup](vendoring.md).
   Actions use exact version tags; publishing credentials are not required.
4. Download `distributions` and `browser-screenshots` from a successful workflow
   run if needed. Artifacts are retained for 14 days; they are not permanent release hosting.
5. Review README support claims against the actual successful CI combinations.

## Building a candidate

1. Choose a Git tag matching the bundled Pele version, for example `v1.12.0`.
   The optional fourth release component identifies Python integration fixes:
   `v1.12.0.1` still bundles Pele 1.12.0. The package check rejects final versions
   whose first three components disagree with the vendor manifest. Neither
   `pyproject.toml` nor `pixi.toml` needs a package-version edit.
2. Update the changelog and relevant compatibility results. Preserve the wrapper's
   MIT license and bundled upstream notices.
3. Commit the candidate changes and, when ready, create the chosen tag on that
   commit. A clean checkout of `v1.12.0` builds version `1.12.0`. CI fetches full
   history and tags (`fetch-depth: 0`) before installing the local package.
4. Move any old distributions out of `dist`, then run:

   ```sh
   pixi lock
   pixi run --locked test
   pixi run --locked lint
   pixi run --locked workflow-check
   pixi run --locked gate
   pixi run --locked version-check
   pixi run --locked -e browser browser-install
   pixi run --locked -e browser browser-check
   pixi run --locked build
   pixi run --locked package-check
   pixi run --locked acceptance
   ```

5. Review the flowchart, sequence, and large-tree screenshots. Confirm the source
   archive contains the example and all rendering assets, and retain the wheel,
   sdist, and `SHA256SUMS` together. CI performs package checks on Linux as well.
6. Require a successful full CI run for the tagged candidate before distributing it.

The macOS test job uses `macos-latest` (ARM64). An existing run keeps the runner
configuration it started with. If a tag needs validation using an updated CI
workflow, dispatch the workflow from `main` with the tag as its source ref:

```sh
gh workflow run ci.yml --ref main -f source_ref=v1.13.0
```

All test, quality, packaging, and browser jobs then check out that exact source
ref. This leaves the existing release tag unchanged.

`hatch-vcs` resolves the package version during builds. Commits after a tag use
development versions based on that tag (for example `1.12.0.post1.dev1+g...`),
without guessing the next Pele release. Dirty checkouts also produce development
versions. Untagged Git repositories use a development version from their history.
A plain source copy with no Git or archive metadata falls back to `0.0.0.dev0`;
this is a local development placeholder, not a release.

An sdist records its resolved version in `PKG-INFO`, so rebuilding it needs no
Git executable or `.git` directory. Wheel installation needs neither Git nor
the build-time versioning plugin. When inspecting an editable installation,
`importlib.metadata.version('pele-python')` reports its version at installation
time; reinstall through Pixi after moving to a different tag if that installed
metadata must be refreshed.

An offline consumer needs both the wrapper wheel and its matching runtime wheel.
The wrapper's pure Python wheel alone is not a complete offline wheelhouse.

## Future publication decisions

Check PyPI name availability and ownership before planning a package-index release.
GitHub Releases hold permanent, validated distribution artifacts.
For eventual PyPI automation, configure a dedicated protected publishing
environment and [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
Publishing authorization and automation are separate from this preparation.
