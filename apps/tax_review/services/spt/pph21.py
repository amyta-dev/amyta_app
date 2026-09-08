from datetime import datetime
import re

from .base import (
    combined_text, date_after_label, extract_pdf_pages, group_pages_by_period,
    ntpn_values, number_after_label, value_after_label,
)
from ..constants import MONTHS_ID

PPH21_OLD_HEADERS = [
    "Bulan", "Tahun", "NPWP", "Status (Normal/Pembetulan)", "Objek Pajak",
    "Tanggal Lapor", "DPP PPh di SPT", "PPh di SPT", "PPh di SSP",
    "Tanggal Bayar di SSP", "NTPN", "Catatan",
]

PPH21_NEW_HEADERS = [
    "Bulan", "Tanggal Lapor", "PPh 21 yang Dipotong di SPT",
    "Kelebihan Penyetoran PPh Pasal 21 dari Masa Pajak Sebelumnya",
    "PPh Pasal 21 yang Kurang (Lebih) Disetor", "PPh 21 di SSP",
    "Tanggal Bayar di SSP", "NTPN", "Catatan",
]


def _status(text):
    m = re.search(r"Pembetulan\s*(?:ke)?[- ]?(\d+)", text, re.I)
    return f"Pembetulan ke-{m.group(1)}" if m else "Normal"


def _npwp(text):
    m = re.search(r"\b\d{2}[.]\d{3}[.]\d{3}[.]\d[-]\d{3}[.]\d{3}\b", text)
    return m.group(0) if m else None


def _payment_date(text):
    return date_after_label(text, ["Tanggal Bayar", "Tanggal Pembayaran", "Tanggal Setor", "Tanggal BPN"])


def parse_pph21_old(file_obj):
    rows = []
    for group in group_pages_by_period(extract_pdf_pages(file_obj)):
        text = combined_text(group)
        month, year = group["key"] or (None, None)
        if not year:
            continue
        # Without a fixed DJP PDF fixture we deliberately create one aggregate row
        # per masa pajak. Duplicating an aggregate SPT amount across several detected
        # object names would overstate the reconciliation.
        obj = value_after_label(text, ["Objek Pajak", "Jenis Penerima Penghasilan"]) or "PPh Pasal 21 (Agregat)"
        dpp = number_after_label(text, ["Jumlah Penghasilan Bruto", "DPP PPh", "Dasar Pengenaan Pajak", "DPP"])
        pph = number_after_label(text, ["PPh Pasal 21 Terutang", "PPh 21 Terutang", "PPh yang Dipotong", "PPh di SPT"])
        ssp = number_after_label(text, ["Jumlah Setor", "PPh di SSP", "Jumlah Pembayaran", "Nilai Pembayaran"])
        report_date = date_after_label(text, ["Tanggal Lapor", "Tanggal Pelaporan", "Tanggal Terima"])
        pay_date = _payment_date(text)
        ntpn = "\n".join(ntpn_values(text)) or None
        rows.append([
            datetime(year, month or 1, 1), year, _npwp(text), _status(text), obj,
            report_date, dpp, pph, ssp, pay_date, ntpn,
            None if any(v is not None for v in (dpp, pph, ssp)) else "Perlu review manual: angka SPT tidak terdeteksi otomatis.",
        ])
    return {"headers": PPH21_OLD_HEADERS, "rows": rows}

def parse_pph21_new(file_obj):
    rows = []
    for group in group_pages_by_period(extract_pdf_pages(file_obj)):
        text = combined_text(group)
        month, year = group["key"] or (None, None)
        if not year:
            continue
        pph = number_after_label(text, ["PPh Pasal 21 yang Dipotong", "PPh 21 yang Dipotong", "PPh Terutang"])
        excess = number_after_label(text, ["Kelebihan Penyetoran PPh Pasal 21 dari Masa Pajak Sebelumnya", "Kelebihan Penyetoran"])
        kurang = number_after_label(text, ["PPh Pasal 21 yang Kurang (Lebih) Disetor", "Kurang (Lebih) Disetor", "Kurang/Lebih Disetor"])
        ssp = number_after_label(text, ["PPh 21 di SSP", "Jumlah Setor", "Jumlah Pembayaran", "Nilai Pembayaran"])
        report_date = date_after_label(text, ["Tanggal Lapor", "Tanggal Pelaporan", "Tanggal Terima"])
        pay_date = _payment_date(text)
        ntpn = "\n".join(ntpn_values(text)) or None
        month_label = f"{MONTHS_ID.get(month, month)} {year}"
        rows.append([
            month_label, report_date, pph, excess or 0, kurang, ssp, pay_date, ntpn,
            None if any(v is not None for v in (pph, kurang, ssp)) else "Perlu review manual: angka SPT tidak terdeteksi otomatis.",
        ])
    return {"headers": PPH21_NEW_HEADERS, "rows": rows}
