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
    words_in_region,
)
from .base import BaseStatementParser


class BniParser(BaseStatementParser):
    code = "bni"
    name = "Bank Negara Indonesia"
    markers = ("TRANSACTION INQUIRY", "POST DATE", "DB/CR", "BALANCE")

    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        self.validate_format(document)
        transactions: list[Transaction] = []

        for page in document.pages:
            anchors = [
                word
                for word in page.words
                if re.fullmatch(r"\d{2}/\d{2}/\d{4}", word.text)
                and 0.05 * page.width < word.cx < 0.16 * page.width
            ]
            anchors.sort(key=lambda word: word.y0)

            for index, anchor in enumerate(anchors):
                next_y = anchors[index + 1].y0 if index + 1 < len(anchors) else page.height
                top = anchor.y0 - 1
                bottom = next_y - 1

                amount_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.69,
                    right=0.80,
                    top=top,
                    bottom=bottom,
                )
                balance_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.85,
                    right=0.995,
                    top=top,
                    bottom=bottom,
                )
                marker_words = words_in_region(
                    page.words,
                    width=page.width,
                    left=0.79,
                    right=0.86,
                    top=top,
                    bottom=bottom,
                )
                markers = [word.text.upper() for word in marker_words if word.text.upper() in {"D", "C"}]
                if not amount_values or not balance_values or not markers:
                    raise ParseError(
                        f"Kolom Amount/DbCr/Balance BNI tidak lengkap pada halaman {page.number}, "
                        f"tanggal {anchor.text}."
                    )

                tx_date = datetime.strptime(anchor.text, "%d/%m/%Y").date()
                amount = abs(amount_values[0][1])
                is_debit = markers[0] == "D"
                description = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.35,
                    right=0.70,
                    top=top,
                    bottom=bottom,
                ) or "(Tanpa description)"

                transactions.append(
                    Transaction(
                        transaction_date=tx_date,
                        description=description,
                        debit=amount if is_debit else Decimal("0"),
                        credit=Decimal("0") if is_debit else amount,
                        balance=balance_values[0][1],
                        source_page=page.number,
                    )
                )

        if not transactions:
            raise ParseError("Tidak ada transaksi BNI yang berhasil dibaca.")

        period_match = re.search(
            r"PERIOD\s*:\s*(\d{2}-[A-Z]{3}-\d{4})\s*-\s*(\d{2}-[A-Z]{3}-\d{4})",
            document.text,
            re.IGNORECASE,
        )
        period_start = period_end = None
        if period_match:
            period_start = datetime.strptime(period_match.group(1).title(), "%d-%b-%Y").date()
            period_end = datetime.strptime(period_match.group(2).title(), "%d-%b-%Y").date()

        opening = self._label_amount(document.text, "Beginning Balance")
        reported_debit = self._label_amount(document.text, "Total Debit")
        reported_credit = self._label_amount(document.text, "Total Credit")
        account_number = first_regex_group(r"ACCOUNT\s*:\s*([0-9]+)", document.text)
        account_name = first_regex_group(
            r"ACCOUNT\s*:\s*[0-9]+\s*/\s*(.+?)(?:\s{2,}|\n)", document.text
        )

        return ParsedStatement(
            bank_code=self.code,
            bank_name=self.name,
            transactions=transactions,
            account_number=account_number,
            account_name=account_name,
            currency="IDR",
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening,
            closing_balance=transactions[-1].balance,
            reported_total_debit=reported_debit,
            reported_total_credit=reported_credit,
        )

    @staticmethod
    def _label_amount(text: str, label: str) -> Decimal | None:
        match = re.search(
            rf"{re.escape(label)}\s*:\s*([\d,]+\.\d{{2}})", text, re.IGNORECASE
        )
        return parse_amount(match.group(1)) if match else None
