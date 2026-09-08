from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Mapping

from .engine.constants import FILE_FIELDS
from .engine.processor import AccountingProcessor, ProcessingValidationError
from .engine.report_writer import generate_report_package
from .engine.utils import parse_code_list


class FinancialReportService:
    """Application service shared by DRF and Jazzmin.

    Transport concerns (Django admin/DRF) end here. The accounting engine remains
    framework-agnostic in ``services.engine`` and operates only on local paths.
    """

    @staticmethod
    def _persist_upload(uploaded, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            if hasattr(uploaded, "chunks"):
                for chunk in uploaded.chunks():
                    handle.write(chunk)
            else:
                handle.write(uploaded.read())

    def generate(
        self,
        *,
        client_name,
        period_start,
        period_end,
        uploads: Mapping[str, object],
        ar_account_codes="",
        ap_account_codes="",
        advance_account_codes="",
        strict_validation=True,
    ) -> tuple[bytes, str, dict]:
        missing = [key for key in FILE_FIELDS if key not in uploads or uploads[key] is None]
        if missing:
            raise ValueError(f"Input workbook belum lengkap: {', '.join(missing)}")

        with tempfile.TemporaryDirectory(prefix="erp_financial_reporting_") as temporary_directory:
            temp_root = Path(temporary_directory)
            input_paths: dict[str, Path] = {}
            for key in FILE_FIELDS:
                destination = temp_root / "inputs" / f"{key}.xlsx"
                self._persist_upload(uploads[key], destination)
                input_paths[key] = destination

            processor = AccountingProcessor(
                client_name=str(client_name).strip(),
                period_start=period_start,
                period_end=period_end,
                input_paths=input_paths,
                ar_account_codes=parse_code_list(ar_account_codes),
                ap_account_codes=parse_code_list(ap_account_codes),
                advance_account_codes=parse_code_list(advance_account_codes),
                strict=bool(strict_validation),
            )
            bundle = processor.process()
            result = generate_report_package(bundle, temp_root / "outputs")
            archive_bytes = result.zip_path.read_bytes()
            metadata = {
                "output_files": result.output_files,
                "issue_counts": result.issue_counts,
                "journal_rows_read": bundle.metrics.journal_rows_read,
                "journal_rows_used": bundle.metrics.journal_rows_used,
            }
            return archive_bytes, result.zip_path.name, metadata


__all__ = ["FinancialReportService", "ProcessingValidationError"]
