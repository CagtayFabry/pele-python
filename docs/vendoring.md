# Vendoring Pele

This is a maintainer procedure. Installing, importing, rendering, or building
the Python package must never invoke it. No Node.js or npm installation is used.

## Checking and bumping

```sh
pixi run pele-check
pixi run pele-bump
```

`pele-check` compares the manifest's version with npm's `latest` release and
prints `current`, `latest`, and `update_available`. `pele-bump` vendors a newer
release using the existing integrity verification, updates README version
references, and adds an entry under `Unreleased` in the changelog. Both an
up-to-date check and a bump to the already bundled version are harmless no-ops.
To choose a particular newer release, use `pixi run pele-bump --version 1.13.0`.
The package version remains derived from Git tags; bumping the bundle creates no tag.

## Daily update pull requests

`.github/workflows/update-pele.yml` checks npm daily at **05:23 UTC** and can also
be run manually with `workflow_dispatch`. A newer release produces a branch
`updates/pele-VERSION` and an update PR. Repeated checks reuse the PR for that
version. Nothing is committed when the bundled version is current.

After uploading the workflow, enable **Allow GitHub Actions to create and approve
pull requests** under the repository's Actions settings. The workflow uses
`GITHUB_TOKEN` by default. GitHub may require approval before CI runs on these
bot-created PRs. For fully automatic CI, optionally provide a fine-grained PAT
or GitHub App token as `PELE_UPDATE_TOKEN`, with repository Contents and Pull
requests write permissions. See [GitHub's workflow-trigger rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow).

The workflow opens PRs for review; it does not merge or publish releases.
Review the normal CI checks and browser artifacts before merging an update.

## Vendoring a specific published artifact

1. Choose an exact published npm `pele` version and review its license and API.
2. In the Pixi development environment, run:

   ```sh
   pixi run python scripts/vendor_pele.py --version 1.12.0
   ```

3. Review `src/pele_python/_vendor/manifest.json` and the asset/license changes.
   The script downloads version-specific registry metadata and its HTTPS npm
   tarball, verifies the full archive against npm's SHA-512 integrity, checks
   the archived package identity/version/MIT license, and reads only the exact
   global bundle and license members. It never extracts arbitrary archive paths.
   The bundle is copied byte-for-byte. The manifest records the source URL,
   npm integrity, archive SHA-256, and each asset's SHA-256 and byte size.
   This detects corrupted/mismatched downloads; it is not a separate publisher
   signature or provenance attestation verification.
4. Run `pixi run gate` before changing the public package. The gate creates
   fresh QuickJS contexts with no DOM, Node, fetch, canvas, or other host shims
   and renders the six representative diagram fixtures.
5. Run `pixi run test`, `pixi run lint`, `pixi run preview`, `pixi run build`,
   `pixi run package-check`, and `pixi run acceptance`. Also run the tests in the
   `py310` through `py315` Pixi environments. Run `pixi run -e browser browser-install` and
   `pixi run -e browser browser-check`, then visually inspect at least the
   flowchart and sequence screenshots in `build/browser`.
6. Record the results and sizes in `docs/compatibility.md`. Update version pins,
   documentation, and the runtime bridge only when the checks justify doing so.

The Python wrapper's license is the repository's `LICENSE`; the unmodified
upstream license is `src/pele_python/_vendor/LICENSE`. Both ship in the wheel
and sdist. The runtime's binary and license are supplied by its own dependency
wheel. No files are retrieved during an sdist-to-wheel build.

The initial specification's package names are superseded by the user-requested
`pele-python` / `pele_python`. No package index publication is part of this work.
