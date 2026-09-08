from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class RestrictedUserAdmin(UserAdmin):
    """User management hanya muncul dan bisa digunakan oleh superuser."""

    fieldsets = UserAdmin.fieldsets + (
        ("Keamanan", {"fields": ("password_changed_at",)}),
    )
    readonly_fields = ("password_changed_at",)

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)
