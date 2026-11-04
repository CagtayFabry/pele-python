"""Feasibility gate: evaluate the unmodified bundle without any host shims."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import quickjs

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    bundle = (ROOT / "src/pele_python/_vendor/pele.global.js").read_text("utf-8")
    diagrams = json.loads((ROOT / "tests/fixtures/diagrams.json").read_text("utf-8"))
    print(platform.platform(), platform.python_version())
    print("quickjs-ng", importlib.metadata.version("quickjs-ng"))
    for kind, diagram in diagrams.items():
        start = time.perf_counter()
        context = quickjs.Context()
        assert context.eval(
            "[typeof document, typeof window, typeof process, typeof require, "
            "typeof fetch].every(x => x === 'undefined')"
        )
        context.eval(bundle)
        # Pass source as a callable argument, never as executable JS.
        bridge = context.eval(
            "(source) => JSON.stringify(pele.render(source, "
            "{idPrefix: 'gate', now: 1767225600000}).svg)"
        )
        svg = json.loads(bridge(diagram["source"]))
        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        text = "".join(root.itertext())
        for label in diagram["labels"]:
            assert label in text, (kind, label)
        print(f"{kind}: PASS ({len(svg):,} SVG chars; {time.perf_counter() - start:.3f}s)")
        del bridge, context


if __name__ == "__main__":
    main()
