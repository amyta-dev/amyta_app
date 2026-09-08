# Financial Reporting

## Purpose

`apps.financial_reporting` owns three accounting workspaces:

1.  Generate Financial Reports
2.  Depreciation Schedule
3.  Bank Statement PDF Parsing

They are three features inside one Django app.

## Structure

``` text
financial_reporting/
├── admin.py
├── apps.py
├── forms.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── migrations/
├── templates/financial_reporting/
└── services/
    ├── generator.py
    ├── depreciation.py
    ├── engine/
    ├── bank_statement_service.py
    └── bank_statement/
        └── parsers/
```

## DRF endpoints

``` text
POST /api/financial-reporting/generate/
POST /api/financial-reporting/depreciation/generate/
POST /api/financial-reporting/bank-statement/convert/
```

Endpoints use authenticated DRF multipart requests.

## Generate Financial Reports

Receives client/period data and eight Excel inputs: Cash Flow Master,
COA Master, Beginning Trial Balance, Journal Voucher, Beginning AR,
Beginning AP, Beginning Advance, and Beginning Cash Flow.

`FinancialReportService` owns processing. Do not copy accounting
calculations into Admin or DRF views.

## Depreciation Schedule

Input:

-   `excel_file` --- required `.xlsx`
-   `client_name` --- optional
-   `year` --- optional

Output is an Excel depreciation schedule.

## Bank Statement PDF Parsing

Supported parser families:

-   BCA
-   BNI
-   BOC
-   CIMB Niaga
-   Mandiri

Requires `PyMuPDF`.

## Maintenance boundary

-   `views.py`: HTTP/DRF responses.
-   `serializers.py`: API validation.
-   `forms.py`: Admin form validation.
-   `services/generator.py`: financial-report orchestration.
-   `services/depreciation.py`: depreciation processing.
-   `services/bank_statement_service.py`: conversion service.
-   `services/bank_statement/`: parsing engine.
-   `admin.py`: Admin/Jazzmin workspaces.

MIME/content types belong in the response/view layer, not business
services.

## Validation

``` bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

Run `check` before migrations to catch import/configuration errors.
