"""Domain exceptions returned as user-friendly conversion errors."""


class StatementParserError(Exception):
    """Base exception for statement parsing failures."""


class InvalidPdfError(StatementParserError):
    """The uploaded file is not a readable PDF."""


class PasswordProtectedPdfError(StatementParserError):
    """The PDF requires a password."""


class UnsupportedFormatError(StatementParserError):
    """The PDF layout does not match the selected bank template."""


class ParseError(StatementParserError):
    """The PDF is recognized, but one or more transaction rows cannot be parsed safely."""
