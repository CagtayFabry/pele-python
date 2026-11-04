# Runtime compatibility

## Pele 1.13.0 release validation

On 2026-11-04, [GitHub CI for the merged Pele update](https://github.com/CagtayFabry/pele-python/actions/runs/41843387574)
passed all 45 integration tests in each of the eight supported combinations:
Linux x64 with Python 3.10–3.15, Windows x64 with Python 3.14, and macOS ARM64
with Python 3.14. The runtime remains pinned to quickjs-ng 0.17.0.2; the
unmodified Pele 1.13.0 global bundle is 733,670 bytes.

The lint/runtime gate, wheel and source distribution checks, clean consumer
installation, source archive rebuild, and headless browser checks also passed.
The browser check covers all six fixture diagram types and the 63-node tree.
Extra platform/version combinations resolved in the lockfile do not imply
tested support.

Flowchart, sequence, and large-tree screenshots were inspected for this update.
Their layout is intact. The Ubuntu runner's default fonts show missing-glyph
boxes for Japanese characters even though the SVG text retains the correct
Unicode labels. Viewers need suitable CJK fonts to display those characters.

## Initial Pele 1.12.0 validation

The initial compatibility results below use **quickjs-ng 0.17.0.2**, pinned exactly,
with the unmodified npm **Pele 1.12.0** global bundle. The currently bundled Pele
version is recorded in `src/pele_python/_vendor/manifest.json`; update PRs must
pass the normal CI checks before their compatibility is established.
MiniRacer was not needed because
QuickJS passed the feasibility gate; no fallback or backend framework is shipped.

The global bundle is 730,358 bytes. The CPython macOS ARM64 runtime wheel is
533,474 bytes compressed (`cp310-abi3-macosx_11_0_arm64`), about 521 KiB. It
has no additional Python runtime dependencies. These are distinct downloads;
installers resolve both in one install operation.

Primary references:

- [Pele 1.12.0 published metadata](https://registry.npmjs.org/pele/1.12.0)
- [Pele API and fallback text measurement](https://pele.run/api)
- [Pinned quickjs-ng release metadata and wheel list](https://pypi.org/pypi/quickjs-ng/0.17.0.2/json)
- [QuickJS Python API and context threading guidance](https://github.com/genotrance/quickjs-ng)
- [Pixi PyPI dependency specifications](https://pixi.prefix.dev/latest/reference/pixi_manifest/)

## Feasibility gate

The gate ran on macOS ARM64 with CPython 3.12.16. Each context first confirmed
that `document`, `window`, `process`, `require`, and `fetch` were undefined.
The entire bundle was evaluated without modifications or host polyfills.
All six fixtures produced valid SVG containing their expected Unicode labels:

| Diagram | Result | SVG characters | Context creation + load + render |
| --- | --- | ---: | ---: |
| Flowchart | Pass | 1,531 | 37 ms |
| Sequence | Pass | 2,701 | 38 ms |
| Class | Pass | 2,592 | 36 ms |
| State | Pass | 2,370 | 37 ms |
| ER | Pass | 2,958 | 35 ms |
| Gantt | Pass | 2,530 | 35 ms |

These timings are single local observations, not performance guarantees.
Bundle loading and six parser/layout paths exercise the regular expressions
and JavaScript features in the release. Unicode labels include accented Latin,
Japanese, and emoji text. The date-sensitive Gantt fixture fixes `now`.

QuickJS 0.17 can create rope strings whose direct conversion by the Python
binding raises `TypeError: Unknown quickjs tag: -6`. Serializing the SVG/error
envelope with `JSON.stringify` flattens the string and passes reliably through
the callable bridge. This affects the adapter, not the vendored bundle.
The integration suite exercises this path using real render results.

## Validation scope

The initial local checks covered macOS ARM64. Current cross-platform CI results
are recorded above.
The pinned runtime lists Linux, Windows, and macOS ARM64 wheels, including
the CPython stable ABI wheel used here. No Intel macOS wheel is published.
Python 3.10 is the minimum required by the runtime. Local validation on 2026-10-31:

| Pixi environment | Python | Platform | Integration suite |
| --- | --- | --- | --- |
| `py310` | CPython 3.10.22 | macOS ARM64 | 45 passed |
| `py311` | CPython 3.11.18 | macOS ARM64 | 45 passed |
| `py312` | CPython 3.12.16 | macOS ARM64 | 45 passed |
| `py313` | CPython 3.13.18 | macOS ARM64 | 45 passed |
| `py314` | CPython 3.14.10 | macOS ARM64 | 45 passed |
| `py315` | CPython 3.15.2 | macOS ARM64 | 45 passed |

All six environments inherit the shared Pixi `test` feature, which includes
pytest, the editable local package installation, and the test task. They use
ordinary CPython builds and the same exact runtime pin. The lockfile resolves
for Linux x64, Windows x64, and macOS ARM64.

The GitHub CI matrix contains eight full-suite jobs: Linux x64 with
Python 3.10–3.15, Windows x64 with Python 3.14, and macOS ARM64 with Python 3.14.
All eight jobs have passed remotely. Extra lockfile platform/version
combinations do not imply tested support. Python 3.10 is kept
as a legacy compatibility target after its upstream end of life.

The pure Python wheel is approximately 278 KiB compressed. Exact final artifact
sizes depend on documentation and the source archive's included development
files; `scripts/acceptance.py` prints both sizes. The vendored bundle and runtime
wheel byte sizes above are fixed for their pinned versions.

`pixi run acceptance` checks asset hashes and licenses in both archives,
rebuilds a byte-identical pure Python wheel from the sdist with an empty PATH,
and creates a minimal independent Pixi project that installs only the wheel
and its declared runtime. Its smoke test runs outside the checkout in isolated
Python mode, empties PATH, and blocks Python socket and subprocess APIs before
the first package import. On macOS, both the sdist build hooks and installed
smoke test additionally run under `sandbox-exec` with `(deny network*)`.
The smoke test verifies that the OS denies a loopback socket connection before
applying the Python audit guard. This passed locally. Other operating systems
use the Python audit guard only until an OS-specific sandbox is provided.
The embedded context has no networking API. No external image retrieval is
performed by the wrapper.

`pixi run preview` creates `build/preview.html` for visual inspection and the
small executed quickstart notebook. `pixi run python -m http.server 8765 --bind
127.0.0.1 --directory build` serves the preview for browser inspection.

## Local browser verification

The `browser` Pixi environment contains Playwright 1.64.1 as development tooling.
`pixi run -e browser browser-install` installs the matching Chromium headless
shell into the workspace's ignored `.pixi/browsers` directory. No browser is
installed by the wrapper, its build, or the default environment's tasks.

`pixi run -e browser browser-check` starts a temporary loopback-only HTTP server,
loads the six diagram-type SVG outputs and the 63-node tree example,
checks visible SVG dimensions and labels, verifies the tree's 63 nodes and 62 edges,
records JavaScript page errors, and writes screenshots and a JSON report under
`build/browser`. The server and browser shut down when the check ends.

Chromium **156.0.8078.4** displayed all six diagrams with no page errors.
The flowchart and sequence screenshots were visually inspected on 2026-10-30:
labels, including accented Latin, Japanese, and emoji, were readable; nodes,
arrows, lifelines, and message labels were positioned correctly without clipping.
The quickstart notebook contains SVG rich-display outputs from the same renderer.
