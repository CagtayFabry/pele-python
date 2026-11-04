"""Generate browser QA and an executed quickstart notebook from real renders."""

from __future__ import annotations

import html
import json
from pathlib import Path

from pele_python import render, render_svg

ROOT = Path(__file__).resolve().parents[1]


def large_tree_source(node_count: int = 63) -> str:
    lines = ["flowchart LR", f"  accTitle: Binary tree with {node_count} nodes"]
    lines.extend(f'  N{node}["Node {node}"]' for node in range(1, node_count + 1))
    lines.extend(f"  N{node // 2} --> N{node}" for node in range(2, node_count + 1))
    return "\n".join(lines)


def main() -> None:
    fixtures = json.loads((ROOT / "tests/fixtures/diagrams.json").read_text("utf-8"))
    vendor = json.loads((ROOT / "src/pele_python/_vendor/manifest.json").read_text("utf-8"))
    cards = []
    for kind, fixture in fixtures.items():
        svg = render_svg(fixture["source"], idPrefix=f"preview-{kind}", now=1767225600000)
        cards.append(
            f"<article><h2>{html.escape(kind.title())}</h2>"
            f'<div class="diagram">{svg}</div>'
            f"<pre>{html.escape(fixture['source'])}</pre></article>"
        )
    tree_code = (
        "from pele_python import render\n\n"
        "node_count = 63\n"
        'lines = ["flowchart LR", f"  accTitle: Binary tree with {node_count} nodes"]\n'
        "lines.extend(f'  N{node}[\"Node {node}\"]' for node in range(1, node_count + 1))\n"
        'lines.extend(f"  N{node // 2} --> N{node}" for node in range(2, node_count + 1))\n'
        'tree_source = "\\n".join(lines)\n\n'
        "tree = render(\n"
        "    tree_source,\n"
        "    idPrefix='notebook-tree',\n"
        "    fontSize=14,\n"
        "    autoDirection=False,\n"
        "    responsive=False,\n"
        ")\n"
        "tree"
    )
    tree = render(
        large_tree_source(),
        idPrefix="notebook-tree",
        fontSize=14,
        autoDirection=False,
        responsive=False,
    )
    cards.append(
        '<article id="large-tree"><h2>Large tree (63 nodes)</h2>'
        "<p>A balanced binary tree with 63 nodes and 62 edges. "
        "Fixed sizing keeps labels readable; scroll to explore the diagram.</p>"
        f'<div class="diagram">{tree.svg}</div><pre>{html.escape(tree_code)}</pre></article>'
    )
    page = (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>pele-python rendering checks</title><style>
body { margin:32px auto; max-width:1000px; padding:0 24px; color:#20252d;
       background:#f5f6f8; font:16px system-ui,sans-serif; }
h1 { font-size:28px; } h2 { margin:0 0 24px; font-size:20px; }
article { margin:24px 0; padding:28px; background:white; border:1px solid #d8dce3;
          border-radius:12px; } .diagram { padding:8px; overflow:auto; }
pre { padding:16px; background:#f5f6f8; font-size:13px; white-space:pre-wrap; }
</style><h1>pele-python</h1>
"""
        + f"<p>Pele {html.escape(vendor['version'])} · QuickJS 0.17.0.2"
        + " · built-in text measurement</p>"
        + "".join(cards)
        + "</html>"
    )
    destination = ROOT / "build"
    destination.mkdir(exist_ok=True)
    (destination / "preview.html").write_text(page, "utf-8")

    def markdown(text):
        return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}

    cells = [
        markdown(
            "# pele-python quickstart\n\n"
            "Run this notebook in an environment containing `pele-python`. "
            "The renderer needs no Node.js, browser, IPython import, or setup cell. "
            "The notebook frontend itself supplies rich SVG display.\n"
        )
    ]
    for index, kind in enumerate(("flowchart", "sequence"), 1):
        source = fixtures[kind]["source"]
        code = (
            "from pele_python import render\n\n"
            f"source = {source!r}\n"
            f"diagram = render(source, idPrefix='notebook-{kind}')\n"
            "diagram"
        )
        diagram = render(source, idPrefix=f"notebook-{kind}")
        cells.extend(
            [
                markdown(
                    f"## {kind.title()}\n\nThe SVG below was rendered by the embedded runtime.\n"
                ),
                {
                    "cell_type": "code",
                    "metadata": {},
                    "execution_count": index,
                    "source": code.splitlines(keepends=True),
                    "outputs": [
                        {
                            "output_type": "execute_result",
                            "execution_count": index,
                            "metadata": {},
                            "data": {"image/svg+xml": diagram.svg, "text/plain": repr(diagram)},
                        }
                    ],
                },
            ]
        )
    cells.extend(
        [
            markdown(
                "## Large tree (63 nodes)\n\n"
                "Generate a balanced binary tree with **63 nodes and 62 edges**. "
                "Each node after the root connects to its parent (`node // 2`). "
                "The left-to-right layout and fixed SVG size keep the labels readable; "
                "scroll through the output to explore all six levels.\n"
            ),
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": 3,
                "source": tree_code.splitlines(keepends=True),
                "outputs": [
                    {
                        "output_type": "execute_result",
                        "execution_count": 3,
                        "metadata": {},
                        "data": {"image/svg+xml": tree.svg, "text/plain": repr(tree)},
                    }
                ],
            },
        ]
    )
    cells.append(
        markdown(
            "## Save or reuse the markup\n\n"
            "`diagram.svg` contains the already rendered SVG. For plain strings, use "
            "`render_svg(source)`. To save: "
            "`Path('diagram.svg').write_text(diagram.svg, encoding='utf-8')`.\n"
        )
    )
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "cells": [{"id": f"cell-{i}", **cell} for i, cell in enumerate(cells)],
    }
    examples = ROOT / "examples"
    examples.mkdir(exist_ok=True)
    (examples / "quickstart.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", "utf-8"
    )
    print(f"Wrote {destination / 'preview.html'} and examples/quickstart.ipynb")


if __name__ == "__main__":
    main()
