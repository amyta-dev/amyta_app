# ERP Workspace - Django + Jazzmin

Base project berasal dari Depreciation Schedule dan sekarang diubah menjadi **modular ERP shell**. Dua feature utama sudah dipisah:

- **Fixed Asset & Depreciation** — stateless upload -> process -> download.
- **Financial Reporting** — 8 workbook input -> Trial Balance, IS, BS, Cash Flow, AR, AP, dan Advance Payment.
- **Tax Review** — parameter review, upload SPT/LK/mapping, reconciliation, dan output workbook.
- **Administration** — user management khusus superuser + password expiry 90 hari.

## Local setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Buka `http://127.0.0.1:8000/`; root otomatis menuju Jazzmin ERP `/admin/`.

## Sidebar

- Fixed Asset & Depreciation
  - Generate Depreciation Schedule
- Financial Reporting
  - Generate Financial Reports
- Operasional Review Pajak
  - Review Perpajakan
  - Dashboard Tax Review
  - Review Baru
- Accounts (hanya superuser untuk user management)

Detail arsitektur: `docs/PROJECT_STRUCTURE.md`.

## Settings

- Local CLI: `config.settings.dev`
- WSGI/ASGI production: `config.settings.prod`

Environment yang umum:

```text
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_DEBUG=0
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

## Important implementation boundary

UI Jazzmin dan API memanggil service layer yang sama. Jangan copy calculation logic ke admin/view. Untuk feature baru, tambah app baru di `apps/` dan register di `FEATURE_APPS`.

## Financial Reporting API

Endpoint: `POST /api/financial-reporting/generate/` (multipart/form-data, authenticated).

Input wajib: `client_name`, `period_start`, `period_end`, `cash_flow_master`, `coa_master`, `beginning_trial_balance`, `journal_voucher`, `beginning_ar`, `beginning_ap`, `beginning_advance`, dan `beginning_cash_flow`.

Output berupa ZIP yang berisi tujuh laporan utama, validation summary, workbook gabungan, dan processing manifest. Engine ini dipindahkan dari aplikasi Flask lama tanpa membawa layer web Flask.
