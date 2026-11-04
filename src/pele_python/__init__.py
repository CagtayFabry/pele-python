"""Render Mermaid to SVG with Pele, without a browser or Node.js."""

from typing import Any
from uuid import uuid4

from . import _runtime
from ._diagram import Diagram
from ._errors import PeleError
from ._options import encode_options

__all__ = ["render", "render_svg", "PeleError"]


def render_svg(source: str, **options: Any) -> str:
    """Render Mermaid source to SVG; options use Pele's JavaScript names.

    Each call owns a fresh QuickJS context. Options must contain finite JSON
    data. A unique SVG ID prefix is generated unless ``idPrefix`` is supplied.

    Raises:
        TypeError: Source is not a string, or an option is not JSON data.
        ValueError: Options contain non-finite numbers or circular references.
        PeleError: Pele cannot parse or render the diagram.
        RuntimeError: The embedded runtime or bundled asset cannot be used.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string containing Mermaid syntax")
    if "idPrefix" not in options:
        options["idPrefix"] = f"pele_{uuid4().hex}"
    return _runtime.render_svg(source, encode_options(options))


def render(source: str, **options: Any) -> Diagram:
    """Render once and return an object supporting notebook SVG display."""
    return Diagram(render_svg(source, **options))
