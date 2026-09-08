from rest_framework.permissions import BasePermission


class IsSuperUserOnly(BasePermission):
    """Dipakai untuk endpoint penambahan/penghapusan user (fitur superuser)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class IsOperationalUser(BasePermission):
    """User biasa yang sudah login (akses fungsi operasional)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
