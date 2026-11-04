"""The sole runtime adapter. Only bundle text is cached, never JS contexts."""

import json
from functools import lru_cache
from importlib import resources

from ._errors import PeleError

# JSON serialization also flattens QuickJS rope strings before they cross the
# native Python boundary (quickjs-ng 0.17 does not expose rope strings directly).
_BRIDGE = """
(source, optionsJSON) => {
    try {
        const result = pele.render(source, JSON.parse(optionsJSON));
        return JSON.stringify({ok: true, svg: result.svg});
    } catch (error) {
        return JSON.stringify({
            ok: false,
            kind: error instanceof pele.PeleError ? 'pele' : 'runtime',
            message: error.message ?? String(error),
            code: error.code ?? null,
            line: error.line ?? null,
            column: error.column ?? null,
            snippet: error.snippet ?? null
        });
    }
}
"""


@lru_cache(maxsize=1)
def _bundle_text() -> str:
    return (
        resources.files("pele_python")
        .joinpath("_vendor")
        .joinpath("pele.global.js")
        .read_text(encoding="utf-8")
    )


def render_svg(source: str, options_json: str) -> str:
    context = bridge = None
    try:
        try:
            import quickjs

            context = quickjs.Context()
            context.eval(_bundle_text())
            bridge = context.eval(_BRIDGE)
        except Exception as exc:
            raise RuntimeError(f"Unable to load bundled Pele in QuickJS: {exc}") from exc

        try:
            # Source and options are function arguments, never executable code.
            payload = json.loads(bridge(source, options_json))
        except Exception as exc:
            raise RuntimeError(f"Unable to execute Pele in QuickJS: {exc}") from exc
    finally:
        # A bridge callable owns a reference to its context. Drop both on the
        # rendering thread, on success as well as on every failure path.
        bridge = context = None

    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        raise RuntimeError("Pele runtime returned an invalid response")
    if payload["ok"]:
        if not isinstance(payload.get("svg"), str):
            raise RuntimeError("Pele runtime did not return an SVG string")
        return payload["svg"]
    if payload.get("kind") == "pele":
        raise PeleError(
            payload.get("message", "Pele rendering failed"),
            code=payload.get("code"),
            line=payload.get("line"),
            column=payload.get("column"),
            snippet=payload.get("snippet"),
        )
    raise RuntimeError(f"Pele runtime execution failed: {payload.get('message', 'unknown error')}")
