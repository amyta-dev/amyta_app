from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..exceptions import ParseError
from ..models import ParsedStatement, Transaction
from ..pdf_utils import (
    PdfDocumentData,
    amounts_in_region,
    description_in_region,
    first_regex_group,
    parse_amount,
    line_texts,
    words_in_region,
)
from .base import BaseStatementParser

_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


class CimbParser(BaseStatementParser):
    code = "cimb"
    name = "Bank CIMB Niaga"
    markers = ("LAPORAN TRANSAKSI", "TGL. TXN", "DEBET", "KREDIT")

    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        self.validate_format(document)
        period_start, period_end = self._period(document.text)
        transactions: list[Transaction] = []

        for page in document.pages:
            anchors = [
                word
                for word in page.words
                if re.fullmatch(r"\d{2}/\d{2}", word.text)
                and word.cx < 0.10 * page.width
            ]
            anchors.sort(key=lambda word: word.y0)

            for index, anchor in enumerate(anchors):
                previous_y = anchors[index - 1].y0 if index else anchor.y0 - 40
                next_y = (
                    anchors[index + 1].y0
                    if index + 1 < len(anchors)
                    else self._total_y(page, anchor.y0)
                )
                top = (previous_y + anchor.y0) / 2 if index else anchor.y0 - 15
                bottom = (
                    (anchor.y0 + next_y) / 2
                    if index + 1 < len(anchors)
                    else next_y
                )

                debit_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.56,
                    right=0.72,
                    top=top,
                    bottom=bottom,
                )
                credit_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.72,
                    right=0.85,
                    top=top,
                    bottom=bottom,
                )
                balance_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.84,
                    right=0.995,
                    top=top,
                    bottom=bottom,
                )
                if not balance_values or (not debit_values and not credit_values):
                    raise ParseError(
                        f"Kolom nominal CIMB tidak lengkap pada halaman {page.number}, "
                        f"tanggal {anchor.text}."
                    )

                try:
                    tx_date = datetime.strptime(
                        f"{anchor.text}/{period_start.year}", "%d/%m/%Y"
                    ).date()
                except ValueError as exc:
                    raise ParseError(f"Tanggal CIMB tidak valid: {anchor.text}.") from exc

                description = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.21,
                    right=0.49,
                    top=top,
                    bottom=bottom,
                ) or "(Tanpa uraian transaksi)"

                transactions.append(
                    Transaction(
                        transaction_date=tx_date,
                        description=description,
                        debit=abs(debit_values[0][1]) if debit_values else Decimal("0"),
                        credit=abs(credit_values[0][1]) if credit_values else Decimal("0"),
                        balance=balance_values[0][1],
                        source_page=page.number,
                    )
                )

        if not transactions:
            raise ParseError("Tidak ada transaksi CIMB yang berhasil dibaca.")

        opening = self._label_amount(document.text, r"SALDO\s+AWAL\s+([\d,]+\.\d{2})")
        closing = self._label_amount(document.text, r"SALDO\s+AKHIR\s+([\d,]+\.\d{2})")
        account_name = self._account_name(document)

        return ParsedStatement(
            bank_code=self.code,
            bank_name=self.name,
            transactions=transactions,
            account_number=first_regex_group(
                r"ACCOUNT\s+NUMBER\s*:\s*([0-9]+)", document.text
            ),
            account_name=account_name,
            currency=first_regex_group(r"CURRENCY\s*:\s*([A-Z]{3})", document.text),
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening,
            closing_balance=closing or transactions[-1].balance,
            reported_total_debit=self._total_from_label(document.text, "Total", 0),
            reported_total_credit=self._total_from_label(document.text, "Total", 1),
        )

    @staticmethod
    def _account_name(document: PdfDocumentData) -> str | None:
        page = document.pages[0]
        candidates = line_texts(
            words_in_region(
                page.words,
                width=page.width,
                left=0.02,
                right=0.55,
                top=45,
                bottom=260,
            )
        )
        for index, line in enumerate(candidates):
            if "KEPADA" in line.upper() and index + 1 < len(candidates):
                return candidates[index + 1]
        return None

    @staticmethod
    def _period(text: str) -> tuple[date, date]:
        match = re.search(
            r"(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(20\d{2})"
            r"\s*-\s*(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(20\d{2})",
            text,
            re.IGNORECASE,
        )
        if not match:
            raise ParseError("Periode statement CIMB tidak ditemukan.")
        start = date(int(match.group(3)), _MONTHS[match.group(2).upper()], int(match.group(1)))
        end = date(int(match.group(6)), _MONTHS[match.group(5).upper()], int(match.group(4)))
        return start, end

    @staticmethod
    def _total_y(page, after_y: float) -> float:
        candidates = [
            word.y0
            for word in page.words
            if word.y0 > after_y and word.text.upper() == "TOTAL"
        ]
        return min(candidates) if candidates else page.height

    @staticmethod
    def _label_amount(text: str, pattern: str) -> Decimal | None:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return parse_amount(match.group(1)) if match else None

    @staticmethod
    def _total_from_label(text: str, label: str, position: int) -> Decimal | None:
        match = re.search(
            rf"{re.escape(label)}\s+([\d,]+\.\d{{2}})\s+([\d,]+\.\d{{2}})",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None
        return parse_amount(match.group(position + 1))
