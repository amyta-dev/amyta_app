from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value: Decimal | int | str | None) -> Decimal | None:
    """Normalize a monetary value to two decimal places."""
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(CENT)


@dataclass(slots=True)
class Transaction:
    transaction_date: date
    description: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    balance: Decimal | None = None
    source_page: int = 1
    balance_inferred: bool = False

    def __post_init__(self) -> None:
        self.debit = money(self.debit) or ZERO
        self.credit = money(self.credit) or ZERO
        self.balance = money(self.balance)
        self.description = "\n".join(
            line.strip() for line in self.description.splitlines() if line.strip()
        ).strip()


@dataclass(slots=True)
class ParsedStatement:
    bank_code: str
    bank_name: str
    transactions: list[Transaction]
    account_number: str | None = None
    account_name: str | None = None
    currency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    reported_total_debit: Decimal | None = None
    reported_total_credit: Decimal | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.opening_balance = money(self.opening_balance)
        self.closing_balance = money(self.closing_balance)
        self.reported_total_debit = money(self.reported_total_debit)
        self.reported_total_credit = money(self.reported_total_credit)
        if self.closing_balance is None and self.transactions:
            self.closing_balance = self.transactions[-1].balance

    @property
    def total_debit(self) -> Decimal:
        return money(sum((tx.debit for tx in self.transactions), ZERO)) or ZERO

    @property
    def total_credit(self) -> Decimal:
        return money(sum((tx.credit for tx in self.transactions), ZERO)) or ZERO

    @property
    def inferred_balance_count(self) -> int:
        return sum(1 for tx in self.transactions if tx.balance_inferred)

    def row_balance_mismatches(self, tolerance: Decimal = Decimal("0.02")) -> list[int]:
        """Return 1-based transaction indexes that do not reconcile."""
        mismatches: list[int] = []
        previous = self.opening_balance

        for index, tx in enumerate(self.transactions, start=1):
            if previous is None:
                if tx.balance is not None:
                    previous = tx.balance
                continue

            expected = money(previous + tx.credit - tx.debit)
            if tx.balance is not None:
                if expected is not None and abs(tx.balance - expected) > tolerance:
                    mismatches.append(index)
                previous = tx.balance
            else:
                previous = expected

        return mismatches

    def reconciliation_difference(self) -> Decimal | None:
        if self.opening_balance is None or self.closing_balance is None:
            return None
        expected = self.opening_balance + self.total_credit - self.total_debit
        return money(self.closing_balance - expected)

    def reconciliation_status(self) -> str:
        difference = self.reconciliation_difference()
        if difference is None:
            return "PARTIAL - opening/closing balance tidak lengkap"
        if abs(difference) <= Decimal("0.02"):
            return "RECONCILED"
        return f"NOT RECONCILED (selisih {difference:,.2f})"
