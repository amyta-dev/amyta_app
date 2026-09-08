from __future__ import annotations

from datetime import datetime
import re

import pdfplumber

from ..constants import MONTH_NAME_TO_NO
from ..exceptions import SPTParseError


NUMBER_RE = re.compile(r"[-+]?\(?\d[\d.,]*\)?")
DATE_RE = re.compile(r"\b(\d{1,2})[\-/](\d{1,2})[\-/](20\d{2})\b")
MONTH_YEAR_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(MONTH_NAME_TO_NO, key=len, reverse=True)) + r")\s+(20\d{2})\b",
    re.IGNORECASE,
)


def extract_pdf_pages(file_obj):
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    pages = []
    try:
        with pdfplumber.open(file_obj) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                tables = page.extract_tables() or []
                pages.append({"page": page_no, "text": text, "tables": tables})
    except Exception as exc:
        raise SPTParseError(f"PDF tidak dapat dibaca: {exc}") from exc
    if not pages:
        raise SPTParseError("PDF tidak memiliki halaman yang dapat dibaca.")
    return pages


def clean_number(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("Rp", "").replace(" ", "")
    # Indonesian documents generally use dots as thousands separators. If both
    # dot and comma exist, comma is treated as decimal separator.
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        # A single dot followed by exactly three digits is normally thousands.
        parts = text.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            text = "".join(parts)
    text = re.sub(r"[^0-9.+-]", "", text)
    if not text:
        return None
    try:
        value = float(text)
        return -value if negative else value
    except ValueError:
        return None


def parse_date(value):
    if isinstance(value, datetime):
        return value
    match = DATE_RE.search(str(value or ""))
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def find_month_year(text):
    match = MONTH_YEAR_RE.search((text or "").lower())
    if match:
        month_name, year = match.groups()
        return MONTH_NAME_TO_NO[month_name.lower()], int(year)
    masa = re.search(r"Masa\s+Pajak\s*[:\-]?\s*(\d{1,2}).{0,30}?Tahun\s+Pajak\s*[:\-]?\s*(20\d{2})", text or "", re.I | re.S)
    if masa:
        month, year = int(masa.group(1)), int(masa.group(2))
        if 1 <= month <= 12:
            return month, year
    return None, None


def value_after_label(text, aliases, max_chars=120):
    for alias in aliases:
        pattern = re.compile(re.escape(alias) + r"\s*[:\-]?\s*([^\n]{1," + str(max_chars) + r"})", re.I)
        match = pattern.search(text or "")
        if match:
            return match.group(1).strip()
    return None


def number_after_label(text, aliases):
    raw = value_after_label(text, aliases)
    if raw:
        match = NUMBER_RE.search(raw)
        if match:
            return clean_number(match.group(0))
    return None


def date_after_label(text, aliases):
    raw = value_after_label(text, aliases)
    return parse_date(raw) if raw else None


def ntpn_values(text):
    values = re.findall(r"\b[A-Z0-9]{16}\b", (text or "").upper())
    return list(dict.fromkeys(values))


def group_pages_by_period(pages):
    groups = []
    current = None
    for page in pages:
        month, year = find_month_year(page["text"])
        key = (month, year) if month and year else None
        if key and (current is None or current["key"] != key):
            current = {"key": key, "pages": []}
            groups.append(current)
        if current is None:
            current = {"key": key, "pages": []}
            groups.append(current)
        current["pages"].append(page)
    return groups


def combined_text(group):
    return "\n".join(page["text"] for page in group["pages"])
