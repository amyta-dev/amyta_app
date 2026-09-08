# Fixed Asset & Depreciation

## Purpose

`apps.depreciation` is the standalone Fixed Asset & Depreciation module.

Primary workflow:

``` text
Upload asset register
→ Validate
→ Calculate depreciation
→ Generate schedule
→ Download result
```

Keep calculation and workbook-generation logic in the service layer
rather than Admin/views.

## Relationship with Financial Reporting

Financial Reporting also exposes a Depreciation Schedule workspace using
service integration inside `apps.financial_reporting`.

Avoid circular imports between `apps.depreciation` and
`apps.financial_reporting`. If this standalone app is retired later,
remove it from `FEATURE_APPS` only after confirming nothing imports it.

## Checks

``` bash
python manage.py check
python manage.py migrate
python manage.py runserver
```
