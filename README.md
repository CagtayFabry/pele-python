# pele-python

Render Mermaid diagrams to SVG from Python, including SVG display in notebooks.
This independent integration vendors **Pele 1.13.0** and depends on
**quickjs-ng 0.17.0.2**. No Node.js, npm, browser, or notebook setup cell is needed.
Rendering is synchronous and works offline after installation.

The distribution is `pele-python`; the Python import is `pele_python`.
This replaces the working names `pele-svg` / `pele_svg` in the specification.
The package has not been published to PyPI; check name availability before
publishing there.

## Installation

Python 3.10 or newer is required. For local development with Pixi:

```sh
pixi install
pixi run test
pixi run build
```

Use the built wheel in another Pixi workspace:

```toml
[pypi-dependencies]
pele-python = { path = "/path/to/pele-python/dist/pele_python-1.13.0-py3-none-any.whl" }
```

In a `pyproject.toml` Pixi project, use `[tool.pixi.pypi-dependencies]` instead.
A source path also works: `pele-python = { path = "/path/to/pele-python" }`.
The wheel filename above corresponds to the `v1.13.0` release candidate.
GitHub release wheels can be downloaded and installed using their local path;
an index dependency such as `pele-python = "==1.13.0"` requires a separate PyPI
publication.
Other Python installers can install the same wheel and resolve its declared
runtime dependency. Offline installation additionally needs the matching
quickjs-ng wheel; the pure Python wrapper wheel does not contain that binary.

## Usage

```python
from pathlib import Path
from pele_python import render, render_svg, PeleError

source = 'flowchart LR\n  A["Input 東京"] --> B[Output]'
svg = render_svg(source)
Path("diagram.svg").write_text(svg, encoding="utf-8")

diagram = render(source, fontSize=20, fontFamily="sans-serif")
diagram  # SVG-capable notebook frontends display this automatically
assert diagram._repr_svg_() == diagram.svg
```

`render_svg(source: str, **options) -> str` returns plain SVG markup.
`render(source: str, **options) -> Diagram` renders once, stores `.svg`, and
implements `_repr_svg_()` without importing IPython or Jupyter. Displaying an
existing diagram does not render it again. The example notebook is
[`examples/quickstart.ipynb`](examples/quickstart.ipynb), including a generated
63-node binary tree with 62 edges.

Options use [Pele's existing JavaScript names](https://pele.run/api), including
`fontSize`, `fontFamily`, `responsive`, `maxWidth`, `autoDirection`, and `now`.
Defaults come from Pele. Only `idPrefix` changes: each omitted prefix becomes
a unique `pele_...` value so inline diagrams can coexist. An explicit prefix
is forwarded unchanged; use unique letters, digits, hyphens, and underscores
for inline diagrams. For reproducible output, fix both `idPrefix` and `now`
(milliseconds since the Unix epoch):

```python
svg = render_svg(source, idPrefix="example", now=1767225600000,
                 responsive=False, autoDirection=False)
```

Options must be finite JSON data: strings, booleans, numbers, `None`, lists
(or tuples), and dictionaries with string keys. JavaScript number precision
applies. Non-finite numbers, circular references, and unsupported Python
objects are rejected before JavaScript runs. Callback options `measurer`,
`icons`, and `math` are unsupported (they may be omitted or `None`).
Source and labels are passed as data, never evaluated as JavaScript.

```python
try:
    render_svg("this is not a diagram")
except PeleError as error:
    print(error.message, error.code, error.line, error.column, error.snippet)
```

Pele diagnostics are preserved; absent fields are `None`. Pele may supply
zero positions or an empty snippet when no location is available. Display
errors as plain text. Invalid Python inputs raise `TypeError` or `ValueError`;
runtime/asset failures raise `RuntimeError` with context.

## Compatibility and limitations

Locally verified: **CPython 3.10–3.15 on macOS ARM64**, including all six required
diagram types, threads, installed-wheel offline rendering, and Pixi installation.
The runtime publishes wheels for several other platforms, but those are not
claimed as verified wrapper platforms until the integration checks pass there.
In particular, the pinned runtime has **no Intel macOS wheel**; a compiler-free
installation is not available there. See [compatibility results](docs/compatibility.md)
for exact versions, sizes, checks, and the Pixi test environments.

The built-in text-width estimator runs without canvas. Font metrics are
approximate; the viewing environment must supply fonts and may render text
differently. Fonts and additional math typesetters are not embedded. External
image URLs may remain SVG references; this wrapper never fetches or embeds
them. Viewing those SVG references is the frontend's responsibility.
Pele's syntax, limits, escaping, and SVG security behavior apply; see
[upstream security documentation](https://pele.run/security).

A fresh QuickJS context is created and released on each call, including calls
from different Python threads. Only the bundled JavaScript text is cached.
There is no CLI, backend-selection API, widget, resize handler, arbitrary
JavaScript execution, or raster/PDF conversion.

## Maintenance

```sh
pixi run lint
pixi run test
pixi run gate
pixi run version-check
pixi run build
pixi run package-check
pixi run acceptance
```

To check npm for a newer Pele release, run `pixi run pele-check`. To vendor it
and update the README/changelog, run `pixi run pele-bump`. The daily GitHub
workflow opens an update PR when a newer release is available. See
[vendoring and update automation](docs/vendoring.md) for repository setup.

The optional local browser checks use their own Pixi environment. They serve
only the generated preview on loopback and write screenshots to `build/browser`:

```sh
pixi run -e browser browser-install
pixi run -e browser browser-check
```

The first command downloads Chromium's headless shell into `.pixi/browsers`.
This is development tooling; installing or using `pele-python` needs no browser.
The shared Pixi `test` feature supplies pytest and the editable package installation
to `py310`, `py311`, `py312`, `py313`, `py314`, and `py315`. For example:

```sh
pixi run --locked -e py310 test
pixi run --locked -e py315 test
```

GitHub CI runs the complete suite on Linux for all six versions, and on Windows
x64 and macOS ARM64 with Python 3.14. Lint/format, workflow validation, the runtime
gate, package validation, isolated installation/sdist rebuilding, and one headless
browser job feed the aggregate `Required CI` check. Other platform/version pairs
remain unverified until tested. CI artifacts include distributions, checksums,
and browser screenshots; publication is a separate step.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md),
[CHANGELOG.md](CHANGELOG.md), and the [release preparation guide](docs/releasing.md).

Package versions are derived from Git tags through `hatch-vcs`. A clean
`v1.13.0` tag builds version `1.13.0`; `v1.13.0.1` is a wrapper revision bundling
the same Pele release. Untagged commits and dirty working trees produce development
versions. A source tree with no Git or archive metadata uses `0.0.0.dev0` for
local development. Built source distributions preserve their resolved version
and can rebuild without Git. Git and the versioning plugin are build/development
tools; installing a wheel does not require them.

Builds use only Python tooling and the checked-in rendering assets. Neither
installation nor import downloads assets, runs subprocesses, or compiles
anything in this wrapper. See [vendoring instructions](docs/vendoring.md) for
the separate maintainer-only artifact verification procedure.

The wrapper and vendored Pele are MIT-licensed. Pele's original license and
SHA-256 vendor manifest are included in both the wheel and source distribution.
