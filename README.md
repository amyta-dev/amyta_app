# ERP Workspace - Django + DRF + Jazzmin

ERP Workspace adalah aplikasi ERP modular berbasis **Django**, **Django REST Framework (DRF)**, dan **Jazzmin**.

Project dikembangkan dengan pendekatan modular sehingga setiap business domain dipisahkan berdasarkan tanggung jawabnya. UI Jazzmin dan API DRF menggunakan service layer yang sama agar business logic tidak terduplikasi.

## Modules

### Fixed Asset & Depreciation

Module untuk pengelolaan dan perhitungan depresiasi fixed asset.

Fitur utama:

- Generate Depreciation Schedule
- Upload dan proses asset register
- Generate output depreciation workbook

### Financial Reporting

Module untuk proses laporan keuangan dan supporting accounting tools.

Fitur utama:

- Generate Financial Reports
- Depreciation Schedule
- Bank Statement PDF Parsing
- Financial report processing
- Accounting validation
- Excel/ZIP report generation

Bank Statement PDF Parsing mendukung format bank yang telah tersedia pada parser, termasuk:

- BCA
- BNI
- Bank of China (BOC)
- CIMB Niaga
- Mandiri

### Tax Review

Module untuk proses review perpajakan.

Fitur utama:

- Review Perpajakan
- Dashboard Tax Review
- Review Baru
- Tax review parameter setup
- Upload dan processing data perpajakan
- Reconciliation
- Generate review output

### Accounts & Administration

Module untuk user dan access management.

Fitur utama:

- User Management
- Group & Permission Management
- Superuser Administration
- Authentication
- Password Expiry
- Session Management

---

## Project Structure

```text
amytang_app/
├── apps/
│   ├── depreciation/
│   ├── financial_reporting/
│   └── tax_review/
│
├── core/
│   ├── accounts/
│   └── middleware/
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── jazzmin_settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
├── static/
├── docs/
├── manage.py
├── requirements.txt
└── README.md
```

Detail implementasi masing-masing module tersedia pada README di dalam app terkait.

---

## Application Architecture

Project menggunakan separation of concerns antara UI, API, dan business logic.

```text
Jazzmin / Django Admin
          │
          │
          ▼
       Forms
          │
          ▼
      Services
          │
          ▼
 Business Processing
          │
          ▼
 Excel / PDF / ZIP Output


DRF API
   │
   ▼
Serializers
   │
   ▼
Services
   │
   ▼
Business Processing
```

Jazzmin dan DRF **tidak boleh memiliki duplicate business logic**.

Business rules, calculation, parsing, reconciliation, dan report generation harus ditempatkan pada service layer masing-masing module.

---

## Installed Applications

Feature applications diregister melalui `config/settings/base.py`.

```python
FEATURE_APPS = [
    "core.accounts.apps.AccountsConfig",
    "apps.depreciation.apps.DepreciationConfig",
    "apps.financial_reporting.apps.FinancialReportingConfig",
    "apps.tax_review.apps.TaxReviewConfig",
]

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + FEATURE_APPS
)
```

---

## Local Setup

Create virtual environment:

```bash
python -m venv venv
```

Activate environment.

Linux / macOS:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply database migrations:

```bash
python manage.py migrate
```

Create superuser:

```bash
python manage.py createsuperuser
```

Run Django system check:

```bash
python manage.py check
```

Start development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Root application diarahkan ke Django Admin / Jazzmin ERP workspace.

---

## ERP Navigation

Sidebar utama terdiri dari business module yang diregister melalui Django Admin dan Jazzmin.

```text
Fixed Asset & Depreciation
└── Generate Depreciation Schedule

Financial Reporting
├── Generate Financial Reports
├── Depreciation Schedule
└── Bank Statement PDF Parsing

Tax Review
├── Review Perpajakan
├── Dashboard Tax Review
└── Review Baru

Accounts
└── User Administration
```

Financial Reporting menggunakan native Django Admin workspace registration sehingga submenu tidak bergantung pada Jazzmin `custom_links`.

---

## Authentication & Authorization

ERP menggunakan authentication bawaan Django untuk Jazzmin/Admin dan Django REST Framework untuk API.

### Web Authentication

Jazzmin menggunakan Django Session Authentication.

User yang belum login akan diarahkan ke:

```text
/admin/login/
```

Setelah login:

```text
/admin/
```

Session dikonfigurasi dengan expiry agar user tidak tetap login terlalu lama ketika tidak aktif.

### API Authentication

DRF mendukung:

- JWT Authentication
- Session Authentication

API secara default menggunakan:

```python
rest_framework.permissions.IsAuthenticated
```

sehingga endpoint tidak bersifat public kecuali secara eksplisit dikonfigurasi berbeda.

---

## API Architecture

API dibangun menggunakan **Django REST Framework**.

Setiap module dapat memiliki:

```text
serializers.py
urls.py
views.py
services/
```

Alur API:

```text
Request
   │
   ▼
DRF View
   │
   ▼
Serializer Validation
   │
   ▼
Service Layer
   │
   ▼
Business Processing
   │
   ▼
Response / Generated File
```

API documentation/schema menggunakan:

```text
drf-spectacular
```

---

## Settings

Project menggunakan settings yang dipisahkan berdasarkan environment.

```text
config/settings/
├── base.py
├── dev.py
└── prod.py
```

### Base Settings

Berisi shared configuration seperti:

- Installed Apps
- Middleware
- Authentication
- DRF
- Session
- Static Files
- Media
- CORS
- Jazzmin

### Development

```text
config.settings.dev
```

Digunakan untuk local development.

### Production

```text
config.settings.prod
```

Digunakan oleh WSGI/ASGI production deployment.

---

## Environment Variables

Contoh environment configuration:

```text
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_DEBUG=0
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Production secret, credential, token, dan `.env` tidak boleh disimpan ke Git repository.

---

## Development Convention

### Business Logic

Business logic harus berada pada:

```text
services/
```

Contoh:

```text
apps/financial_reporting/services/
apps/tax_review/services/
apps/depreciation/services/
```

Jangan menaruh calculation atau processing logic langsung pada:

```text
admin.py
views.py
serializers.py
forms.py
templates/
```

### DRF

Gunakan:

```text
serializers.py
```

untuk request validation.

Gunakan:

```text
views.py
```

untuk HTTP/API handling.

Gunakan:

```text
services/
```

untuk business processing.

### Django Admin / Jazzmin

`admin.py` bertanggung jawab terhadap:

- model registration
- workspace registration
- Admin URL
- Admin UI integration

Business processing tetap dilakukan melalui service layer.

### Database Changes

Setiap perubahan model database harus menggunakan migration.

```bash
python manage.py makemigrations
python manage.py migrate
```

Sebelum migrate, jalankan:

```bash
python manage.py check
```

---

## Dependency Notes

Beberapa fitur membutuhkan library tambahan sesuai business processing yang digunakan.

Contohnya PDF bank statement parsing menggunakan:

```text
PyMuPDF
```

Install seluruh dependency project melalui:

```bash
pip install -r requirements.txt
```

Hindari install dependency secara manual tanpa memperbarui `requirements.txt`.

---

## Documentation

Dokumentasi teknis yang lebih detail dipisahkan per module.

```text
README.md

apps/
├── depreciation/
│   └── README.md
├── financial_reporting/
│   └── README.md
└── tax_review/
    └── README.md

core/
└── accounts/
    └── README.md

docs/
└── PROJECT_STRUCTURE.md
```

Root `README.md` hanya menjelaskan **project-level architecture dan setup**.

Detail seperti:

- input field
- upload format
- API request parameter
- validation rule
- calculation logic
- output workbook
- supported template
- business rule

harus didokumentasikan di README masing-masing module.

---

## Development Workflow

Sebelum menjalankan aplikasi:

```bash
python manage.py check
```

Jika terdapat perubahan model:

```bash
python manage.py makemigrations
python manage.py migrate
```

Run application:

```bash
python manage.py runserver
```

Git workflow:

```bash
git status
git add .
git commit -m "Describe the change"
git push origin main
```

---

## Important Implementation Boundary

Project mengikuti prinsip:

> **Admin/UI dan API adalah interface. Service layer adalah tempat business logic.**

Feature baru tidak selalu membutuhkan Django app baru.

Jika feature masih berada dalam business domain yang sama, feature tersebut sebaiknya ditambahkan ke app yang sudah ada.

Contoh:

```text
Financial Reporting
├── Generate Financial Reports
├── Depreciation Schedule
└── Bank Statement PDF Parsing
```

Ketiga fitur tersebut dapat berada di dalam satu `financial_reporting` module dengan service masing-masing.

Tujuannya agar struktur ERP tetap modular, maintainable, testable, dan mudah dikembangkan.