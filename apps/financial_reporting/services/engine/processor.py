from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .constants import (
    DETAIL_KEYWORDS,
    FILE_FIELDS,
    FX_TOLERANCE,
    MONEY_TOLERANCE,
)
from .excel_reader import InputFormatError, read_input_table
from .models import (
    CashFlowMappingAudit,
    InputTable,
    Issue,
    LedgerRow,
    ProcessingMetrics,
    ReportBundle,
    StatementRow,
    TrialBalanceRow,
    VoucherReconciliation,
    ZERO,
)
from .utils import (
    clean_text,
    natural_code_key,
    normalize_code,
    sha256_file,
    sum_decimals,
    to_decimal,
)

MONEY_EPSILON = Decimal(MONEY_TOLERANCE)
FX_EPSILON = Decimal(FX_TOLERANCE)


class ProcessingValidationError(ValueError):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("Validasi data gagal.")


@dataclass(slots=True)
class HierarchyNode:
    code: str
    level: int
    description_id: str
    description_en: str
    description_zh: str
    accounts: set[str]
    parent: str = ""
    main: str = ""


class AccountingProcessor:
    def __init__(
        self,
        *,
        client_name: str,
        period_start: date,
        period_end: date,
        input_paths: dict[str, str | Path],
        ar_account_codes: set[str] | None = None,
        ap_account_codes: set[str] | None = None,
        advance_account_codes: set[str] | None = None,
        strict: bool = True,
    ) -> None:
        self.client_name = clean_text(client_name)
        self.period_start = period_start
        self.period_end = period_end
        self.input_paths = {key: Path(value) for key, value in input_paths.items()}
        self.ar_account_codes = {normalize_code(value) for value in (ar_account_codes or set()) if normalize_code(value)}
        self.ap_account_codes = {normalize_code(value) for value in (ap_account_codes or set()) if normalize_code(value)}
        self.advance_account_codes = {
            normalize_code(value) for value in (advance_account_codes or set()) if normalize_code(value)
        }
        self.strict = strict
        self.issues: list[Issue] = []
        self.metrics = ProcessingMetrics()
        self.tables: dict[str, InputTable] = {}
        self.coa_by_code: dict[str, dict[str, Any]] = {}
        self.coa_order: list[str] = []
        self.journal_rows: list[dict[str, Any]] = []
        self.trial_by_code: dict[str, TrialBalanceRow] = {}

    def process(self) -> ReportBundle:
        self._validate_request()
        self._load_inputs()
        self._prepare_coa()
        beginning_tb = self._prepare_beginning_tb()
        self._prepare_journal()
        voucher_reconciliation = self._reconcile_vouchers()
        trial_balance = self._build_trial_balance(beginning_tb)
        income_statement, earnings_after_tax = self._build_income_statement(trial_balance)
        balance_sheet = self._build_balance_sheet(trial_balance, earnings_after_tax)
        cash_flow, cash_flow_audit = self._build_cash_flow(trial_balance)
        ar_ledger = self._build_ledger(
            report_key="ar",
            beginning=self.tables["beginning_ar"],
            party_column="Customer",
            overrides=self.ar_account_codes,
            trial_balance=trial_balance,
        )
        ap_ledger = self._build_ledger(
            report_key="ap",
            beginning=self.tables["beginning_ap"],
            party_column="Vendor",
            overrides=self.ap_account_codes,
            trial_balance=trial_balance,
        )
        advance_ledger = self._build_ledger(
            report_key="advance",
            beginning=self.tables["beginning_advance"],
            party_column="Vendor",
            overrides=self.advance_account_codes,
            trial_balance=trial_balance,
        )

        if self.strict and any(issue.severity == "ERROR" for issue in self.issues):
            raise ProcessingValidationError(self.issues)

        unmapped = [row for row in trial_balance if row.account_code not in self.coa_by_code]
        input_hashes = {
            key: {
                "label": FILE_FIELDS[key],
                "filename": path.name,
                "sha256": sha256_file(path),
            }
            for key, path in self.input_paths.items()
        }
        return ReportBundle(
            client_name=self.client_name,
            period_start=self.period_start,
            period_end=self.period_end,
            trial_balance=trial_balance,
            income_statement=income_statement,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            ar_ledger=ar_ledger,
            ap_ledger=ap_ledger,
            advance_ledger=advance_ledger,
            issues=self.issues,
            voucher_reconciliation=voucher_reconciliation,
            cash_flow_mapping_audit=cash_flow_audit,
            unmapped_accounts=unmapped,
            metrics=self.metrics,
            input_hashes=input_hashes,
        )

    def _validate_request(self) -> None:
        if not self.client_name:
            self.issues.append(Issue("ERROR", "Input", "Nama klien", "Nama klien wajib diisi."))
        if self.period_start > self.period_end:
            self.issues.append(
                Issue("ERROR", "Input", "Periode", "Tanggal awal tidak boleh melewati tanggal akhir.")
            )
        missing = [FILE_FIELDS[key] for key in FILE_FIELDS if key not in self.input_paths]
        if missing:
            self.issues.append(
                Issue("ERROR", "Input", "File", f"File wajib belum tersedia: {', '.join(missing)}.")
            )
        if any(issue.severity == "ERROR" for issue in self.issues):
            raise ProcessingValidationError(self.issues)

    def _load_inputs(self) -> None:
        fatal_format_error = False
        for key, label in FILE_FIELDS.items():
            try:
                self.tables[key] = read_input_table(
                    self.input_paths[key],
                    spec_key=key,
                    label=label,
                    issues=self.issues,
                )
            except InputFormatError as exc:
                fatal_format_error = True
                self.issues.append(Issue("ERROR", label, self.input_paths[key].name, str(exc)))
        # A malformed/missing workbook prevents downstream processing. Row-level
        # data errors (for example an invalid date) remain in the issue log so
        # non-strict mode can still produce a diagnostic package.
        if fatal_format_error:
            raise ProcessingValidationError(self.issues)

    def _prepare_coa(self) -> None:
        table = self.tables["coa_master"]
        for record in table.rows:
            code = normalize_code(record.get("Account Code"))
            if not code:
                continue
            reference = f"baris {record.get('_source_row', '?')}"
            if code in self.coa_by_code:
                self.issues.append(
                    Issue("ERROR", table.label, reference, f"Account Code {code} duplikat; baris pertama digunakan.")
                )
                continue
            self.coa_by_code[code] = record
            self.coa_order.append(code)

    def _prepare_beginning_tb(self) -> dict[str, dict[str, Any]]:
        table = self.tables["beginning_trial_balance"]
        result: dict[str, dict[str, Any]] = {}
        for record in table.rows:
            code = normalize_code(record.get("Account Code"))
            if not code:
                continue
            reference = f"baris {record.get('_source_row', '?')} / akun {code}"
            opening_idr = to_decimal(
                record.get("Opening Balance (IDR)"),
                issues=self.issues,
                category=table.label,
                reference=reference,
                field="Opening Balance (IDR)",
            )
            opening_fx = to_decimal(
                record.get("Opening Balance (FX)"),
                issues=self.issues,
                category=table.label,
                reference=reference,
                field="Opening Balance (FX)",
            )
            if code in result:
                self.issues.append(
                    Issue(
                        "WARNING",
                        table.label,
                        reference,
                        f"Account Code {code} duplikat; saldo awal dijumlahkan.",
                    )
                )
                result[code]["opening_idr"] += opening_idr
                result[code]["opening_fx"] += opening_fx
            else:
                result[code] = {
                    "account_name": clean_text(record.get("Account Name")),
                    "opening_idr": opening_idr,
                    "opening_fx": opening_fx,
                }
            if code not in self.coa_by_code:
                self.issues.append(
                    Issue("WARNING", table.label, reference, f"Account Code {code} tidak ditemukan di COA Master.")
                )
        return result

    def _prepare_journal(self) -> None:
        table = self.tables["journal_voucher"]
        self.metrics.journal_rows_read = len(table.rows)
        amount_fields = ("Debit-IDR", "Credit-IDR", "Debit-FX", "Credit-FX")
        for record in table.rows:
            row_number = int(record.get("_source_row", 0) or 0)
            voucher = clean_text(record.get("Voucher No.")) or f"ROW-{row_number}"
            code = normalize_code(record.get("Account Code"))
            reference = f"{voucher} / baris {row_number}"
            if not clean_text(record.get("Voucher No.")):
                self.issues.append(Issue("ERROR", table.label, reference, "Voucher No. kosong."))
            if not code:
                self.issues.append(Issue("ERROR", table.label, reference, "Account Code kosong."))
                continue
            transaction_date = record.get("Date")
            parsed = dict(record)
            parsed["Voucher No."] = voucher
            parsed["Account Code"] = code
            parsed["Account Name"] = clean_text(record.get("Account Name"))
            parsed["Cash Flow Code"] = normalize_code(record.get("Cash Flow Code"))
            parsed["Third Party"] = clean_text(record.get("Third Party"))
            for field in amount_fields:
                parsed[field] = to_decimal(
                    record.get(field),
                    issues=self.issues,
                    category=table.label,
                    reference=reference,
                    field=field,
                )
                if parsed[field] < ZERO:
                    self.issues.append(
                        Issue("WARNING", table.label, reference, f"{field} bernilai negatif; nilai tetap diproses.")
                    )
            if transaction_date is None:
                if any(parsed[field] != ZERO for field in amount_fields):
                    self.issues.append(Issue("ERROR", table.label, reference, "Date wajib diisi untuk baris transaksi."))
                continue
            if not (self.period_start <= transaction_date <= self.period_end):
                self.metrics.journal_rows_outside_period += 1
                continue
            if parsed["Debit-IDR"] and parsed["Credit-IDR"]:
                self.issues.append(
                    Issue("WARNING", table.label, reference, "Debit-IDR dan Credit-IDR terisi pada baris yang sama.")
                )
            if parsed["Debit-FX"] and parsed["Credit-FX"]:
                self.issues.append(
                    Issue("WARNING", table.label, reference, "Debit-FX dan Credit-FX terisi pada baris yang sama.")
                )
            if not any(parsed[field] != ZERO for field in amount_fields):
                self.issues.append(Issue("WARNING", table.label, reference, "Semua nilai debit/kredit nol."))
            parsed["Date"] = transaction_date
            parsed["_source_row"] = row_number
            self.journal_rows.append(parsed)

        self.metrics.journal_rows_used = len(self.journal_rows)
        self.metrics.journal_debit_idr = sum_decimals(row["Debit-IDR"] for row in self.journal_rows)
        self.metrics.journal_credit_idr = sum_decimals(row["Credit-IDR"] for row in self.journal_rows)
        self.metrics.journal_debit_fx = sum_decimals(row["Debit-FX"] for row in self.journal_rows)
        self.metrics.journal_credit_fx = sum_decimals(row["Credit-FX"] for row in self.journal_rows)
        idr_diff = self.metrics.journal_debit_idr - self.metrics.journal_credit_idr
        if abs(idr_diff) > MONEY_EPSILON:
            self.issues.append(
                Issue("ERROR", table.label, "Total jurnal", f"Jurnal IDR tidak seimbang; selisih {idr_diff}.")
            )
        fx_diff = self.metrics.journal_debit_fx - self.metrics.journal_credit_fx
        if abs(fx_diff) > FX_EPSILON:
            self.issues.append(
                Issue("WARNING", table.label, "Total jurnal", f"Jurnal FX tidak seimbang; selisih {fx_diff}.")
            )

    def _reconcile_vouchers(self) -> list[VoucherReconciliation]:
        grouped: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"debit_idr": ZERO, "credit_idr": ZERO, "debit_fx": ZERO, "credit_fx": ZERO}
        )
        for row in self.journal_rows:
            bucket = grouped[row["Voucher No."]]
            bucket["debit_idr"] += row["Debit-IDR"]
            bucket["credit_idr"] += row["Credit-IDR"]
            bucket["debit_fx"] += row["Debit-FX"]
            bucket["credit_fx"] += row["Credit-FX"]

        result: list[VoucherReconciliation] = []
        for voucher in sorted(grouped):
            bucket = grouped[voucher]
            diff_idr = bucket["debit_idr"] - bucket["credit_idr"]
            diff_fx = bucket["debit_fx"] - bucket["credit_fx"]
            result.append(
                VoucherReconciliation(
                    voucher_no=voucher,
                    debit_idr=bucket["debit_idr"],
                    credit_idr=bucket["credit_idr"],
                    difference_idr=diff_idr,
                    debit_fx=bucket["debit_fx"],
                    credit_fx=bucket["credit_fx"],
                    difference_fx=diff_fx,
                )
            )
            if abs(diff_idr) > MONEY_EPSILON:
                self.issues.append(
                    Issue("ERROR", "Journal Voucher", voucher, f"Voucher IDR tidak seimbang; selisih {diff_idr}.")
                )
            if abs(diff_fx) > FX_EPSILON:
                self.issues.append(
                    Issue(
                        "WARNING",
                        "Journal Voucher",
                        voucher,
                        f"Voucher FX tidak seimbang; selisih {diff_fx}. Ini dapat diterima jika FX hanya informasi ekuivalen.",
                    )
                )
        return result

    def _build_trial_balance(self, beginning_tb: dict[str, dict[str, Any]]) -> list[TrialBalanceRow]:
        movement: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"debit_idr": ZERO, "credit_idr": ZERO, "debit_fx": ZERO, "credit_fx": ZERO}
        )
        journal_names: dict[str, str] = {}
        for row in self.journal_rows:
            code = row["Account Code"]
            movement[code]["debit_idr"] += row["Debit-IDR"]
            movement[code]["credit_idr"] += row["Credit-IDR"]
            movement[code]["debit_fx"] += row["Debit-FX"]
            movement[code]["credit_fx"] += row["Credit-FX"]
            journal_names.setdefault(code, row["Account Name"])

        ordered_codes = list(self.coa_order)
        extras = (set(beginning_tb) | set(movement)) - set(ordered_codes)
        ordered_codes.extend(sorted(extras, key=natural_code_key))

        rows: list[TrialBalanceRow] = []
        for code in ordered_codes:
            coa = self.coa_by_code.get(code, {})
            beginning = beginning_tb.get(code, {})
            account_name = (
                clean_text(coa.get("Account Name (Indonesia)"))
                or clean_text(beginning.get("account_name"))
                or clean_text(journal_names.get(code))
                or "Unmapped account"
            )
            if code not in self.coa_by_code:
                self.issues.append(
                    Issue(
                        "WARNING",
                        "Pemetaan akun",
                        code,
                        "Akun terdapat pada saldo awal/jurnal tetapi tidak ada di COA Master; tetap dimasukkan ke Trial Balance.",
                    )
                )
            opening_idr = beginning.get("opening_idr", ZERO)
            opening_fx = beginning.get("opening_fx", ZERO)
            bucket = movement[code]
            ending_idr = opening_idr + bucket["debit_idr"] - bucket["credit_idr"]
            ending_fx = opening_fx + bucket["debit_fx"] - bucket["credit_fx"]
            row = TrialBalanceRow(
                account_code=code,
                account_name=account_name,
                opening_idr=opening_idr,
                opening_fx=opening_fx,
                debit_idr=bucket["debit_idr"],
                credit_idr=bucket["credit_idr"],
                debit_fx=bucket["debit_fx"],
                credit_fx=bucket["credit_fx"],
                ending_idr=ending_idr,
                ending_fx=ending_fx,
            )
            rows.append(row)
            self.trial_by_code[code] = row

        self.metrics.tb_opening_idr = sum_decimals(row.opening_idr for row in rows)
        self.metrics.tb_opening_fx = sum_decimals(row.opening_fx for row in rows)
        self.metrics.tb_ending_idr = sum_decimals(row.ending_idr for row in rows)
        self.metrics.tb_ending_fx = sum_decimals(row.ending_fx for row in rows)
        if abs(self.metrics.tb_opening_idr) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Trial Balance",
                    "Saldo awal IDR",
                    f"Saldo awal Trial Balance tidak nol; selisih {self.metrics.tb_opening_idr}.",
                )
            )
        if abs(self.metrics.tb_ending_idr) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "ERROR",
                    "Trial Balance",
                    "Saldo akhir IDR",
                    f"Saldo akhir Trial Balance tidak nol; selisih {self.metrics.tb_ending_idr}.",
                )
            )
        if abs(self.metrics.tb_ending_fx) > FX_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Trial Balance",
                    "Saldo akhir FX",
                    f"Saldo akhir Trial Balance FX tidak nol; selisih {self.metrics.tb_ending_fx}.",
                )
            )
        return rows

    def _build_hierarchy(self, statement: str) -> tuple[dict[str, HierarchyNode], dict[str, list[str]]]:
        if statement == "IS":
            levels = [
                (
                    "IS Classification (Code)",
                    "IS Classification (Indonesia)",
                    "IS Classification (English)",
                    "IS Classification (Chinese)",
                ),
                (
                    "IS Sub-Classification 1 (Code)",
                    "IS Sub-Classification 1 (Indonesia)",
                    "IS Sub-Classification 1 (English)",
                    "IS Sub-Classification 1 (Chinese)",
                ),
                (
                    "IS Sub-Classification 2 (Code)",
                    "IS Sub-Classification 2 (Indonesia)",
                    "IS Sub-Classification 2 (English)",
                    "IS Sub-Classification 2 (Chinese)",
                ),
            ]
        else:
            levels = [
                (
                    "BS Classification (Code)",
                    "BS Classification (Indonesia)",
                    "BS Classification (English)",
                    "BS Classification (Chinese)",
                ),
                (
                    "BS Sub-Classification 1 (Code)",
                    "BS Sub-Classification 1 (Indonesia)",
                    "BS Sub-Classification 1 (English)",
                    "BS Sub-Classification 1 (Chinese)",
                ),
                (
                    "BS Sub-Classification 2 (Code)",
                    "BS Sub-Classification 2 (Indonesia)",
                    "BS Sub-Classification 2 (English)",
                    "BS Sub-Classification 2 (Chinese)",
                ),
            ]
        nodes: dict[str, HierarchyNode] = {}
        children: dict[str, list[str]] = defaultdict(list)
        for account_code, coa in self.coa_by_code.items():
            parent = ""
            main = ""
            for level, (code_col, id_col, en_col, zh_col) in enumerate(levels):
                code = normalize_code(coa.get(code_col))
                if not code:
                    continue
                if level == 0:
                    main = code
                node = nodes.get(code)
                descriptions = (
                    clean_text(coa.get(id_col)),
                    clean_text(coa.get(en_col)),
                    clean_text(coa.get(zh_col)),
                )
                if node is None:
                    node = HierarchyNode(
                        code=code,
                        level=level,
                        description_id=descriptions[0],
                        description_en=descriptions[1],
                        description_zh=descriptions[2],
                        accounts=set(),
                        parent=parent,
                        main=main,
                    )
                    nodes[code] = node
                    if parent and code not in children[parent]:
                        children[parent].append(code)
                else:
                    if node.parent != parent and parent:
                        self.issues.append(
                            Issue(
                                "WARNING",
                                "COA Master",
                                code,
                                f"Kode klasifikasi memiliki parent tidak konsisten ({node.parent} dan {parent}).",
                            )
                        )
                node.accounts.add(account_code)
                parent = code
        for parent_code in children:
            children[parent_code].sort(key=natural_code_key)
        return nodes, children

    def _sum_tb(self, accounts: Iterable[str]) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
        rows = [self.trial_by_code[code] for code in accounts if code in self.trial_by_code]
        return (
            sum_decimals(row.opening_idr for row in rows),
            sum_decimals(row.debit_idr for row in rows),
            sum_decimals(row.credit_idr for row in rows),
            sum_decimals(row.ending_idr for row in rows),
            sum_decimals(row.opening_fx for row in rows),
            sum_decimals(row.ending_fx for row in rows),
        )

    def _build_income_statement(
        self, trial_balance: list[TrialBalanceRow]
    ) -> tuple[list[StatementRow], StatementRow]:
        nodes, children = self._build_hierarchy("IS")
        defaults = {
            "1": ("Pendapatan", "Revenue", "收入"),
            "2": ("Harga Pokok Pendapatan", "Cost of Revenue", "营业成本"),
            "3": ("Beban Operasi", "Operating Expenses", "营业费用"),
            "4": ("Pendapatan Lain-lain", "Other Income", "其他收入"),
            "5": ("Beban Lain-lain", "Other Expenses", "其他费用"),
            "6": ("Beban Pajak Kini", "Current Income Tax Expense", "当期所得税费用"),
        }
        rows: list[StatementRow] = []
        main_totals: dict[str, tuple[Decimal, Decimal, Decimal]] = {}

        mapped_is_accounts = {
            code
            for code, coa in self.coa_by_code.items()
            if normalize_code(coa.get("IS Classification (Code)"))
        }
        mapped_bs_accounts = {
            code
            for code, coa in self.coa_by_code.items()
            if normalize_code(coa.get("BS Classification (Code)"))
        }
        unclassified_pl = [
            row.account_code
            for row in trial_balance
            if row.account_code not in mapped_is_accounts
            and row.account_code not in mapped_bs_accounts
            and self._infer_statement_side(row.account_code, row.account_name) == "pl"
        ]

        def make_node_row(node: HierarchyNode, *, kind: str = "detail") -> StatementRow:
            opening_raw, debit, credit, ending_raw, _, _ = self._sum_tb(node.accounts)
            return StatementRow(
                code=node.code,
                description_id=node.description_id or node.description_en,
                description_en=node.description_en or node.description_id,
                description_zh=node.description_zh,
                opening=-opening_raw,
                movement=credit - debit,
                ending=-ending_raw,
                level=node.level,
                kind=kind,  # type: ignore[arg-type]
            )

        for main_code in ("1", "2", "3", "4", "5", "6"):
            node = nodes.get(main_code)
            if node is None:
                descriptions = defaults[main_code]
                node = HierarchyNode(
                    code=main_code,
                    level=0,
                    description_id=descriptions[0],
                    description_en=descriptions[1],
                    description_zh=descriptions[2],
                    accounts=set(),
                    main=main_code,
                )
            main_row = make_node_row(node, kind="section")
            rows.append(main_row)
            main_totals[main_code] = (main_row.opening, main_row.movement, main_row.ending)
            for sub1_code in children.get(main_code, []):
                sub1 = nodes[sub1_code]
                rows.append(make_node_row(sub1))
                for sub2_code in children.get(sub1_code, []):
                    rows.append(make_node_row(nodes[sub2_code]))

            if main_code == "2":
                rows.append(self._subtotal_row("Laba Kotor", "Gross Profit", "毛利", main_totals, ("1", "2")))
            elif main_code == "3":
                rows.append(
                    self._subtotal_row(
                        "Laba Operasi", "Operating Profit", "营业利润", main_totals, ("1", "2", "3")
                    )
                )
            elif main_code == "5":
                rows.append(
                    self._subtotal_row(
                        "Laba Sebelum Pajak",
                        "Earnings Before Tax",
                        "税前收益",
                        main_totals,
                        ("1", "2", "3", "4", "5"),
                    )
                )

        unclassified_values = (ZERO, ZERO, ZERO)
        if unclassified_pl:
            opening_raw, debit, credit, ending_raw, _, _ = self._sum_tb(unclassified_pl)
            unclassified_values = (-opening_raw, credit - debit, -ending_raw)
            rows.append(
                StatementRow(
                    code="U",
                    description_id="Akun laba rugi belum dipetakan",
                    description_en="Unmapped profit or loss accounts",
                    description_zh="未映射损益科目",
                    opening=unclassified_values[0],
                    movement=unclassified_values[1],
                    ending=unclassified_values[2],
                    level=0,
                    kind="check",
                )
            )
            self.issues.append(
                Issue(
                    "WARNING",
                    "Income Statement",
                    ", ".join(unclassified_pl),
                    "Akun laba rugi belum memiliki klasifikasi COA; disajikan pada baris terpisah.",
                )
            )

        eat_opening = sum_decimals(values[0] for values in main_totals.values()) + unclassified_values[0]
        eat_movement = sum_decimals(values[1] for values in main_totals.values()) + unclassified_values[1]
        eat_ending = sum_decimals(values[2] for values in main_totals.values()) + unclassified_values[2]
        eat = StatementRow(
            code="",
            description_id="Laba Setelah Pajak",
            description_en="Earnings After Tax",
            description_zh="税后收益",
            opening=eat_opening,
            movement=eat_movement,
            ending=eat_ending,
            level=0,
            kind="total",
        )
        rows.append(eat)
        self.metrics.earnings_after_tax_opening = eat.opening
        self.metrics.earnings_after_tax_movement = eat.movement
        self.metrics.earnings_after_tax_ending = eat.ending
        return rows, eat

    @staticmethod
    def _subtotal_row(
        description_id: str,
        description_en: str,
        description_zh: str,
        totals: dict[str, tuple[Decimal, Decimal, Decimal]],
        codes: tuple[str, ...],
    ) -> StatementRow:
        return StatementRow(
            code="",
            description_id=description_id,
            description_en=description_en,
            description_zh=description_zh,
            opening=sum_decimals(totals.get(code, (ZERO, ZERO, ZERO))[0] for code in codes),
            movement=sum_decimals(totals.get(code, (ZERO, ZERO, ZERO))[1] for code in codes),
            ending=sum_decimals(totals.get(code, (ZERO, ZERO, ZERO))[2] for code in codes),
            kind="subtotal",
        )

    def _build_balance_sheet(
        self, trial_balance: list[TrialBalanceRow], earnings_after_tax: StatementRow
    ) -> list[StatementRow]:
        nodes, children = self._build_hierarchy("BS")
        defaults = {
            "1": ("Aset", "Assets", "资产"),
            "2": ("Liabilitas", "Liabilities", "负债"),
            "3": ("Ekuitas", "Equity", "所有者权益"),
        }
        mapped_bs_accounts = {
            code
            for code, coa in self.coa_by_code.items()
            if normalize_code(coa.get("BS Classification (Code)"))
        }
        fallback: dict[str, list[str]] = {"1": [], "2": [], "3": []}
        for row in trial_balance:
            if row.account_code in mapped_bs_accounts:
                continue
            side = self._infer_statement_side(row.account_code, row.account_name)
            if side == "asset":
                fallback["1"].append(row.account_code)
            elif side == "liability":
                fallback["2"].append(row.account_code)
            elif side == "equity":
                fallback["3"].append(row.account_code)

        def value_for_accounts(accounts: Iterable[str], main_code: str) -> tuple[Decimal, Decimal]:
            opening_raw, _, _, ending_raw, _, _ = self._sum_tb(accounts)
            multiplier = Decimal("1") if main_code == "1" else Decimal("-1")
            return opening_raw * multiplier, ending_raw * multiplier

        rows: list[StatementRow] = []
        main_values: dict[str, tuple[Decimal, Decimal]] = {}
        for main_code in ("1", "2", "3"):
            node = nodes.get(main_code)
            if node is None:
                descriptions = defaults[main_code]
                node = HierarchyNode(
                    code=main_code,
                    level=0,
                    description_id=descriptions[0],
                    description_en=descriptions[1],
                    description_zh=descriptions[2],
                    accounts=set(),
                    main=main_code,
                )
            opening, ending = value_for_accounts(node.accounts, main_code)
            fallback_opening, fallback_ending = value_for_accounts(fallback[main_code], main_code)
            opening += fallback_opening
            ending += fallback_ending
            if main_code == "3":
                ending += earnings_after_tax.ending
            main_values[main_code] = (opening, ending)
            rows.append(
                StatementRow(
                    code=main_code,
                    description_id=node.description_id or defaults[main_code][0],
                    description_en=node.description_en or defaults[main_code][1],
                    description_zh=node.description_zh or defaults[main_code][2],
                    opening=opening,
                    ending=ending,
                    level=0,
                    kind="section",
                )
            )
            for sub1_code in children.get(main_code, []):
                sub1 = nodes[sub1_code]
                sub_opening, sub_ending = value_for_accounts(sub1.accounts, main_code)
                rows.append(
                    StatementRow(
                        code=sub1.code,
                        description_id=sub1.description_id or sub1.description_en,
                        description_en=sub1.description_en or sub1.description_id,
                        description_zh=sub1.description_zh,
                        opening=sub_opening,
                        ending=sub_ending,
                        level=1,
                    )
                )
                for sub2_code in children.get(sub1_code, []):
                    sub2 = nodes[sub2_code]
                    sub2_opening, sub2_ending = value_for_accounts(sub2.accounts, main_code)
                    rows.append(
                        StatementRow(
                            code=sub2.code,
                            description_id=sub2.description_id or sub2.description_en,
                            description_en=sub2.description_en or sub2.description_id,
                            description_zh=sub2.description_zh,
                            opening=sub2_opening,
                            ending=sub2_ending,
                            level=2,
                        )
                    )
            if fallback[main_code]:
                descriptions = {
                    "1": ("Aset belum dipetakan", "Unmapped assets", "未映射资产"),
                    "2": ("Liabilitas belum dipetakan", "Unmapped liabilities", "未映射负债"),
                    "3": ("Ekuitas belum dipetakan", "Unmapped equity", "未映射权益"),
                }[main_code]
                rows.append(
                    StatementRow(
                        code=f"{main_code}.U",
                        description_id=descriptions[0],
                        description_en=descriptions[1],
                        description_zh=descriptions[2],
                        opening=fallback_opening,
                        ending=fallback_ending,
                        level=1,
                        kind="check",
                    )
                )
                self.issues.append(
                    Issue(
                        "WARNING",
                        "Balance Sheet",
                        ", ".join(fallback[main_code]),
                        "Akun tanpa klasifikasi COA disajikan sebagai kelompok 'belum dipetakan'.",
                    )
                )
            if main_code == "3":
                rows.append(
                    StatementRow(
                        code="",
                        description_id="Laba setelah pajak periode berjalan",
                        description_en="Current-period earnings after tax",
                        description_zh="本期税后利润",
                        opening=ZERO,
                        ending=earnings_after_tax.ending,
                        level=1,
                        kind="subtotal",
                    )
                )

        total_le_opening = main_values["2"][0] + main_values["3"][0]
        total_le_ending = main_values["2"][1] + main_values["3"][1]
        rows.append(
            StatementRow(
                code="",
                description_id="Total Liabilitas dan Ekuitas",
                description_en="Total Liabilities and Equity",
                description_zh="负债与权益总额",
                opening=total_le_opening,
                ending=total_le_ending,
                kind="total",
            )
        )
        difference_opening = main_values["1"][0] - total_le_opening
        difference_ending = main_values["1"][1] - total_le_ending
        rows.append(
            StatementRow(
                code="",
                description_id="Selisih keseimbangan",
                description_en="Balance check",
                description_zh="平衡检查",
                opening=difference_opening,
                ending=difference_ending,
                kind="check",
            )
        )
        self.metrics.assets_opening = main_values["1"][0]
        self.metrics.assets_ending = main_values["1"][1]
        self.metrics.liabilities_equity_opening = total_le_opening
        self.metrics.liabilities_equity_ending = total_le_ending
        self.metrics.bs_difference_opening = difference_opening
        self.metrics.bs_difference_ending = difference_ending
        if abs(difference_opening) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Balance Sheet",
                    "Saldo awal",
                    f"Aset tidak sama dengan liabilitas dan ekuitas; selisih {difference_opening}.",
                )
            )
        if abs(difference_ending) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Balance Sheet",
                    "Saldo akhir",
                    f"Aset tidak sama dengan liabilitas dan ekuitas; selisih {difference_ending}.",
                )
            )
        return rows

    def _build_cash_flow(
        self, trial_balance: list[TrialBalanceRow]
    ) -> tuple[list[StatementRow], list[CashFlowMappingAudit]]:
        table = self.tables["cash_flow_master"]
        nodes: dict[str, HierarchyNode] = {}
        children: dict[str, list[str]] = defaultdict(list)
        item_order: list[str] = []
        class_order: list[str] = []
        sub_order: dict[str, list[str]] = defaultdict(list)

        for record in table.rows:
            item = normalize_code(record.get("Cash Flow Item (Code)"))
            sub = normalize_code(record.get("Cash Flow Sub-Classification (Code)"))
            main = normalize_code(record.get("Cash Flow Classification (Code)"))
            if not item:
                continue
            if main and main not in class_order:
                class_order.append(main)
            if sub and sub not in sub_order[main]:
                sub_order[main].append(sub)
            if item not in item_order:
                item_order.append(item)
            if main not in nodes:
                nodes[main] = HierarchyNode(
                    code=main,
                    level=0,
                    description_id=clean_text(record.get("Cash Flow Classification (Indonesia)")),
                    description_en=clean_text(record.get("Cash Flow Classification (English)")),
                    description_zh=clean_text(record.get("Cash Flow Classification (Chinese)")),
                    accounts=set(),
                    main=main,
                )
            if sub not in nodes:
                nodes[sub] = HierarchyNode(
                    code=sub,
                    level=1,
                    description_id=clean_text(record.get("Cash Flow Sub-Classification (Indonesia)")),
                    description_en=clean_text(record.get("Cash Flow Sub-Classification (English)")),
                    description_zh=clean_text(record.get("Cash Flow Sub-Classification (Chinese)")),
                    accounts=set(),
                    parent=main,
                    main=main,
                )
                children[main].append(sub)
            if item not in nodes:
                nodes[item] = HierarchyNode(
                    code=item,
                    level=2,
                    description_id=clean_text(record.get("Cash Flow Item (Indonesia)")),
                    description_en=clean_text(record.get("Cash Flow Item (English)")),
                    description_zh=clean_text(record.get("Cash Flow Item (Chinese)")),
                    accounts=set(),
                    parent=sub,
                    main=main,
                )
                children[sub].append(item)

        legacy_map = {str(index): code for index, code in enumerate(item_order, start=1)}
        direct: dict[str, Decimal] = defaultdict(lambda: ZERO)
        audit: list[CashFlowMappingAudit] = []
        cash_accounts = {
            code
            for code, coa in self.coa_by_code.items()
            if normalize_code(coa.get("BS Sub-Classification 2 (Code)")) == "1.1.1"
        }
        for row in self.journal_rows:
            source_code = normalize_code(row.get("Cash Flow Code"))
            account_code = row["Account Code"]
            amount = row["Debit-IDR"] - row["Credit-IDR"]
            reference = f"{row['Voucher No.']} / baris {row.get('_source_row', '?')}"
            if source_code:
                mapped = ""
                method = ""
                if source_code in item_order:
                    mapped = source_code
                    method = "exact-item"
                elif source_code.isdigit() and source_code in legacy_map:
                    mapped = legacy_map[source_code]
                    method = "legacy-sequential"
                elif source_code in nodes:
                    mapped = source_code
                    method = "exact-hierarchy"
                if mapped:
                    direct[mapped] += amount
                    status = "OK"
                    if method == "legacy-sequential":
                        self.issues.append(
                            Issue(
                                "INFO",
                                "Cash Flow",
                                reference,
                                f"Cash Flow Code {source_code} dipetakan otomatis ke {mapped} berdasarkan urutan Cash Flow Master.",
                            )
                        )
                    if account_code not in cash_accounts:
                        self.issues.append(
                            Issue(
                                "WARNING",
                                "Cash Flow",
                                reference,
                                "Cash Flow Code diisi pada akun yang tidak terpetakan sebagai kas/bank (BS code 1.1.1).",
                            )
                        )
                else:
                    status = "UNMAPPED"
                    self.issues.append(
                        Issue("WARNING", "Cash Flow", reference, f"Cash Flow Code {source_code} tidak dikenali.")
                    )
                audit.append(
                    CashFlowMappingAudit(
                        journal_row=int(row.get("_source_row", 0) or 0),
                        voucher_no=row["Voucher No."],
                        source_code=source_code,
                        mapped_code=mapped,
                        method=method,
                        amount=amount,
                        status=status,
                    )
                )
            elif account_code in cash_accounts and amount != ZERO:
                self.issues.append(
                    Issue(
                        "WARNING",
                        "Cash Flow",
                        reference,
                        "Transaksi kas/bank tidak memiliki Cash Flow Code dan tidak masuk movement laporan arus kas.",
                    )
                )

        ancestors: dict[str, set[str]] = {}
        for code in nodes:
            lineage = {code}
            parent = nodes[code].parent
            while parent:
                lineage.add(parent)
                parent = nodes[parent].parent if parent in nodes else ""
            ancestors[code] = lineage

        movement_by_code: dict[str, Decimal] = {}
        for target in nodes:
            movement_by_code[target] = sum_decimals(
                amount for source, amount in direct.items() if target in ancestors.get(source, {source})
            )

        beginning_table = self.tables["beginning_cash_flow"]
        opening_map: dict[str, Decimal] = {}
        opening_present: set[str] = set()
        for record in beginning_table.rows:
            code = normalize_code(record.get("Code"))
            if not code:
                continue
            opening_present.add(code)
            opening_map[code] = opening_map.get(code, ZERO) + to_decimal(
                record.get("Opening Balance (IDR)"),
                issues=self.issues,
                category=beginning_table.label,
                reference=f"baris {record.get('_source_row', '?')} / code {code}",
                field="Opening Balance (IDR)",
            )

        def opening_for(code: str) -> Decimal:
            if code in opening_present:
                return opening_map.get(code, ZERO)
            descendants = [item for item in item_order if code in ancestors.get(item, set())]
            return sum_decimals(opening_map.get(item, ZERO) for item in descendants)

        rows: list[StatementRow] = []
        main_rows: dict[str, StatementRow] = {}
        for main in class_order:
            node = nodes[main]
            main_row = StatementRow(
                code=main,
                description_id=node.description_id,
                description_en=node.description_en,
                description_zh=node.description_zh,
                opening=opening_for(main),
                movement=movement_by_code.get(main, ZERO),
                ending=opening_for(main) + movement_by_code.get(main, ZERO),
                level=0,
                kind="section",
            )
            rows.append(main_row)
            main_rows[main] = main_row
            for sub in sub_order[main]:
                sub_node = nodes[sub]
                sub_opening = opening_for(sub)
                sub_movement = movement_by_code.get(sub, ZERO)
                rows.append(
                    StatementRow(
                        code=sub,
                        description_id=sub_node.description_id,
                        description_en=sub_node.description_en,
                        description_zh=sub_node.description_zh,
                        opening=sub_opening,
                        movement=sub_movement,
                        ending=sub_opening + sub_movement,
                        level=1,
                    )
                )
                for item in children.get(sub, []):
                    item_node = nodes[item]
                    item_opening = opening_for(item)
                    item_movement = movement_by_code.get(item, ZERO)
                    rows.append(
                        StatementRow(
                            code=item,
                            description_id=item_node.description_id,
                            description_en=item_node.description_en,
                            description_zh=item_node.description_zh,
                            opening=item_opening,
                            movement=item_movement,
                            ending=item_opening + item_movement,
                            level=2,
                        )
                    )

        total_movement = sum_decimals(row.movement for row in main_rows.values())
        total_opening = sum_decimals(row.opening for row in main_rows.values())
        rows.append(
            StatementRow(
                code="",
                description_id="Total arus kas",
                description_en="Total cash flow movement",
                description_zh="现金流变动总额",
                opening=total_opening,
                movement=total_movement,
                ending=total_opening + total_movement,
                kind="total",
            )
        )

        tb_cash_opening = sum_decimals(
            self.trial_by_code[code].opening_idr for code in cash_accounts if code in self.trial_by_code
        )
        tb_cash_ending = sum_decimals(
            self.trial_by_code[code].ending_idr for code in cash_accounts if code in self.trial_by_code
        )
        if "5" in opening_present:
            cash_beginning = opening_map["5"]
        elif "4" in opening_present:
            cash_beginning = opening_map["4"]
        else:
            cash_beginning = tb_cash_opening
            self.issues.append(
                Issue(
                    "INFO",
                    "Cash Flow",
                    "Kas awal",
                    "Code 5/4 tidak ditemukan pada Beginning Cash Flow Statement; kas awal memakai Trial Balance.",
                )
            )
        cash_ending = cash_beginning + total_movement
        rows.append(
            StatementRow(
                code="4",
                description_id="Kas dan bank di awal periode",
                description_en="Cash at beginning of period",
                description_zh="期初现金余额",
                opening=opening_map.get("4", ZERO),
                movement=cash_beginning,
                ending=cash_beginning,
                kind="subtotal",
            )
        )
        rows.append(
            StatementRow(
                code="5",
                description_id="Kas dan bank di akhir periode",
                description_en="Cash at ending of period",
                description_zh="期末现金余额",
                opening=cash_beginning,
                movement=total_movement,
                ending=cash_ending,
                kind="total",
            )
        )
        self.metrics.cash_beginning = cash_beginning
        self.metrics.cash_ending = cash_ending
        self.metrics.tb_cash_opening = tb_cash_opening
        self.metrics.tb_cash_ending = tb_cash_ending
        self.metrics.cash_reconciliation_opening = cash_beginning - tb_cash_opening
        self.metrics.cash_reconciliation_ending = cash_ending - tb_cash_ending
        if abs(self.metrics.cash_reconciliation_opening) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Cash Flow",
                    "Rekonsiliasi kas awal",
                    f"Kas awal arus kas berbeda dari saldo kas/bank Trial Balance sebesar {self.metrics.cash_reconciliation_opening}.",
                )
            )
        if abs(self.metrics.cash_reconciliation_ending) > MONEY_EPSILON:
            self.issues.append(
                Issue(
                    "WARNING",
                    "Cash Flow",
                    "Rekonsiliasi kas akhir",
                    f"Kas akhir arus kas berbeda dari saldo kas/bank Trial Balance sebesar {self.metrics.cash_reconciliation_ending}.",
                )
            )
        return rows, audit

    def _build_ledger(
        self,
        *,
        report_key: str,
        beginning: InputTable,
        party_column: str,
        overrides: set[str],
        trial_balance: list[TrialBalanceRow],
    ) -> list[LedgerRow]:
        account_codes = {
            normalize_code(record.get("Account Code"))
            for record in beginning.rows
            if normalize_code(record.get("Account Code"))
        }
        account_codes |= overrides
        if not account_codes:
            keywords = DETAIL_KEYWORDS[report_key]
            for row in self.journal_rows:
                account_name = clean_text(row.get("Account Name")).casefold()
                coa_name = clean_text(
                    self.coa_by_code.get(row["Account Code"], {}).get("Account Name (English)")
                ).casefold()
                combined = f"{account_name} {coa_name}"
                if any(keyword in combined for keyword in keywords):
                    account_codes.add(row["Account Code"])
            if account_codes:
                self.issues.append(
                    Issue(
                        "INFO",
                        f"{report_key.upper()} Report",
                        ", ".join(sorted(account_codes, key=natural_code_key)),
                        "Account code diinferensikan dari nama akun karena file saldo awal tidak berisi data.",
                    )
                )
        if not account_codes:
            self.issues.append(
                Issue(
                    "WARNING",
                    f"{report_key.upper()} Report",
                    "Account Code",
                    "Tidak ada account code yang dapat diidentifikasi; laporan hanya berisi header.",
                )
            )
            return []

        beginning_map: dict[tuple[str, str], dict[str, Any]] = {}
        for record in beginning.rows:
            code = normalize_code(record.get("Account Code"))
            if not code or code not in account_codes:
                continue
            party_display = clean_text(record.get(party_column)) or "Tanpa Nama / Unspecified"
            party_key = party_display.casefold()
            key = (code, party_key)
            opening_idr = to_decimal(
                record.get("Opening Balance (IDR)"),
                issues=self.issues,
                category=beginning.label,
                reference=f"baris {record.get('_source_row', '?')} / {code} / {party_display}",
                field="Opening Balance (IDR)",
            )
            opening_fx = to_decimal(
                record.get("Opening Balance (FX)"),
                issues=self.issues,
                category=beginning.label,
                reference=f"baris {record.get('_source_row', '?')} / {code} / {party_display}",
                field="Opening Balance (FX)",
            )
            if key in beginning_map:
                beginning_map[key]["opening_idr"] += opening_idr
                beginning_map[key]["opening_fx"] += opening_fx
                self.issues.append(
                    Issue(
                        "WARNING",
                        beginning.label,
                        f"{code} / {party_display}",
                        "Saldo awal duplikat dijumlahkan.",
                    )
                )
            else:
                beginning_map[key] = {
                    "party": party_display,
                    "account_name": clean_text(record.get("Account Name")),
                    "opening_idr": opening_idr,
                    "opening_fx": opening_fx,
                }

        transactions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in self.journal_rows:
            code = row["Account Code"]
            if code not in account_codes:
                continue
            party_display = clean_text(row.get("Third Party")) or "Tanpa Nama / Unspecified"
            key = (code, party_display.casefold())
            transactions[key].append(row)
            if not clean_text(row.get("Third Party")):
                self.issues.append(
                    Issue(
                        "WARNING",
                        f"{report_key.upper()} Report",
                        f"{row['Voucher No.']} / baris {row.get('_source_row', '?')}",
                        "Third Party kosong; transaksi dikelompokkan sebagai 'Tanpa Nama / Unspecified'.",
                    )
                )

        keys = set(beginning_map) | set(transactions)
        result: list[LedgerRow] = []
        ending_by_account: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for code, party_key in sorted(keys, key=lambda item: (natural_code_key(item[0]), item[1])):
            beginning_data = beginning_map.get((code, party_key), {})
            tx_rows = sorted(
                transactions.get((code, party_key), []),
                key=lambda row: (row["Date"], row["Voucher No."], int(row.get("_source_row", 0) or 0)),
            )
            party = beginning_data.get("party") or (
                clean_text(tx_rows[0].get("Third Party")) if tx_rows else "Tanpa Nama / Unspecified"
            )
            coa = self.coa_by_code.get(code, {})
            account_name = (
                clean_text(beginning_data.get("account_name"))
                or clean_text(coa.get("Account Name (Indonesia)"))
                or (clean_text(tx_rows[0].get("Account Name")) if tx_rows else "Unmapped account")
            )
            opening_idr = beginning_data.get("opening_idr", ZERO)
            opening_fx = beginning_data.get("opening_fx", ZERO)
            running_idr = opening_idr
            running_fx = opening_fx
            result.append(
                LedgerRow(
                    account_code=code,
                    account_name=account_name,
                    party=party,
                    opening_idr=opening_idr,
                    opening_fx=opening_fx,
                    transaction_date=None,
                    bl_no="",
                    remarks="",
                    description="Opening Balance",
                    debit_idr=ZERO,
                    debit_fx=ZERO,
                    credit_idr=ZERO,
                    credit_fx=ZERO,
                    ending_idr=running_idr,
                    ending_fx=running_fx,
                )
            )
            for tx in tx_rows:
                running_idr += tx["Debit-IDR"] - tx["Credit-IDR"]
                running_fx += tx["Debit-FX"] - tx["Credit-FX"]
                result.append(
                    LedgerRow(
                        account_code=code,
                        account_name=account_name,
                        party=party,
                        opening_idr=None,
                        opening_fx=None,
                        transaction_date=tx["Date"],
                        bl_no=clean_text(tx.get("BL No.")),
                        remarks=clean_text(tx.get("Remarks")),
                        description=clean_text(tx.get("Description")),
                        debit_idr=tx["Debit-IDR"],
                        debit_fx=tx["Debit-FX"],
                        credit_idr=tx["Credit-IDR"],
                        credit_fx=tx["Credit-FX"],
                        ending_idr=running_idr,
                        ending_fx=running_fx,
                    )
                )
            ending_by_account[code] += running_idr

        tb_by_code = {row.account_code: row for row in trial_balance}
        for code in sorted(account_codes, key=natural_code_key):
            ledger_ending = ending_by_account.get(code, ZERO)
            tb_ending = tb_by_code.get(code, TrialBalanceRow(code, "")).ending_idr
            difference = ledger_ending - tb_ending
            if abs(difference) > MONEY_EPSILON:
                self.issues.append(
                    Issue(
                        "WARNING",
                        f"{report_key.upper()} Report",
                        code,
                        f"Saldo akhir detail berbeda dari Trial Balance sebesar {difference}.",
                    )
                )
        return result

    @staticmethod
    def _infer_statement_side(account_code: str, account_name: str) -> str:
        text = account_name.casefold()
        if any(word in text for word in ("payable", "utang", "hutang", "liabilit")):
            return "liability"
        if any(
            word in text
            for word in (
                "receivable",
                "piutang",
                "cash",
                "bank",
                "inventory",
                "asset",
                "advance payment",
                "prepaid",
            )
        ):
            return "asset"
        if any(word in text for word in ("capital", "equity", "retained", "modal", "ekuitas")):
            return "equity"
        first = account_code[:1]
        if first == "1":
            return "asset"
        if first == "2":
            return "liability"
        if first in {"3", "4"}:
            return "equity"
        return "pl"
