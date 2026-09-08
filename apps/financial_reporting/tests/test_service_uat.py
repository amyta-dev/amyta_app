from datetime import date
from pathlib import Path

from apps.financial_reporting.services.engine.processor import AccountingProcessor


def test_engine_with_uat_files():
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    if not fixture_dir.exists():
        return
    paths = {
        "cash_flow_master": fixture_dir / "Cash Flow Master.xlsx",
        "coa_master": fixture_dir / "COA Master.xlsx",
        "beginning_trial_balance": fixture_dir / "Beginning Trial Balance.xlsx",
        "journal_voucher": fixture_dir / "Journal Voucher.xlsx",
        "beginning_ar": fixture_dir / "Beginning AR Report.xlsx",
        "beginning_ap": fixture_dir / "Beginning AP Report.xlsx",
        "beginning_advance": fixture_dir / "Beginning Advance Payment Report.xlsx",
        "beginning_cash_flow": fixture_dir / "Beginning Cash Flow Statement.xlsx",
    }
    bundle = AccountingProcessor(
        client_name="UAT Client",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        input_paths=paths,
        strict=True,
    ).process()
    assert not [issue for issue in bundle.issues if issue.severity == "ERROR"]
