from datetime import timedelta
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse

PASSWORD_MAX_AGE_DAYS = 90


class PasswordExpiryMiddleware:
    """Paksa ganti password setelah 90 hari, termasuk untuk UI Jazzmin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            changed_at = getattr(user, "password_changed_at", None)
            expired = changed_at and timezone.now() - changed_at > timedelta(days=PASSWORD_MAX_AGE_DAYS)
            if expired:
                allowed = (
                    request.path.startswith("/admin/password_change"),
                    request.path.startswith("/admin/logout"),
                    request.path.startswith("/api/auth/change-password"),
                    request.path.startswith("/static/"),
                )
                if not any(allowed):
                    if request.path.startswith("/admin/"):
                        return redirect(reverse("admin:password_change"))
                    return JsonResponse(
                        {"detail": "Password sudah berusia 90 hari. Harap ganti password terlebih dahulu."},
                        status=403,
                    )
        return self.get_response(request)
