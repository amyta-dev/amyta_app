from __future__ import annotations

APP_NAME = "Generator Laporan Keuangan"
APP_VERSION = "1.1.0"
DEFAULT_MAX_UPLOAD_MB = 80
MONEY_TOLERANCE = "0.01"
FX_TOLERANCE = "0.01"

NAVY = "0F2D4A"
NAVY_LIGHT = "DCE6F1"
YELLOW = "FFF200"
YELLOW_LIGHT = "FFF9C4"
WHITE = "FFFFFF"
BLACK = "000000"
RED = "C00000"
GREEN = "008000"
GREY = "E7E6E6"
LIGHT_GREY = "F3F4F6"
ORANGE = "F4B183"

NUMBER_FORMAT = '#,##0.00;[Red](#,##0.00);-'
DATE_FORMAT = 'dd-mmm-yyyy'

FILE_FIELDS = {
    "cash_flow_master": "Cash Flow Master",
    "coa_master": "COA Master",
    "beginning_trial_balance": "Beginning Trial Balance",
    "journal_voucher": "Journal Voucher",
    "beginning_ar": "Beginning AR Report",
    "beginning_ap": "Beginning AP Report",
    "beginning_advance": "Beginning Advance Payment Report",
    "beginning_cash_flow": "Beginning Cash Flow Statement",
}

# Canonical columns and accepted aliases. Matching ignores case, punctuation,
# repeated whitespace, and leading/trailing spaces.
TABLE_SPECS = {
    "cash_flow_master": {
        "required": [
            "Cash Flow Item (Code)",
            "Cash Flow Sub-Classification (Code)",
            "Cash Flow Classification (Code)",
        ],
        "columns": [
            "Cash Flow Item (Indonesia)",
            "Cash Flow Sub-Classification (Indonesia)",
            "Cash Flow Classification (Indonesia)",
            "Cash Flow Item (Code)",
            "Cash Flow Sub-Classification (Code)",
            "Cash Flow Classification (Code)",
            "Cash Flow Item (English)",
            "Cash Flow Sub-Classification (English)",
            "Cash Flow Classification (English)",
            "Cash Flow Item (Chinese)",
            "Cash Flow Sub-Classification (Chinese)",
            "Cash Flow Classification (Chinese)",
        ],
        "key": "Cash Flow Item (Code)",
        "code_columns": {
            "Cash Flow Item (Code)",
            "Cash Flow Sub-Classification (Code)",
            "Cash Flow Classification (Code)",
        },
        "date_columns": set(),
    },
    "coa_master": {
        "required": [
            "Account Code",
            "Account Name (Indonesia)",
            "BS Classification (Code)",
            "IS Classification (Code)",
        ],
        "columns": [
            "Account Code",
            "Account Name (Indonesia)",
            "BS Sub-Classification 2 (Indonesia)",
            "BS Sub-Classification 1 (Indonesia)",
            "BS Classification (Indonesia)",
            "IS Sub-Classification 2 (Indonesia)",
            "IS Sub-Classification 1 (Indonesia)",
            "IS Classification (Indonesia)",
            "Account Name (English)",
            "BS Sub-Classification 2 (English)",
            "BS Sub-Classification 2 (Code)",
            "BS Sub-Classification 1 (English)",
            "BS Sub-Classification 1 (Code)",
            "BS Classification (English)",
            "BS Classification (Code)",
            "IS Sub-Classification 2 (English)",
            "IS Sub-Classification 2 (Code)",
            "IS Sub-Classification 1 (English)",
            "IS Sub-Classification 1 (Code)",
            "IS Classification (English)",
            "IS Classification (Code)",
            "Account Name (Chinese)",
            "BS Sub-Classification 2 (Chinese)",
            "BS Sub-Classification 1 (Chinese)",
            "BS Classification (Chinese)",
            "IS Sub-Classification 2 (Chinese)",
            "IS Sub-Classification 1 (Chinese)",
            "IS Classification (Chinese)",
        ],
        "key": "Account Code",
        "code_columns": {
            "Account Code",
            "BS Sub-Classification 2 (Code)",
            "BS Sub-Classification 1 (Code)",
            "BS Classification (Code)",
            "IS Sub-Classification 2 (Code)",
            "IS Sub-Classification 1 (Code)",
            "IS Classification (Code)",
        },
        "date_columns": set(),
    },
    "beginning_trial_balance": {
        "required": [
            "Account Code",
            "Account Name",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "columns": [
            "Account Code",
            "Account Name",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "key": "Account Code",
        "code_columns": {"Account Code"},
        "date_columns": set(),
    },
    "journal_voucher": {
        "required": [
            "Voucher No.",
            "Date",
            "Account Code",
            "Debit-IDR",
            "Credit-IDR",
        ],
        "columns": [
            "Voucher No.",
            "Date",
            "Period",
            "BL No.",
            "Remarks",
            "Description",
            "Account Code",
            "Account Name",
            "Debit-IDR",
            "Credit-IDR",
            "Debit-FX",
            "Credit-FX",
            "Cash Flow Code",
            "Third Party",
            "Comments",
        ],
        "key": "Account Code",
        "code_columns": {"Account Code", "Cash Flow Code"},
        "date_columns": {"Date", "Period"},
    },
    "beginning_ar": {
        "required": [
            "Account Code",
            "Account Name",
            "Customer",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "columns": [
            "Account Code",
            "Account Name",
            "Customer",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "key": "Account Code",
        "code_columns": {"Account Code"},
        "date_columns": set(),
    },
    "beginning_ap": {
        "required": [
            "Account Code",
            "Account Name",
            "Vendor",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "columns": [
            "Account Code",
            "Account Name",
            "Vendor",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "key": "Account Code",
        "code_columns": {"Account Code"},
        "date_columns": set(),
    },
    "beginning_advance": {
        "required": [
            "Account Code",
            "Account Name",
            "Vendor",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "columns": [
            "Account Code",
            "Account Name",
            "Vendor",
            "Opening Balance (IDR)",
            "Opening Balance (FX)",
        ],
        "key": "Account Code",
        "code_columns": {"Account Code"},
        "date_columns": set(),
    },
    "beginning_cash_flow": {
        "required": ["Code", "Opening Balance (IDR)"],
        "columns": [
            "Code",
            "Description (Indonesia)",
            "Description (English)",
            "Description (Chinese)",
            "Opening Balance (IDR)",
        ],
        "key": "Code",
        "code_columns": {"Code"},
        "date_columns": set(),
        "keep_blank_key_rows": True,
    },
}

HEADER_ALIASES = {
    "voucher no": "Voucher No.",
    "voucher number": "Voucher No.",
    "bl no": "BL No.",
    "bl number": "BL No.",
    "debit idr": "Debit-IDR",
    "credit idr": "Credit-IDR",
    "debit fx": "Debit-FX",
    "credit fx": "Credit-FX",
    "cashflow code": "Cash Flow Code",
    "cash flow item code": "Cash Flow Item (Code)",
    "cash flow sub classification code": "Cash Flow Sub-Classification (Code)",
    "cash flow classification code": "Cash Flow Classification (Code)",
    "opening balance idr": "Opening Balance (IDR)",
    "opening balance fx": "Opening Balance (FX)",
    "account code": "Account Code",
    "account name": "Account Name",
    "account name indonesia": "Account Name (Indonesia)",
    "third party": "Third Party",
}

DETAIL_KEYWORDS = {
    "ar": (
        "account receivable",
        "accounts receivable",
        "trade receivable",
        "piutang usaha",
        "piutang dagang",
    ),
    "ap": (
        "account payable",
        "accounts payable",
        "trade payable",
        "utang usaha",
        "hutang usaha",
        "utang dagang",
        "hutang dagang",
    ),
    "advance": (
        "advance payment",
        "advance payments",
        "supplier advance",
        "prepayment to supplier",
        "uang muka",
    ),
}
