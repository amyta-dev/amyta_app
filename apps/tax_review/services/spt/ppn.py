from .base import combined_text, date_after_label, extract_pdf_pages, group_pages_by_period, ntpn_values, number_after_label
from ..constants import MONTHS_ID

OLD_HEADERS = [
    "Bulan", "Tahun", "Status", "DPP Ekspor",
    "DPP Penyerahan yang PPN-nya harus dipungut sendiri",
    "DPP Penyerahan yang PPN-nya dipungut oleh Pemungut PPN",
    "DPP Penyerahan yang PPN-nya tidak dipungut",
    "DPP Penyerahan yang dibebaskan dari pengenaan PPN",
    "Jumlah Seluruh Penyerahan",
    "PPN Penyerahan yang PPN-nya harus dipungut sendiri",
    "PPN Penyerahan yang PPN-nya dipungut oleh Pemungut PPN",
    "PPN Penyerahan yang PPN-nya tidak dipungut",
    "PPN Penyerahan yang dibebaskan dari pengenaan PPN",
    "Jumlah PPN", "Pajak Masukan yang dapat diperhitungkan", "PPN kurang atau lebih bayar",
    "Status BPE", "Tanggal Pelaporan", "Tanggal Pembayaran", "Jumlah", "NTPN", "Catatan",
]

NEW_HEADERS = [
    "Bulan", "Tahun", "Status",
    "Harga Jual Ekspor BKP/BKP Tidak Berwujud/JKP",
    "Harga Jual Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan DPP Nilai Lain atau Besaran Tertentu",
    "Harga Jual Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri lainnya",
    "Harga Jual Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan Faktur Pajak yang dilaporkan secara digunggung",
    "Harga Jual Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut oleh Pemungut PPN",
    "Harga Jual Penyerahan yang mendapat fasilitas PPN atau PPnBM Tidak Dipungut",
    "Harga Jual Penyerahan yang mendapat fasilitas PPN atau PPnBM Dibebaskan",
    "Harga Jual Penyerahan yang mendapat fasilitas PPN atau PPnBM dengan Faktur Pajak yang dilaporkan secara digunggung",
    "Total Harga Jual",
    "DPP Nilai Lain Ekspor BKP/BKP Tidak Berwujud/JKP",
    "DPP Nilai Lain Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan DPP Nilai Lain Nilai Lain atau Besaran Tertentu",
    "DPP Nilai Lain Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri lainnya",
    "DPP Nilai Lain Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan Faktur Pajak yang dilaporkan secara digunggung",
    "DPP Nilai Lain Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut oleh Pemungut PPN",
    "DPP Nilai Lain Penyerahan yang mendapat fasilitas PPN atau PPnBM Tidak Dipungut",
    "DPP Nilai Lain Penyerahan yang mendapat fasilitas PPN atau PPnBM Dibebaskan",
    "DPP Nilai Lain Penyerahan yang mendapat fasilitas PPN atau PPnBM dengan Faktur Pajak yang dilaporkan secara digunggung",
    "Total DPP Nilai Lain",
    "PPN Ekspor BKP/BKP Tidak Berwujud/JKP",
    "PPN Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan DPP Nilai Lain atau Besaran Tertentu",
    "PPN Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri lainnya",
    "PPN Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri dengan Faktur Pajak yang dilaporkan secara digunggung",
    "PPN Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut oleh Pemungut PPN",
    "PPN Penyerahan yang mendapat fasilitas PPN atau PPnBM Tidak Dipungut",
    "PPN Penyerahan yang mendapat fasilitas PPN atau PPnBM Dibebaskan",
    "PPN Penyerahan yang mendapat fasilitas PPN atau PPnBM dengan Faktur Pajak yang dilaporkan secara digunggung",
    "Total PPN", "Jumlah Seluruh Penyerahan",
    "PPN Penyerahan yang PPN-nya harus dipungut sendiri",
    "PPN Penyerahan yang PPN-nya dipungut oleh Pemungut PPN",
    "PPN Penyerahan yang PPN-nya tidak dipungut",
    "PPN Penyerahan yang dibebaskan dari pengenaan PPN",
    "Jumlah PPN",
    "PPN Impor BKP, Pemanfaatan BKP Tidak Berwujud dan/atau JKP dari luar Daerah Pabean di dalam Daerah Pabean yang Pajak Masukannya dapat dikreditkan",
    "PPN Perolehan BKP/JKP dari dalam negeri dengan DPP Nilai Lain atau Besaran Tertentu yang Pajak Masukannya dapat dikreditkan",
    "Kompensasi kelebihan Pajak Masukan", "Jumlah Pajak Masukan yang dapat diperhitungkan",
    "PPN kurang atau (lebih) bayar", "Status BPE", "Tanggal Pelaporan",
    "Tanggal Pembayaran", "Jumlah", "NTPN", "Catatan",
]


def _common(text):
    return {
        "status": "Pembetulan" if "pembetulan" in text.lower() else ("Kurang Bayar" if "kurang bayar" in text.lower() else "Normal"),
        "report_date": date_after_label(text, ["Tanggal Pelaporan", "Tanggal Lapor", "Tanggal Terima"]),
        "pay_date": date_after_label(text, ["Tanggal Pembayaran", "Tanggal Bayar", "Tanggal Setor"]),
        "payment": number_after_label(text, ["Jumlah Pembayaran", "Jumlah Bayar", "Nilai Pembayaran"]),
        "ntpn": "\n".join(ntpn_values(text)) or None,
    }


def parse_ppn_old(file_obj):
    rows = []
    for group in group_pages_by_period(extract_pdf_pages(file_obj)):
        text = combined_text(group); month, year = group["key"] or (None, None)
        if not year: continue
        c = _common(text)
        dpp_export = number_after_label(text, ["DPP Ekspor"])
        dpp_self = number_after_label(text, ["DPP Penyerahan yang PPN-nya harus dipungut sendiri", "PPN-nya harus dipungut sendiri"])
        dpp_collector = number_after_label(text, ["DPP Penyerahan yang PPN-nya dipungut oleh Pemungut PPN"])
        dpp_not_collected = number_after_label(text, ["DPP Penyerahan yang PPN-nya tidak dipungut"])
        dpp_exempt = number_after_label(text, ["DPP Penyerahan yang dibebaskan"])
        total_delivery = number_after_label(text, ["Jumlah Seluruh Penyerahan", "Total Penyerahan"])
        ppn_self = number_after_label(text, ["PPN Penyerahan yang PPN-nya harus dipungut sendiri"])
        ppn_collector = number_after_label(text, ["PPN Penyerahan yang PPN-nya dipungut oleh Pemungut PPN"])
        ppn_not_collected = number_after_label(text, ["PPN Penyerahan yang PPN-nya tidak dipungut"])
        ppn_exempt = number_after_label(text, ["PPN Penyerahan yang dibebaskan"])
        total_ppn = number_after_label(text, ["Jumlah PPN", "Total PPN"])
        input_tax = number_after_label(text, ["Pajak Masukan yang dapat diperhitungkan", "Jumlah Pajak Masukan"])
        payable = number_after_label(text, ["PPN kurang atau lebih bayar", "PPN Kurang Bayar", "PPN Lebih Bayar"])
        rows.append([
            MONTHS_ID.get(month, month), year, c["status"], dpp_export, dpp_self, dpp_collector,
            dpp_not_collected, dpp_exempt, total_delivery, ppn_self, ppn_collector,
            ppn_not_collected, ppn_exempt, total_ppn, input_tax, payable,
            c["status"], c["report_date"], c["pay_date"], c["payment"], c["ntpn"],
            None if total_delivery is not None else "Perlu review manual: jumlah seluruh penyerahan tidak terdeteksi otomatis.",
        ])
    return {"headers": OLD_HEADERS, "rows": rows}


def parse_ppn_new(file_obj):
    rows = []
    for group in group_pages_by_period(extract_pdf_pages(file_obj)):
        text = combined_text(group); month, year = group["key"] or (None, None)
        if not year: continue
        c = _common(text)
        row = [None] * len(NEW_HEADERS)
        row[0], row[1], row[2] = MONTHS_ID.get(month, month), year, c["status"]
        # Fields used by the reconciliation are populated explicitly; other detailed
        # categories remain available for future parser refinement without changing schema.
        row[11] = number_after_label(text, ["Total Harga Jual", "Jumlah Harga Jual"])
        row[20] = number_after_label(text, ["Total DPP Nilai Lain"])
        row[29] = number_after_label(text, ["Total PPN"])
        row[30] = number_after_label(text, ["Jumlah Seluruh Penyerahan", "Total Penyerahan"]) or row[11]
        row[35] = number_after_label(text, ["Jumlah PPN", "Total PPN"]) or row[29]
        row[39] = number_after_label(text, ["Jumlah Pajak Masukan yang dapat diperhitungkan", "Pajak Masukan yang dapat diperhitungkan"])
        row[40] = number_after_label(text, ["PPN kurang atau (lebih) bayar", "PPN Kurang Bayar", "PPN Lebih Bayar"])
        row[41], row[42], row[43], row[44], row[45] = c["status"], c["report_date"], c["pay_date"], c["payment"], c["ntpn"]
        row[46] = None if row[11] is not None else "Perlu review manual: Total Harga Jual tidak terdeteksi otomatis."
        rows.append(row)
    return {"headers": NEW_HEADERS, "rows": rows}
