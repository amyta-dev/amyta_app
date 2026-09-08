MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

OBJECT_KEYS = {
    "pph23": "Objek PPh 23",
    "pph4_2": "Objek PPh 4(2)",
    "pph21": "Objek PPh 21",
    "ppn": "Objek PPN",
    "koreksi_pph_badan": "Koreksi PPh Badan",
}

FINANCIAL_REQUIRED_HEADERS = ("Nama Akun", "Keterangan", "Jumlah")
MAPPING_REQUIRED_HEADERS = (
    "Keyword",
    "Objek PPh 23",
    "Objek PPh 4(2)",
    "Objek PPh 21",
    "Objek PPN",
    "Koreksi PPh Badan",
    "Tanda",
)

MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}
MONTH_NAME_TO_NO = {v.lower(): k for k, v in MONTHS_ID.items()}
MONTH_NAME_TO_NO.update({
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
})
