from datetime import datetime
import re

from .base import combined_text, date_after_label, extract_pdf_pages, group_pages_by_period, ntpn_values, number_after_label

HEADERS = [
    "Bulan", "Tahun", "Status SPT (Normal/Pembetulan)", "Jenis Pajak",
    "Tanggal Lapor", "PPh di SPT", "PPh di SSP", "Tanggal Bayar di SSP",
    "NTPN", "Catatan",
]


def _status(text):
    m = re.search(r"Pembetulan\s*(?:ke)?[- ]?(\d+)", text, re.I)
    return f"Pembetulan ke-{m.group(1)}" if m else "Normal"


def _tax_types(text):
    # Prefer an explicit Jenis Pajak label. If the text mentions several tax types
    # but no row-level split is available, do not duplicate one aggregate amount.
    explicit = re.search(r"Jenis\s+Pajak\s*[:\-]?\s*([^\n]{1,60})", text, re.I)
    if explicit:
        value = explicit.group(1).strip()
        if re.search(r"23", value):
            return ["PPh Pasal 23"]
        if re.search(r"4\s*\(?2\)?|final", value, re.I):
            return ["PPh 4 ayat 2"]
        return [value]
    candidates = []
    patterns = [
        (r"PPh\s*(?:Pasal\s*)?23", "PPh Pasal 23"),
        (r"PPh\s*(?:Pasal\s*)?4\s*\(?2\)?|PPh\s*Final", "PPh 4 ayat 2"),
        (r"PPh\s*(?:Pasal\s*)?22", "PPh Pasal 22"),
        (r"PPh\s*(?:Pasal\s*)?26", "PPh Pasal 26"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text, re.I):
            candidates.append(label)
    if len(candidates) == 1:
        return candidates
    return ["PPh Unifikasi (Perlu Review)"]

def parse_unifikasi(file_obj):
    rows = []
    for group in group_pages_by_period(extract_pdf_pages(file_obj)):
        text = combined_text(group)
        month, year = group["key"] or (None, None)
        if not year:
            continue
        report_date = date_after_label(text, ["Tanggal Lapor", "Tanggal Pelaporan", "Tanggal Terima"])
        pay_date = date_after_label(text, ["Tanggal Bayar", "Tanggal Pembayaran", "Tanggal Setor"])
        ntpn = "\n".join(ntpn_values(text)) or None
        pph_spt = number_after_label(text, ["PPh di SPT", "PPh Terutang", "Jumlah PPh", "PPh yang Dipotong/Dipungut"])
        pph_ssp = number_after_label(text, ["PPh di SSP", "Jumlah Setor", "Jumlah Pembayaran", "Nilai Pembayaran"])
        for tax_type in _tax_types(text):
            rows.append([
                datetime(year, month or 1, 1), year, _status(text), tax_type,
                report_date, pph_spt, pph_ssp, pay_date, ntpn,
                None if any(v is not None for v in (pph_spt, pph_ssp)) else "Perlu review manual: nilai PPh tidak terdeteksi otomatis.",
            ])
    return {"headers": HEADERS, "rows": rows}
