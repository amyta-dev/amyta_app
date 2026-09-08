from __future__ import annotations

from decimal import Decimal
from typing import Any

from .exceptions import UnsupportedFormatError
from .models import ParsedStatement
from .parsers import BcaParser, BniParser, BocParser, CimbParser, MandiriParser
from .pdf_utils import load_pdf

_PARSERS = {
    "bca": BcaParser(),
    "cimb": CimbParser(),
    "boc": BocParser(),
    "mandiri": MandiriParser(),
    "bni": BniParser(),
}

BANK_OPTIONS = [
    ("bca", "Bank Central Asia"),
    ("cimb", "Bank CIMB Niaga"),
    ("boc", "Bank of China"),
    ("mandiri", "Bank Mandiri"),
    ("bni", "Bank Negara Indonesia"),
]


def parse_statement(
    bank_code: str,
    pdf_bytes: bytes,
    *,
    max_pages: int = 100,
    **options: Any,
) -> ParsedStatement:
    parser = _PARSERS.get(bank_code.lower())
    if parser is None:
        raise UnsupportedFormatError("Bank yang dipilih belum didukung.")
    document = load_pdf(pdf_bytes, max_pages=max_pages)
    statement = parser.parse(document, **options)

    mismatches = statement.row_balance_mismatches()
    if mismatches:
        preview = ", ".join(str(index) for index in mismatches[:10])
        suffix = "..." if len(mismatches) > 10 else ""
        statement.warnings.append(
            f"Running balance tidak cocok pada transaksi: {preview}{suffix}."
        )

    if (
        statement.reported_total_debit is not None
        and abs(statement.reported_total_debit - statement.total_debit) > Decimal("0.02")
    ):
        statement.warnings.append(
            "Total debit hasil parsing berbeda dari total debit yang tercetak pada PDF."
        )
    if (
        statement.reported_total_credit is not None
        and abs(statement.reported_total_credit - statement.total_credit) > Decimal("0.02")
    ):
        statement.warnings.append(
            "Total credit hasil parsing berbeda dari total credit yang tercetak pada PDF."
        )

    return statement
