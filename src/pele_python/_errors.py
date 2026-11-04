"""Diagnostics supplied by Pele."""


class PeleError(Exception):
    """An upstream parse/render failure; missing diagnostics are ``None``.

    ``line`` and ``column`` are upstream positions (1-based, or 0 when Pele
    supplies no position). Error messages/snippets are text, not HTML.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        line: int | None = None,
        column: int | None = None,
        snippet: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.line = line
        self.column = column
        self.snippet = snippet
