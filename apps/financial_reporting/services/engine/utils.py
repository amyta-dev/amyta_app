from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from dateutil import parser as date_parser
from openpyxl.utils.datetime import from_excel

from .models import Issue, ZERO

_HEADER_RE = re.compile(r"[^a-z0-9]+")
_CODE_PART_RE = re.compile(r"(\d+|[^\d]+)")


def normalize_header(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    return _HEADER_RE.sub(" ", text).strip()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return unicodedata.normalize("NFKC", str(value)).strip()


def normalize_code(value: Any, number_format: str | None = None) -> str:
    """Return a stable text representation for account/classification codes.

    Excel often stores codes as numbers. The function preserves explicit decimal
    places from the cell number format when possible and avoids scientific
    notation. It also keeps text codes (including leading zeroes) unchanged.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, datetime):
        # A code accidentally formatted as a date cannot be recovered perfectly.
        # ISO text is safer than silently converting it to another number.
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int):
        if number_format and re.fullmatch(r"0+", number_format.strip()):
            return f"{value:0{len(number_format.strip())}d}"
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        fmt = (number_format or "").split(";")[0]
        decimal_match = re.search(r"0\.([0#]+)", fmt)
        if decimal_match:
            places = len(decimal_match.group(1))
            return f"{value:.{places}f}"
        dec = Decimal(str(value))
        if dec == dec.to_integral_value():
            return str(dec.quantize(Decimal("1")))
        return format(dec.normalize(), "f")
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(value.quantize(Decimal("1")))
        return format(value.normalize(), "f")

    text = clean_text(value)
    if not text:
        return ""
    # Remove a harmless trailing .0 introduced by spreadsheet imports, but do
    # not collapse intentional codes such as 6601.10.
    if re.fullmatch(r"[-+]?\d+\.0", text):
        return text[:-2]
    return text


def natural_code_key(code: str) -> tuple:
    code = code or ""
    parts: list[tuple[int, Any]] = []
    for part in _CODE_PART_RE.findall(code):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part.casefold()))
    return tuple(parts)


def to_decimal(
    value: Any,
    *,
    issues: list[Issue] | None = None,
    category: str = "Data",
    reference: str = "",
    field: str = "nilai",
) -> Decimal:
    if value in (None, ""):
        return ZERO
    if isinstance(value, bool):
        if issues is not None:
            issues.append(Issue("WARNING", category, reference, f"{field} berupa boolean; dianggap 0."))
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            if issues is not None:
                issues.append(Issue("ERROR", category, reference, f"{field} bukan angka yang valid."))
            return ZERO
        return Decimal(str(value))

    text = clean_text(value)
    if not text or text in {"-", "–", "—"}:
        return ZERO
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = re.sub(r"(?i)\b(idr|rp|usd|rmb|cny)\b", "", text)
    text = text.replace(" ", "").replace("'", "")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        right = text.rsplit(",", 1)[1]
        if len(right) <= 4:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        # Multiple dots are almost certainly thousand separators except the last.
        if text.count(".") > 1:
            head, tail = text.rsplit(".", 1)
            text = head.replace(".", "") + "." + tail

    text = re.sub(r"[^0-9eE+\-.]", "", text)
    try:
        result = Decimal(text)
        return -result if negative else result
    except (InvalidOperation, ValueError):
        if issues is not None:
            issues.append(Issue("ERROR", category, reference, f"{field} '{value}' tidak dapat dibaca sebagai angka."))
        return ZERO


def parse_date_value(
    value: Any,
    *,
    epoch: datetime | None = None,
    issues: list[Issue] | None = None,
    category: str = "Journal Voucher",
    reference: str = "",
    field: str = "Date",
) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            dt = from_excel(value, epoch=epoch) if epoch is not None else from_excel(value)
            return dt.date() if isinstance(dt, datetime) else dt
        except Exception:
            pass
    text = clean_text(value)
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=False).date()
    except (ValueError, OverflowError, TypeError):
        if issues is not None:
            issues.append(Issue("ERROR", category, reference, f"{field} '{text}' tidak dapat dibaca sebagai tanggal."))
        return None


def safe_excel_text(value: Any) -> str:
    text = clean_text(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str, default: str = "laporan-keuangan") -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    return normalized or default


def parse_code_list(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        normalize_code(part.strip())
        for part in re.split(r"[,;\n]+", value)
        if normalize_code(part.strip())
    }


def sum_decimals(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)
