from __future__ import annotations

from dataclasses import dataclass

try:
    from django.conf import settings
except Exception:  # pragma: no cover
    settings = None

from .bank_statement import BANK_OPTIONS, build_excel, output_filename, parse_statement
from .bank_statement.exceptions import StatementParserError


DEFAULT_MAX_UPLOAD_MB = 25
DEFAULT_MAX_PDF_PAGES = 100
DEFAULT_BOC_SIGN_MODE = "accounting"


@dataclass(frozen=True)
class BankStatementResult:
    stream: object
    filename: str
    bank_name: str
    transaction_count: int
    warnings: tuple[str, ...]


def convert_bank_statement(*, bank_code: str, uploaded_file) -> BankStatementResult:
    """Convert an uploaded bank statement PDF to Excel in memory.

    This function is intentionally framework-light. Flask login/session/CSRF and
    template code from the source application are not carried into Django.
    """
    try:
        max_upload_mb = int(getattr(settings, "BANK_STATEMENT_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB)) if settings is not None else DEFAULT_MAX_UPLOAD_MB
        max_pages = int(getattr(settings, "BANK_STATEMENT_MAX_PDF_PAGES", DEFAULT_MAX_PDF_PAGES)) if settings is not None else DEFAULT_MAX_PDF_PAGES
        boc_sign_mode = str(getattr(settings, "BANK_STATEMENT_BOC_SIGN_MODE", DEFAULT_BOC_SIGN_MODE)) if settings is not None else DEFAULT_BOC_SIGN_MODE
    except Exception:
        # Allows the parser service to be unit-tested without bootstrapping Django settings.
        max_upload_mb = DEFAULT_MAX_UPLOAD_MB
        max_pages = DEFAULT_MAX_PDF_PAGES
        boc_sign_mode = DEFAULT_BOC_SIGN_MODE

    if boc_sign_mode not in {"accounting", "brd"}:
        raise ValueError("BANK_STATEMENT_BOC_SIGN_MODE harus 'accounting' atau 'brd'.")

    max_bytes = max_upload_mb * 1024 * 1024
    pdf_bytes = uploaded_file.read(max_bytes + 1)
    if len(pdf_bytes) > max_bytes:
        raise StatementParserError(f"Ukuran file melebihi {max_upload_mb} MB.")

    original_name = uploaded_file.name or "bank_statement.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise StatementParserError("File harus menggunakan ekstensi .pdf.")

    statement = parse_statement(
        bank_code,
        pdf_bytes,
        max_pages=max_pages,
        boc_sign_mode=boc_sign_mode,
    )
    excel_stream = build_excel(statement, original_name)
    return BankStatementResult(
        stream=excel_stream,
        filename=output_filename(original_name, bank_code),
        bank_name=statement.bank_name,
        transaction_count=len(statement.transactions),
        warnings=tuple(statement.warnings),
    )
