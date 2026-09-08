from .pph21 import parse_pph21_old, parse_pph21_new
from .ppn import parse_ppn_old, parse_ppn_new
from .unifikasi import parse_unifikasi
from ..exceptions import SPTParseError


def parse_all(files):
    parsed = {
        "pph21_old": parse_pph21_old(files["spt_pph21_2024"]),
        "pph21_new": parse_pph21_new(files["spt_pph21_2025"]),
        "ppn_old": parse_ppn_old(files["spt_ppn_2024"]),
        "ppn_new": parse_ppn_new(files["spt_ppn_2025"]),
        "unifikasi": parse_unifikasi(files["spt_unifikasi"]),
    }
    labels = {
        "pph21_old": "SPT PPh 21 versi 2024 dan sebelumnya",
        "pph21_new": "SPT PPh 21 versi 2025 ke atas",
        "ppn_old": "SPT PPN versi 2024 dan sebelumnya",
        "ppn_new": "SPT PPN versi 2025 ke atas",
        "unifikasi": "SPT PPh Unifikasi",
    }
    empty = [labels[key] for key, value in parsed.items() if not value.get("rows")]
    if empty:
        raise SPTParseError(
            "Tidak ditemukan masa pajak yang dapat dikenali pada: " + ", ".join(empty) +
            ". Pastikan PDF memiliki text layer (bukan scan image) dan format periodenya terbaca."
        )
    return parsed


def _year_from_month_cell(value):
    if hasattr(value, "year"):
        return value.year
    text = str(value or "")
    for token in text.split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def unifikasi_paid_by_year(rows, tax_type_contains):
    result = {}
    needle = tax_type_contains.casefold()
    for row in rows:
        if len(row) < 7 or needle not in str(row[3] or "").casefold():
            continue
        year = row[1] or _year_from_month_cell(row[0])
        result[year] = result.get(year, 0.0) + float(row[5] or row[6] or 0)
    return result


def pph21_spt_by_year(old_rows, new_rows):
    result = {}
    for row in old_rows:
        year = row[1] if len(row) > 1 else _year_from_month_cell(row[0])
        result[year] = result.get(year, 0.0) + float(row[7] or 0)
    for row in new_rows:
        year = _year_from_month_cell(row[0])
        result[year] = result.get(year, 0.0) + float(row[2] or 0)
    return result


def ppn_object_by_year(old_rows, new_rows):
    result = {}
    for row in old_rows:
        year = row[1]
        result[year] = result.get(year, 0.0) + float(row[8] or 0)
    for row in new_rows:
        year = row[1]
        result[year] = result.get(year, 0.0) + float(row[11] or 0)
    return result
