from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..exceptions import ParseError
from ..models import ParsedStatement, Transaction, money
from ..pdf_utils import (
    PdfDocumentData,
    amounts_in_region,
    description_in_region,
    first_regex_group,
    line_texts,
    parse_amount,
    words_in_region,
)
from .base import BaseStatementParser

_MONTHS = {
    "JANUARI": 1,
    "JANUARY": 1,
    "FEBRUARI": 2,
    "FEBRUARY": 2,
    "MARET": 3,
    "MARCH": 3,
    "APRIL": 4,
    "MEI": 5,
    "MAY": 5,
    "JUNI": 6,
    "JUNE": 6,
    "JULI": 7,
    "JULY": 7,
    "AGUSTUS": 8,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OKTOBER": 10,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DESEMBER": 12,
    "DECEMBER": 12,
}


class BcaParser(BaseStatementParser):
    code = "bca"
    name = "Bank Central Asia"
    markers = ("REKENING GIRO", "TANGGAL", "MUTASI", "SALDO")

    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        self.validate_format(document)
        period_match = re.search(
            r"PERIODE\s*:\s*([A-Z]+)\s+(20\d{2})", document.text, re.IGNORECASE
        )
        if not period_match:
            raise ParseError("Periode/tahun pada statement BCA tidak ditemukan.")

        month_name = period_match.group(1).upper()
        year = int(period_match.group(2))
        month = _MONTHS.get(month_name)
        if month is None:
            raise ParseError(f"Nama bulan BCA tidak dikenali: {month_name}.")

        transactions: list[Transaction] = []
        warnings: list[str] = []
        opening_balance: Decimal | None = None

        for page in document.pages:
            anchors = [
                word
                for word in page.words
                if re.fullmatch(r"\d{2}/\d{2}", word.text)
                and word.cx < 0.15 * page.width
            ]
            anchors.sort(key=lambda word: word.y0)

            for index, anchor in enumerate(anchors):
                next_y = (
                    anchors[index + 1].y0
                    if index + 1 < len(anchors)
                    else self._footer_y(page.words, page.height, anchor.y0)
                )
                top = anchor.y0 - 1.0
                bottom = next_y - 1.0

                description = description_in_region(
                    page.words,
                    width=page.width,
                    left=0.135,
                    right=0.52,
                    top=top,
                    bottom=bottom,
                )
                normalized_description = re.sub(
                    r"\s+", " ", description or ""
                ).strip().upper()

                balance_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.79,
                    right=0.995,
                    top=top,
                    bottom=bottom,
                )

                # Some complete BCA statements print the opening balance as the
                # first dated row, for example "01/05 SALDO AWAL 584,914,179.49".
                # It is statement metadata, not a transaction, and therefore has
                # no amount in the MUTASI column.  Capture it and skip the row.
                if normalized_description.startswith("SALDO AWAL"):
                    if balance_values:
                        candidate = money(balance_values[0][1])
                        if opening_balance is None:
                            opening_balance = candidate
                        elif candidate is not None and opening_balance != candidate:
                            warnings.append(
                                "Lebih dari satu SALDO AWAL BCA ditemukan dengan nilai berbeda; "
                                "nilai pertama digunakan."
                            )
                    else:
                        warnings.append(
                            "Baris SALDO AWAL BCA ditemukan tetapi nilainya tidak terbaca."
                        )
                    continue

                amount_values = amounts_in_region(
                    page.words,
                    width=page.width,
                    left=0.58,
                    right=0.79,
                    top=top,
                    bottom=bottom,
                )
                if not amount_values:
                    raise ParseError(
                        f"Nilai mutasi BCA tidak terbaca pada halaman {page.number}, "
                        f"tanggal {anchor.text}."
                    )

                marker_words = words_in_region(
                    page.words,
                    width=page.width,
                    left=0.72,
                    right=0.80,
                    top=top,
                    bottom=bottom,
                )
                is_debit = any(word.text.upper() == "DB" for word in marker_words)
                amount = abs(amount_values[0][1])

                try:
                    tx_date = datetime.strptime(
                        f"{anchor.text}/{year}", "%d/%m/%Y"
                    ).date()
                except ValueError as exc:
                    raise ParseError(f"Tanggal BCA tidak valid: {anchor.text}.") from exc

                if not description:
                    description = "(Tanpa keterangan)"

                transactions.append(
                    Transaction(
                        transaction_date=tx_date,
                        description=description,
                        debit=amount if is_debit else Decimal("0"),
                        credit=Decimal("0") if is_debit else amount,
                        balance=balance_values[0][1] if balance_values else None,
                        source_page=page.number,
                    )
                )

        if not transactions:
            raise ParseError("Tidak ada transaksi BCA yang berhasil dibaca.")

        # Footer values are useful fallbacks and also allow statement-level
        # reconciliation when a complete statement is uploaded.
        footer_opening = self._summary_amount(
            r"SALDO\s+AWAL\s*:\s*([0-9,]+\.\d{2})", document.text
        )
        if opening_balance is None:
            opening_balance = footer_opening
        elif footer_opening is not None and opening_balance != footer_opening:
            warnings.append(
                "SALDO AWAL pada tabel berbeda dari SALDO AWAL pada ringkasan BCA."
            )

        reported_total_credit = self._summary_amount(
            r"MUTASI\s+CR\s*:\s*([0-9,]+\.\d{2})", document.text
        )
        reported_total_debit = self._summary_amount(
            r"MUTASI\s+DB\s*:\s*([0-9,]+\.\d{2})", document.text
        )
        reported_closing = self._summary_amount(
            r"SALDO\s+AKHIR\s*:\s*([0-9,]+\.\d{2})", document.text
        )

        self._infer_missing_balances(transactions, warnings, opening_balance)
        account_name = self._account_name(document)
        account_number = first_regex_group(
            r"NO\.\s*REKENING\s*:\s*([0-9]+)", document.text
        )
        currency = first_regex_group(r"MATA\s+UANG\s*:\s*([A-Z]{3})", document.text)
        period_start = date(year, month, 1)
        period_end = date(year, month, calendar.monthrange(year, month)[1])

        if self._is_partial_statement(document):
            warnings.append(
                "Statement BCA merupakan potongan halaman. Opening balance statement "
                "hanya digunakan apabila tercetak pada PDF."
            )

        closing_balance = reported_closing or transactions[-1].balance
        if (
            reported_closing is not None
            and transactions[-1].balance is not None
            and abs(reported_closing - transactions[-1].balance) > Decimal("0.02")
        ):
            warnings.append(
                "SALDO AKHIR pada ringkasan BCA berbeda dari saldo transaksi terakhir."
            )

        return ParsedStatement(
            bank_code=self.code,
            bank_name=self.name,
            transactions=transactions,
            account_number=account_number,
            account_name=account_name,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            reported_total_debit=reported_total_debit,
            reported_total_credit=reported_total_credit,
            warnings=warnings,
        )

    @staticmethod
    def _summary_amount(pattern: str, text: str) -> Decimal | None:
        value = first_regex_group(pattern, text)
        return parse_amount(value) if value else None

    @staticmethod
    def _is_partial_statement(document: PdfDocumentData) -> bool:
        page_markers = re.findall(
            r"HALAMAN\s*:\s*(\d+)\s*/\s*(\d+)", document.text, re.IGNORECASE
        )
        if not page_markers:
            return False

        totals = {int(total) for _, total in page_markers}
        if len(totals) != 1:
            return True

        total = totals.pop()
        current_pages = {int(current) for current, _ in page_markers}
        return total != len(document.pages) or current_pages != set(range(1, total + 1))

    @staticmethod
    def _footer_y(words: list, page_height: float, after_y: float) -> float:
        candidates = [
            word.y0
            for word in words
            if word.y0 > after_y
            and (
                word.text.lower().startswith("bersambung")
                or word.text.upper() in {"TOTAL", "SALDO"}
            )
        ]
        return min(candidates) if candidates else page_height

    @staticmethod
    def _infer_missing_balances(
        transactions: list[Transaction],
        warnings: list[str],
        opening_balance: Decimal | None = None,
    ) -> None:
        inferred = 0

        # For a complete statement, calculate/validate every row from the
        # captured opening balance.  This also handles statements where BCA
        # prints balances only at periodic checkpoints.
        if opening_balance is not None:
            previous = opening_balance
            for index, tx in enumerate(transactions, start=1):
                expected = money(previous + tx.credit - tx.debit)
                if tx.balance is None:
                    tx.balance = expected
                    tx.balance_inferred = True
                    inferred += 1
                elif expected is not None and abs(tx.balance - expected) > Decimal("0.02"):
                    warnings.append(
                        f"Saldo BCA pada transaksi {index} berbeda dari perhitungan running balance."
                    )
                if tx.balance is not None:
                    previous = tx.balance
                elif expected is not None:
                    previous = expected

            if inferred:
                warnings.append(
                    f"{inferred} saldo BCA yang kosong pada PDF dihitung dari running balance."
                )
            return

        first_known = next(
            (index for index, tx in enumerate(transactions) if tx.balance is not None), None
        )
        if first_known is None:
            warnings.append("Tidak ada saldo BCA yang dapat dibaca atau dihitung.")
            return

        # Backfill transactions before the first printed balance, if any.
        current = transactions[first_known].balance
        assert current is not None
        for index in range(first_known - 1, -1, -1):
            next_tx = transactions[index + 1]
            current = money(current + next_tx.debit - next_tx.credit)
            transactions[index].balance = current
            transactions[index].balance_inferred = True
            inferred += 1

        # Forward-fill balances that BCA leaves blank between printed checkpoints.
        previous = transactions[first_known].balance
        for index in range(first_known + 1, len(transactions)):
            tx = transactions[index]
            assert previous is not None
            expected = money(previous + tx.credit - tx.debit)
            if tx.balance is None:
                tx.balance = expected
                tx.balance_inferred = True
                inferred += 1
            elif expected is not None and abs(tx.balance - expected) > Decimal("0.02"):
                warnings.append(
                    f"Saldo BCA pada transaksi {index + 1} berbeda dari perhitungan running balance."
                )
            previous = tx.balance

        if inferred:
            warnings.append(
                f"{inferred} saldo BCA yang kosong pada PDF dihitung dari running balance."
            )

    @staticmethod
    def _account_name(document: PdfDocumentData) -> str | None:
        page = document.pages[0]
        top_left = words_in_region(
            page.words,
            width=page.width,
            left=0.04,
            right=0.50,
            top=70,
            bottom=180,
        )
        for line in line_texts(top_left):
            upper = line.upper()
            if upper.startswith("KCU ") or upper in {"REKENING GIRO", "INDONESIA"}:
                continue
            if "NO. REKENING" in upper:
                continue
            if len(line) >= 5:
                return line
        return None
