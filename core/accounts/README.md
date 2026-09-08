# Accounts

## Purpose

`core.accounts` owns ERP user/authentication administration.

``` python
AUTH_USER_MODEL = "accounts.User"
```

It integrates with Django Admin/Jazzmin and the password-expiry
middleware:

``` text
core.middleware.password_expiry.PasswordExpiryMiddleware
```

## Responsibilities

-   user accounts;
-   authentication integration;
-   permissions/groups where applicable;
-   superuser administration;
-   password-expiry support.

## Authentication

Jazzmin/Django Admin uses Django sessions. DRF uses JWT and Session
Authentication with `IsAuthenticated` by default.

Recommended web-session behavior is a 30-minute idle timeout and expiry
when the browser closes. Protected custom Django pages must use
`login_required` or `LoginRequiredMixin`.

## Security

Never commit passwords, access tokens, production secret keys, `.env`
files, or private SSH keys.

## Checks

``` bash
python manage.py check
python manage.py createsuperuser
python manage.py runserver
```
