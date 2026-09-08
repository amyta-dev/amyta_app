from __future__ import annotations

import re
from datetime import datetime
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
)
from .base import BaseStatementParser


class MandiriParser(BaseStatementParser):
    code = "mandiri"
    name = "Bank Mandiri"
    markers = ("LAPORAN REKENING KORAN", "POSTING DATE", "REMARK", "BALANCE")

    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        self.validate_format(document)
        transactions: list[Transaction] = []

        for page in document.pages:
            anchors = [
                word
                for word in page.words
                if re.fullmatch(r"\d{2}/\d{2}/\d{4}", word.text)
                and word.cx < 0.17 * page.width
            ]
            anchors.sort(key=lambda word: word.y0)
            if not anchors:
                continue

            # Some remarks continue at the very top of the next page.
            if transactions:
                continuation = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.17,
                    right=0.38,
                    top=0,
                    bottom=max(0, anchors[0].y0 - 10),
                )
                if continuation:
                    transactions[-1].description = (
                        f"{transactions[-1].description}\n{continuation}".strip()
                    )

            for index, anchor in enumerate(anchors):
                next_y = (
                    anchors[index + 1].y0
                    if index + 1 < len(anchors)
                    else self._footer_y(page, anchor.y0)
                )
                top = max(0, anchor.y0 - 10)
                bottom = max(top + 1, next_y - 10)

                debit_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.50,
                    right=0.65,
                    top=top,
                    bottom=bottom,
                )
                credit_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.65,
                    right=0.80,
                    top=top,
                    bottom=bottom,
                )
                balance_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.80,
                    right=0.995,
                    top=top,
                    bottom=bottom,
                )
                if not debit_values or not credit_values or not balance_values:
                    raise ParseError(
                        f"Kolom Debit/Credit/Balance Mandiri tidak lengkap pada halaman "
                        f"{page.number}, tanggal {anchor.text}."
                    )

                description = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.17,
                    right=0.38,
                    top=top,
                    bottom=bottom,
                ) or "(Tanpa remarks)"

                transactions.append(
                    Transaction(
                        transaction_date=datetime.strptime(
                            anchor.text, "%d/%m/%Y"
                        ).date(),
                        description=description,
                        debit=abs(debit_values[0][1]),
                        credit=abs(credit_values[0][1]),
                        balance=balance_values[0][1],
                        source_page=page.number,
                    )
                )

        if not transactions:
            raise ParseError("Tidak ada transaksi Mandiri yang berhasil dibaca.")

        period_match = re.search(
            r"PERIOD\s+(\d{2}\s+[A-Z]{3}\s+\d{4})\s*-\s*(\d{2}\s+[A-Z]{3}\s+\d{4})",
            document.text,
            re.IGNORECASE,
        )
        period_start = period_end = None
        if period_match:
            period_start = datetime.strptime(period_match.group(1).title(), "%d %b %Y").date()
            period_end = datetime.strptime(period_match.group(2).title(), "%d %b %Y").date()

        account_line = first_regex_group(r"ACCOUNT\s+NO\s+([^\n]+)", document.text)
        account_number = None
        account_name = None
        if account_line:
            account_match = re.match(r"([0-9]+)\s+(?:[A-Z]{3}\s+)?(.+)", account_line.strip())
            if account_match:
                account_number = account_match.group(1)
                account_name = account_match.group(2).strip()

        opening = self._label_amount(document.text, "Opening Balance")

        return ParsedStatement(
            bank_code=self.code,
            bank_name=self.name,
            transactions=transactions,
            account_number=account_number,
            account_name=account_name,
            currency=first_regex_group(r"CURRENCY\s+([A-Z]{3})", document.text),
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening,
            closing_balance=transactions[-1].balance,
            reported_total_debit=self._label_amount(document.text, "Total Amount Debited"),
            reported_total_credit=self._reported_credit(document),
        )

    @staticmethod
    def _footer_y(page, after_y: float) -> float:
        candidates = [
            word.y0
            for word in page.words
            if word.y0 > after_y
            and word.cx < 0.20 * page.width
            and word.text.upper() in {"NO", "TOTAL", "CLOSING"}
        ]
        return min(candidates) if candidates else page.height

    @staticmethod
    def _label_amount(text: str, label: str) -> Decimal | None:
        match = re.search(
            rf"{re.escape(label)}\s+([\d,]+\.\d{{2}})", text, re.IGNORECASE
        )
        return parse_amount(match.group(1)) if match else None

    @staticmethod
    def _reported_credit(document: PdfDocumentData) -> Decimal | None:
        # The footer's text extraction order can place the value before/after another label.
        last_page = document.pages[-1]
        label_y = next(
            (
                word.y0
                for word in last_page.words
                if word.text.upper() == "CREDIT" and word.cx < 0.35 * last_page.width
            ),
            None,
        )
        if label_y is None:
            return None
        candidates = amounts_in_region(
            last_page.words,
            width=last_page.width,
            left=0.20,
            right=0.55,
            top=label_y - 5,
            bottom=min(last_page.height, label_y + 45),
        )
        return candidates[0][1] if candidates else None
