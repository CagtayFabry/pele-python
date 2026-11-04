"""Notebook rich display without an IPython dependency."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class Diagram:
    svg: str

    def _repr_svg_(self) -> str:
        return self.svg

    def __repr__(self) -> str:
        return f"Diagram({len(self.svg):,} SVG characters)"
