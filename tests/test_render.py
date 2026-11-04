import json
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from importlib import resources
from pathlib import Path

import pytest

import pele_python
from pele_python import PeleError, _runtime, render, render_svg

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/diagrams.json").read_text(encoding="utf-8")
)
SOURCE = "flowchart LR\n accTitle: Input and output\n A[Input] --> B[Output]"


def svg_root(svg):
    assert type(svg) is str
    root = ET.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert float(root.attrib["width"]) > 0
    assert float(root.attrib["height"]) > 0
    return root


@pytest.mark.parametrize("kind", FIXTURES)
def test_representative_diagrams(kind):
    fixture = FIXTURES[kind]
    root = svg_root(render_svg(fixture["source"], now=1767225600000))
    text = "".join(root.itertext())
    for label in fixture["labels"]:
        assert label in text


def test_notebook_display_renders_once_without_ipython(monkeypatch):
    ipython_modules = {name for name in sys.modules if name.startswith("IPython")}
    diagram = render(SOURCE)

    def unexpected_render(*args, **kwargs):
        pytest.fail("rich display must not re-render")

    monkeypatch.setattr(_runtime, "render_svg", unexpected_render)
    assert diagram._repr_svg_() is diagram.svg
    assert diagram._repr_svg_() == diagram.svg
    assert "Diagram(" in repr(diagram)
    assert len(repr(diagram)) < 80
    assert ipython_modules == {name for name in sys.modules if name.startswith("IPython")}


def test_unique_ids_and_explicit_prefix():
    first = svg_root(render_svg(SOURCE))
    second = svg_root(render_svg(SOURCE))
    first_ids = {element.attrib["id"] for element in first.iter() if "id" in element.attrib}
    second_ids = {element.attrib["id"] for element in second.iter() if "id" in element.attrib}
    assert first_ids and second_ids
    assert first_ids.isdisjoint(second_ids)
    assert first.attrib["aria-labelledby"] in first_ids
    fixed = svg_root(render_svg(SOURCE, idPrefix="user-prefix"))
    assert fixed.attrib["aria-labelledby"] == "user-prefix-title"


def test_reproducibility_with_fixed_prefix_and_clock():
    source = FIXTURES["gantt"]["source"]
    options = {"idPrefix": "fixed", "now": 1767225600000}
    assert render_svg(source, **options) == render_svg(source, **options)


def test_options_affect_output():
    original = svg_root(render_svg(SOURCE))
    changed = svg_root(render_svg(SOURCE, fontSize=28, fontFamily="serif", responsive=False))
    assert "font:28px sans-serif" in changed.attrib["style"]
    assert "font-family:var(--pele-font,serif)" in changed.attrib["style"]
    assert "max-width:100%" in original.attrib["style"]
    assert "max-width:100%" not in changed.attrib["style"]
    assert float(changed.attrib["height"]) > float(original.attrib["height"])
    constrained = svg_root(render_svg(SOURCE, maxWidth=180, autoDirection=False))
    assert constrained.attrib != original.attrib


def test_quotes_backslashes_newlines_and_markup_cross_as_data():
    source = 'flowchart LR\n A["He said #quot;hi#quot; C:\\tmp <b>bold</b> & text"] --> B["終 👋"]'
    root = svg_root(render_svg(source, autoDirection=False))
    text = "".join(root.itertext())
    assert 'He said "hi" C:\\tmp' in text
    assert "bold" in text
    assert "終 👋" in text
    assert "&amp;" in render_svg(source)


def test_code_like_label_is_not_executed():
    label = "'); throw new Error('injected'); //"
    source = 'flowchart LR\n A["' + label + '"]'
    text = " ".join(svg_root(render_svg(source)).itertext())
    assert label in text


def test_source_and_json_control_characters_are_callable_data(monkeypatch):
    # A miniature JS renderer checks the transport independent of Mermaid syntax.
    monkeypatch.setattr(
        _runtime,
        "_bundle_text",
        lambda: "var pele = {render: (s, o) => ({svg: JSON.stringify([s, o])})};",
    )
    source = 'quote " slash \\ null \0 separator \u2028\u2029 emoji 👋\n'
    options = {"idPrefix": "fixed", "unknownOption": {"label": source}}
    assert json.loads(render_svg(source, **options)) == [source, options]


@pytest.mark.parametrize("source", [None, 42, b"flowchart LR", [], {}])
def test_non_string_source_rejected_before_runtime(source, monkeypatch):
    monkeypatch.setattr(_runtime, "render_svg", lambda *args: pytest.fail("entered runtime"))
    with pytest.raises(TypeError, match="source must be a string"):
        render_svg(source)
    with pytest.raises(TypeError):
        render(source)


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        (-float("inf"), ValueError),
        (10**1000, ValueError),
        ({"nested": [float("nan")]}, ValueError),
        ({1: "coerced keys are forbidden"}, TypeError),
        (object(), TypeError),
        (lambda: 1, TypeError),
        ({1, 2}, TypeError),
        (b"bytes", TypeError),
    ],
)
def test_invalid_options_rejected_before_runtime(value, error, monkeypatch):
    monkeypatch.setattr(_runtime, "render_svg", lambda *args: pytest.fail("entered runtime"))
    with pytest.raises(error):
        render_svg(SOURCE, config=value)


@pytest.mark.parametrize("name", ["measurer", "icons", "math"])
def test_callbacks_are_not_supported(name):
    with pytest.raises(TypeError, match="callback"):
        render_svg(SOURCE, **{name: "() => arbitraryJavaScript()"})


def test_circular_options_rejected():
    value = []
    value.append(value)
    with pytest.raises(ValueError, match="circular"):
        render_svg(SOURCE, config=value)


def test_shared_containers_and_json_values_are_allowed():
    values = [None, True, False, 2, 1.5, "text", {"key": []}]
    svg_root(render_svg(SOURCE, unknownOption=(values, values)))


def test_error_diagnostics_and_recovery():
    with pytest.raises(PeleError) as caught:
        render_svg("flowchart LR\n A[unterminated")
    error = caught.value
    assert error.message == str(error)
    assert "Parse error" in error.message
    assert error.code == "syntax"
    assert error.line == 2
    assert error.column > 0
    assert "A[unterminated" in error.snippet
    svg_root(render_svg(SOURCE))


def test_unsupported_diagram_preserves_upstream_empty_positions():
    with pytest.raises(PeleError) as caught:
        render_svg("not a diagram")
    assert caught.value.code == "unsupported-diagram"
    assert caught.value.line == 0
    assert caught.value.column == 0
    assert caught.value.snippet == ""


def test_missing_error_diagnostics_are_none(monkeypatch):
    monkeypatch.setattr(
        _runtime,
        "_bundle_text",
        lambda: (
            """
        var pele = {
            PeleError: class extends Error {},
            render() { throw new this.PeleError('minimal diagnostic'); }
        };
        """
        ),
    )
    with pytest.raises(PeleError) as caught:
        render_svg(SOURCE)
    error = caught.value
    assert error.message == "minimal diagnostic"
    assert (error.code, error.line, error.column, error.snippet) == (None,) * 4


def test_runtime_load_failure_has_context(monkeypatch):
    monkeypatch.setattr(_runtime, "_bundle_text", lambda: "this is broken JavaScript;")
    with pytest.raises(RuntimeError, match="Unable to load bundled Pele"):
        render_svg(SOURCE)


def test_missing_asset_is_runtime_failure(monkeypatch):
    def missing():
        raise FileNotFoundError("missing pele.global.js")

    monkeypatch.setattr(_runtime, "_bundle_text", missing)
    with pytest.raises(RuntimeError, match="missing pele.global.js"):
        render_svg(SOURCE)


def test_unexpected_js_failure_is_runtime_error(monkeypatch):
    monkeypatch.setattr(
        _runtime,
        "_bundle_text",
        lambda: (
            "var pele = {PeleError: class extends Error {}, "
            "render() { throw new Error('runtime exploded'); }};"
        ),
    )
    with pytest.raises(RuntimeError, match="runtime exploded"):
        render_svg(SOURCE)


@pytest.mark.parametrize(
    "bridge",
    [
        "() => {throw new Error('native bridge failure')}",
        "() => 'not json'",
        "() => 'null'",
        "() => JSON.stringify({ok: true, svg: 42})",
    ],
)
def test_invalid_bridge_result_is_runtime_error(bridge, monkeypatch):
    monkeypatch.setattr(_runtime, "_BRIDGE", bridge)
    with pytest.raises(RuntimeError):
        render_svg(SOURCE)


def test_independent_renders_in_multiple_threads():
    def work(index):
        source = f"flowchart LR\n accTitle: Thread {index}\n A[Worker {index}] --> B[Done]"
        root = svg_root(render_svg(source))
        assert f"Worker {index}" in "".join(root.itertext())
        return root.attrib["aria-labelledby"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(work, range(16)))
    assert len(set(ids)) == 16


def test_vendored_asset_hashes():
    import hashlib

    vendor = resources.files(pele_python).joinpath("_vendor")
    manifest = json.loads(vendor.joinpath("manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "pele"
    for name, metadata in manifest["files"].items():
        data = vendor.joinpath(name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
        assert len(data) == metadata["size_bytes"]
