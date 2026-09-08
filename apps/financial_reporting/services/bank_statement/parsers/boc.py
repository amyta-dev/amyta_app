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


class BocParser(BaseStatementParser):
    code = "boc"
    name = "Bank of China"
    markers = ("STATEMENT OF ACCOUNT/PERINCIAN REKENING", "TRAN. AMOUNT", "BALANCE")

    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        self.validate_format(document)
        sign_mode = str(options.get("boc_sign_mode", "accounting")).lower()
        if sign_mode not in {"accounting", "brd"}:
            raise ParseError("BOC_SIGN_MODE harus 'accounting' atau 'brd'.")

        transactions: list[Transaction] = []
        warnings: list[str] = []

        for page in document.pages:
            anchors = []
            for word in page.words:
                if not re.fullmatch(r"\d{6}", word.text) or word.cx >= 0.13 * page.width:
                    continue
                has_value_date = any(
                    re.fullmatch(r"\d{6}", other.text)
                    and 0.12 * page.width < other.cx < 0.22 * page.width
                    and abs(other.y0 - word.y0) <= 2.5
                    for other in page.words
                )
                if has_value_date:
                    anchors.append(word)
            anchors.sort(key=lambda word: word.y0)

            for index, anchor in enumerate(anchors):
                next_y = (
                    anchors[index + 1].y0
                    if index + 1 < len(anchors)
                    else self._footer_y(page, anchor.y0)
                )
                top = anchor.y0 - 2
                bottom = next_y - 1

                amount_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.55,
                    right=0.76,
                    top=top,
                    bottom=bottom,
                )
                balance_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.76,
                    right=0.995,
                    top=top,
                    bottom=bottom,
                )
                if not amount_values or not balance_values:
                    raise ParseError(
                        f"Tran. Amount/Balance BOC tidak lengkap pada halaman {page.number}, "
                        f"tanggal {anchor.text}."
                    )

                signed_amount = amount_values[0][1]
                absolute_amount = abs(signed_amount)
                if sign_mode == "accounting":
                    debit = absolute_amount if signed_amount < 0 else Decimal("0")
                    credit = absolute_amount if signed_amount >= 0 else Decimal("0")
                else:  # literal mapping in the supplied BRD table
                    debit = absolute_amount if signed_amount >= 0 else Decimal("0")
                    credit = absolute_amount if signed_amount < 0 else Decimal("0")

                tx_date = datetime.strptime(anchor.text, "%y%m%d").date()
                description = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.20,
                    right=0.56,
                    top=top,
                    bottom=bottom,
                ) or "(Tanpa Vou. No./Trans No.)"

                transactions.append(
                    Transaction(
                        transaction_date=tx_date,
                        description=description,
                        debit=debit,
                        credit=credit,
                        balance=balance_values[0][1],
                        source_page=page.number,
                    )
                )

        if not transactions:
            raise ParseError("Tidak ada transaksi Bank of China yang berhasil dibaca.")

        if sign_mode == "brd":
            warnings.append(
                "BOC_SIGN_MODE=brd: mapping mengikuti tabel BRD secara literal "
                "(positif=Debit, negatif=Credit). Mode ini berlawanan dengan catatan pada PDF BOC."
            )

        period_start = self._compact_date(
            first_regex_group(r"FROM\(YYYYMMDD\)/DARI\s*:\s*(\d{8})", document.text)
        )
        period_end = self._compact_date(
            first_regex_group(r"TO\(YYYYMMDD\)/SAMPAI\s*:\s*(\d{8})", document.text)
        )

        return ParsedStatement(
            bank_code=self.code,
            bank_name=self.name,
            transactions=transactions,
            account_number=first_regex_group(
                r"ACCOUNT\s+NO\./NOMOR\s+REKENING\s*:\s*([0-9]+)", document.text
            ),
            account_name=first_regex_group(r"NAME/NAMA\s*:\s*([^\n]+)", document.text),
            currency=first_regex_group(r"CURRENCY/KURS\s*:\s*([A-Z]{3})", document.text),
            period_start=period_start,
            period_end=period_end,
            opening_balance=self._label_amount(
                document.text,
                r"PREVIOUS\s+PERIOD\s+BALANCE/SALDO\s+PERIODE\s+SEBELUMNYA\s*:\s*([\d,]+\.\d{2})",
            ),
            closing_balance=self._label_amount(
                document.text,
                r"BALANCE\s+FOR\s+THE\s+PERIOD/SALDO\s+AKHIR\s*:\s*([\d,]+\.\d{2})",
            )
            or transactions[-1].balance,
            reported_total_debit=self._label_amount(
                document.text,
                r"DEBIT\s+AMOUNT/TTL\s+NILAI\s+TRX\s+DB\s*:\s*([\d,]+\.\d{2})",
            ),
            reported_total_credit=self._label_amount(
                document.text,
                r"CREDIT\s+AMOUNT/TTL\s+NILAI\s+TRX\s+KR\s*:\s*([\d,]+\.\d{2})",
            ),
            warnings=warnings,
            metadata={"boc_sign_mode": sign_mode},
        )

    @staticmethod
    def _footer_y(page, after_y: float) -> float:
        candidates = [
            word.y0
            for word in page.words
            if word.y0 > after_y
            and word.cx < 0.20 * page.width
            and word.text.upper() == "BALANCE"
        ]
        return min(candidates) if candidates else page.height

    @staticmethod
    def _label_amount(text: str, pattern: str) -> Decimal | None:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return parse_amount(match.group(1)) if match else None

    @staticmethod
    def _compact_date(value: str | None):
        return datetime.strptime(value, "%Y%m%d").date() if value else None
