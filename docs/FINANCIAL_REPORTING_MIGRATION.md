# Financial Reporting — Flask Feature Migration to Django

## Tujuan

Fitur Generator Laporan Keuangan dari aplikasi Flask dipindahkan ke ERP Django tanpa membawa framework Flask. Accounting engine dipertahankan sebagai pure Python service agar rumus yang sudah lolos UAT tidak perlu ditulis ulang.

## Boundary

```text
apps/financial_reporting/
├── admin.py                  # Jazzmin UI adapter
├── forms.py                  # Admin upload form
├── models.py                 # Unmanaged navigation model
├── serializers.py           # DRF multipart input contract
├── views.py                  # DRF/download adapter
├── urls.py
├── services/
│   ├── generator.py          # temp-file orchestration shared by UI + API
│   └── engine/               # framework-agnostic accounting domain
│       ├── constants.py
│       ├── excel_reader.py
│       ├── models.py
│       ├── processor.py
│       ├── report_writer.py
│       └── utils.py
└── tests/
    ├── fixtures/             # 8 UAT workbooks
    └── test_service_uat.py
```

`services/engine/` tidak boleh mengimpor Django, DRF, Jazzmin, atau Flask.

## Input

1. Cash Flow Master
2. COA Master
3. Beginning Trial Balance
4. Journal Voucher
5. Beginning AR Report
6. Beginning AP Report
7. Beginning Advance Payment Report
8. Beginning Cash Flow Statement

Metadata proses: Nama Klien, Periode Awal, Periode Akhir. Opsional: override account code AR/AP/Advance dan strict validation.

## Output

- 01_Trial_Balance.xlsx
- 02_Income_Statement.xlsx
- 03_Balance_Sheet.xlsx
- 04_Cash_Flow_Statement.xlsx
- 05_AR_Report.xlsx
- 06_AP_Report.xlsx
- 07_Advance_Payment_Report.xlsx
- 08_Validation_Summary.xlsx
- All_Reports.xlsx
- processing_manifest.json

Semua file dikembalikan sebagai satu ZIP.

## Interface

Jazzmin sidebar:

```text
Financial Reporting
└── Generate Financial Reports
```

Workspace menggunakan Django Admin/Jazzmin dan memanggil service yang sama dengan DRF.

DRF endpoint:

```text
POST /api/financial-reporting/generate/
Content-Type: multipart/form-data
Authentication: JWT atau authenticated Django session
```

## Penyimpanan

Fitur tetap stateless seperti aplikasi asal. Input workbook ditulis hanya ke `TemporaryDirectory`, diproses, output ZIP dibaca ke response, lalu temporary directory dihapus. Tidak ada model database untuk menyimpan isi workbook.

## UAT smoke test

Dengan 8 workbook dari paket UAT:

- Trial Balance: 27 rows
- Income Statement: 29 rows
- Balance Sheet: 24 rows
- Cash Flow: 24 rows
- AR Ledger: 10 rows
- AP Ledger: 10 rows
- Advance Ledger: 7 rows
- Journal rows read/used: 78 / 78
- Validation issues: 0

