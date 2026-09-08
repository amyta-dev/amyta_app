from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

Severity = Literal["ERROR", "WARNING", "INFO"]
ZERO = Decimal("0")


@dataclass(slots=True)
class Issue:
    severity: Severity
    category: str
    reference: str
    message: str


@dataclass(slots=True)
class InputTable:
    label: str
    source_name: str
    sheet_name: str
    header_row: int
    rows: list[dict[str, Any]]


@dataclass(slots=True)
class TrialBalanceRow:
    account_code: str
    account_name: str
    opening_idr: Decimal = ZERO
    opening_fx: Decimal = ZERO
    debit_idr: Decimal = ZERO
    credit_idr: Decimal = ZERO
    debit_fx: Decimal = ZERO
    credit_fx: Decimal = ZERO
    ending_idr: Decimal = ZERO
    ending_fx: Decimal = ZERO
    comments: str = ""


@dataclass(slots=True)
class StatementRow:
    code: str
    description_id: str
    description_en: str
    description_zh: str
    opening: Decimal = ZERO
    movement: Decimal = ZERO
    ending: Decimal = ZERO
    level: int = 0
    kind: Literal["detail", "section", "subtotal", "total", "check"] = "detail"


@dataclass(slots=True)
class LedgerRow:
    account_code: str
    account_name: str
    party: str
    opening_idr: Decimal | None
    opening_fx: Decimal | None
    transaction_date: date | None
    bl_no: str
    remarks: str
    description: str
    debit_idr: Decimal
    debit_fx: Decimal
    credit_idr: Decimal
    credit_fx: Decimal
    ending_idr: Decimal
    ending_fx: Decimal


@dataclass(slots=True)
class VoucherReconciliation:
    voucher_no: str
    debit_idr: Decimal
    credit_idr: Decimal
    difference_idr: Decimal
    debit_fx: Decimal
    credit_fx: Decimal
    difference_fx: Decimal


@dataclass(slots=True)
class CashFlowMappingAudit:
    journal_row: int
    voucher_no: str
    source_code: str
    mapped_code: str
    method: str
    amount: Decimal
    status: str


@dataclass(slots=True)
class ProcessingMetrics:
    journal_rows_read: int = 0
    journal_rows_used: int = 0
    journal_rows_outside_period: int = 0
    journal_debit_idr: Decimal = ZERO
    journal_credit_idr: Decimal = ZERO
    journal_debit_fx: Decimal = ZERO
    journal_credit_fx: Decimal = ZERO
    tb_opening_idr: Decimal = ZERO
    tb_opening_fx: Decimal = ZERO
    tb_ending_idr: Decimal = ZERO
    tb_ending_fx: Decimal = ZERO
    assets_opening: Decimal = ZERO
    assets_ending: Decimal = ZERO
    liabilities_equity_opening: Decimal = ZERO
    liabilities_equity_ending: Decimal = ZERO
    bs_difference_opening: Decimal = ZERO
    bs_difference_ending: Decimal = ZERO
    cash_beginning: Decimal = ZERO
    cash_ending: Decimal = ZERO
    tb_cash_opening: Decimal = ZERO
    tb_cash_ending: Decimal = ZERO
    cash_reconciliation_opening: Decimal = ZERO
    cash_reconciliation_ending: Decimal = ZERO
    earnings_after_tax_opening: Decimal = ZERO
    earnings_after_tax_movement: Decimal = ZERO
    earnings_after_tax_ending: Decimal = ZERO


@dataclass(slots=True)
class ReportBundle:
    client_name: str
    period_start: date
    period_end: date
    trial_balance: list[TrialBalanceRow]
    income_statement: list[StatementRow]
    balance_sheet: list[StatementRow]
    cash_flow: list[StatementRow]
    ar_ledger: list[LedgerRow]
    ap_ledger: list[LedgerRow]
    advance_ledger: list[LedgerRow]
    issues: list[Issue]
    voucher_reconciliation: list[VoucherReconciliation]
    cash_flow_mapping_audit: list[CashFlowMappingAudit]
    unmapped_accounts: list[TrialBalanceRow]
    metrics: ProcessingMetrics
    input_hashes: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationResult:
    zip_path: Path
    output_files: list[str]
    issue_counts: dict[str, int]
