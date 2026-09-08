# ERP Project Structure

The project is intentionally split into **three business applications only**.
Authentication and shared technical utilities live under `core/` because they
are infrastructure, not ERP business modules.

```text
erp_modular_jazzmin/
├── manage.py
├── config/                         # Django project configuration only
│   ├── settings/
│   ├── urls.py
│   └── jazzmin_settings.py
│
├── core/                           # Shared infrastructure
│   ├── accounts/                   # User, login, API auth, user admin
│   ├── middleware/                 # Password expiry, etc.
│   └── utils/                      # Shared Excel/PDF helpers
│
└── apps/                           # BUSINESS MODULES ONLY
    ├── depreciation/
    │   ├── admin.py
    │   ├── forms.py
    │   ├── models.py
    │   ├── serializers.py
    │   ├── services.py
    │   ├── urls.py
    │   └── views.py
    │
    ├── financial_reporting/
    │   ├── admin.py
    │   ├── forms.py
    │   ├── models.py
    │   ├── serializers.py
    │   ├── urls.py
    │   ├── views.py
    │   └── services/
    │       ├── generator.py
    │       └── engine/
    │
    └── tax_review/
        ├── admin.py
        ├── forms.py
        ├── models.py
        ├── serializers.py
        ├── urls.py
        ├── views.py
        ├── templates/
        └── services/
            ├── processor.py
            ├── financial_mapping.py
            ├── spt.py
            └── reconciliation.py
```

## Rule for future features

A folder under `apps/` must represent a real business module visible to the
user. Helper logic that belongs only to a feature stays inside that feature's
`services/` folder. Do not create separate Django apps for parsers, mappings,
exports, or calculations unless they become independent business modules.

Examples:

- `tax_review/services/financial_mapping.py` belongs to Tax Review.
- `tax_review/services/spt.py` belongs to Tax Review.
- `tax_review/services/reconciliation.py` belongs to Tax Review.
- `financial_reporting/services/engine/` belongs to Financial Reporting.
- User/account handling belongs to `core/accounts/`.
