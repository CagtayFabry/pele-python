# Minimal Python wrapper for Pele

Status: proposed specification; implementation and runtime compatibility are not yet verified.

## Objective

Provide a Python package that renders Mermaid source to SVG using [Pele](https://pele.run/). Installing the package with a Python package installer, including Pixi's PyPI dependency support, must install everything needed to render diagrams. Users must not install Node.js, run npm, download a browser, or execute setup commands in a notebook.

Working names: distribution `pele-svg`, import `pele_svg`. Name availability must be checked before publishing.

## Packaging model

Ship a standard Python wheel containing:

- The Python wrapper and type information.
- An exact, vendored release of Pele's complete `dist/pele.global.js` bundle.
- Pele's MIT license and a vendor manifest recording its version, source URL, and SHA-256 digest.

Declare an embedded JavaScript runtime as a normal Python dependency. The preferred candidate is [`quickjs-ng`](https://pypi.org/project/quickjs-ng/), which supplies QuickJS through Python wheels and exposes `quickjs.Context`.

This means one Python installation command resolves the wrapper and its runtime dependency. It does **not** mean the wrapper wheel physically contains every dependency or can be installed offline by itself. Offline installation would additionally require the matching runtime wheel and any other declared dependencies.

Use Python 3.10 or newer, subject to the selected runtime's supported versions. Do not claim support for a platform unless its runtime wheel is available and the wrapper passes integration tests there. In particular, the reviewed quickjs-ng release lists macOS ARM64 wheels; Intel macOS support must be established separately.

The wrapper itself should be a pure-Python wheel with package data; platform-specific binaries belong to the runtime dependency. Neither installation nor import may trigger downloads, compilation, or subprocesses initiated by this wrapper. On unsupported platforms, document that a runtime wheel is unavailable rather than claiming a compiler-free installation.

## Runtime feasibility gate

Before implementing the public package, prove that an unmodified, pinned Pele global bundle can load and render representative diagrams inside quickjs-ng without a DOM, browser, or Node globals.

Check flowchart, sequence, class, state, ER, and Gantt diagrams, including Unicode labels. Exercise regular-expression and other JavaScript features used by the bundle. Pele documents a built-in text-width estimator for environments without canvas, so no browser-based font measurement should be required.

If QuickJS cannot run the bundle reliably, evaluate [`mini-racer`](https://pypi.org/project/mini-racer/) as the fallback embedded runtime. Select one runtime for the first release; do not implement a backend-selection framework. Record the compatibility results and dependency size before choosing.

## Public API

Expose only these initial entry points:

```python
from pele_svg import render, render_svg, PeleError

# An SVG string suitable for saving or passing to another library.
svg = render_svg("flowchart LR\n  A[Input] --> B[Output]")

# An object displayed automatically as SVG by an SVG-capable notebook frontend.
diagram = render("flowchart LR\n  A[Input] --> B[Output]")
diagram

# Access the rendered markup explicitly.
assert isinstance(diagram.svg, str)
```

Required signatures:

```python
def render_svg(source: str, **options) -> str: ...
def render(source: str, **options) -> Diagram: ...
```

`Diagram` must contain the rendered `svg` string and implement `_repr_svg_()` returning that string. Constructing it through `render()` performs rendering once; displaying it must not re-render. A short plain-text representation is sufficient outside an SVG-capable frontend.

The package must not require IPython or Jupyter. Notebook integration uses the rich-display protocol directly. File export uses ordinary Python file APIs; a separate save method is unnecessary for the first release.

## Options and errors

Forward JSON-serializable options to Pele using its existing JavaScript option names, such as `fontSize`, `fontFamily`, `responsive`, `maxWidth`, `autoDirection`, and `idPrefix`. Avoid maintaining a second naming scheme or duplicating the full upstream option schema.

- Preserve Pele's option defaults except for generating a unique `idPrefix` when the caller omits it. This prevents collisions between diagrams displayed in one notebook.
- Honor an explicit `idPrefix`; callers can combine it with a fixed `now` value when they need reproducible output.
- Reject non-string source with `TypeError`.
- Reject options that cannot be represented as finite JSON data before entering JavaScript. Do not accept raw JavaScript or Python callbacks for options such as `measurer`, `icons`, or `math` in the initial release.
- Translate upstream parse/render failures into `PeleError`, preserving `message`, `code`, `line`, `column`, and `snippet` when supplied by Pele. Missing diagnostic fields should be `None`.
- Distinguish failure to load or execute the bundled runtime from a diagram syntax error; runtime failures should raise `RuntimeError` with useful context.

Sources and labels must cross the bridge as data, using a callable bridge and/or JSON encoding. Never interpolate unescaped Mermaid source into executable JavaScript.

## Internal design

Keep a single private runtime adapter responsible for loading the bundled asset, invoking Pele's synchronous `render()` function, and returning its SVG or serialized error details.

For the first implementation, create a fresh runtime context for each render call and release it afterward. This keeps threading and lifecycle behavior simple. The bundle text may be cached in Python; live JavaScript contexts must not be shared across threads. Optimize context reuse only if measurements justify the added lifecycle management.

Load the bundle through `importlib.resources`, independent of the current working directory. Both a wheel installation and a source-distribution build must contain all rendering assets. Builds from the source distribution must not need npm or retrieve missing assets.

Rendering must work without network access. Source-specified external image URLs may remain SVG references; the wrapper does not fetch or embed those images. Exact font metrics, embedded fonts, and additional math typesetters are outside the initial scope.

## Vendoring and licensing

Pin one published Pele release rather than fetching `latest` or using a moving version range. Pele 1.12.0 is the candidate reviewed for this specification; confirm its published artifacts during implementation.

Provide a maintainer-only vendoring procedure that downloads the published npm artifact, verifies its registry integrity, copies the global bundle and license, and updates the vendor manifest. Users and package builds must never run this procedure automatically.

Preserve upstream license notices and identify the wrapper as an independent Python integration. Choose the wrapper's own license before publication. Include the upstream license in both wheel and source distribution.

Pin the runtime version validated by the initial release. Expand the supported range only after testing other versions.

## Pixi integration

Once published, a project should need only a normal PyPI dependency:

```toml
[pypi-dependencies]
pele-svg = "==0.1.0"
```

For a project configured in `pyproject.toml`, the equivalent table is `[tool.pixi.pypi-dependencies]`. Before publication, use Pixi's local-wheel/path dependency support.

No Node.js dependency, npm manifest, activation script, or setup task should be necessary. Jupyter remains a dependency of the user's notebook environment, rather than of the renderer.

## Acceptance tests

The implementation is complete when:

1. A built wheel installs into a clean supported Python environment with its declared dependencies, and renders from a directory outside the source checkout.
2. Rendering succeeds with Node.js and npm absent from `PATH` and network access disabled after installation.
3. The feasibility-gate diagram types produce valid SVG containing expected labels. At least a flowchart and sequence diagram receive visual inspection in a notebook or browser, rather than relying only on XML validity.
4. Unicode, quotes, backslashes, newlines, and markup-like labels pass safely through the Python–JavaScript boundary, subject to Mermaid's label syntax.
5. Two inline outputs receive distinct default SVG IDs; an explicit prefix is preserved. Serializable options demonstrably affect output.
6. Invalid Mermaid produces useful `PeleError` diagnostics, and a later valid render still succeeds. Invalid Python inputs produce the specified Python exceptions.
7. `Diagram` displays through `_repr_svg_()` without importing IPython, while `render_svg()` returns a plain string.
8. Independent render calls work from multiple Python threads without sharing a runtime context.
9. Wheel and source distribution contain the bundle, vendor manifest, and license; rebuilding a wheel from the source distribution requires no JavaScript toolchain.
10. A minimal Pixi project can install the wheel and render a diagram without additional setup tasks.

## Deliverables and scope

Deliver the source package, a built wheel and source distribution, tests, a small example notebook, vendoring instructions, and a README covering installation, API usage, platform support, and known font-metric limitations.

Exclude a CLI, browser widgets, automatic resize handling, raster/PDF conversion, arbitrary JavaScript execution, custom math/icon callbacks, and publishing to a package index from this initial implementation.

## Primary references

- [Pele API and non-browser text measurement](https://pele.run/api)
- [Pele package metadata](https://github.com/obsidianmd/pele/blob/main/package.json)
- [Pele license](https://github.com/obsidianmd/pele/blob/main/LICENSE)
- [quickjs-ng runtime and available wheels](https://pypi.org/project/quickjs-ng/)
- [quickjs-ng API and threading guidance](https://github.com/genotrance/quickjs-ng)
- [MiniRacer fallback runtime](https://pypi.org/project/mini-racer/)
- [Pixi dependency manifest](https://pixi.prefix.dev/latest/reference/pixi_manifest/)
