# Tax Review Django App

Self-contained Django + DRF + Jazzmin feature app for the Program Review Perpajakan workflow.

## Main flow

1. Jazzmin workspace / DRF receives company, period, tax parameters and uploaded files.
2. `services/processor.py` orchestrates the process.
3. `services/excel_input.py` reads Financial Statement and Keyword Mapping workbooks.
4. `services/mapping.py` maps financial rows into tax objects.
5. `services/spt/` parses the five SPT PDFs.
6. `services/reconciliation.py` calculates WHT/PPN reconciliation.
7. `services/workbook.py` generates the downloadable XLSX working paper.

## Integration

Add to `INSTALLED_APPS`:

```python
"apps.tax_review.apps.TaxReviewConfig",
```

Add to project `urls.py`:

```python
path("api/tax-review/", include("apps.tax_review.urls")),
```

Do not add a Jazzmin `custom_links` entry for this app. `TaxReviewWorkspace` is already the single sidebar launcher.

Dependencies used by this app include Django, Django REST Framework, openpyxl, and pdfplumber.
