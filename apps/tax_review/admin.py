from django.contrib import admin, messages
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .forms import TaxReviewForm
from .models import TaxReviewWorkspace
from .services.constants import MIME_XLSX
from .services.exceptions import TaxReviewError
from .services.processor import process_tax_review


@admin.register(TaxReviewWorkspace)
class TaxReviewWorkspaceAdmin(admin.ModelAdmin):
    """Single Jazzmin launcher. Do not add a duplicate custom_link for this app."""

    def get_urls(self):
        custom = [
            path("workspace/", self.admin_site.admin_view(self.workspace_view), name="tax_review_workspace"),
        ]
        return custom + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:tax_review_workspace"))

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        # Launcher only: it is not CRUD data. View permission is enough for navigation.
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def workspace_view(self, request):
        form = TaxReviewForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                buffer, filename = process_tax_review(form.cleaned_data)
                return FileResponse(buffer, as_attachment=True, filename=filename, content_type=MIME_XLSX)
            except TaxReviewError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f"Proses Review Pajak gagal: {exc}")
        context = {
            **self.admin_site.each_context(request),
            "title": "Program Review Perpajakan",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "tax_review/admin_workspace.html", context)
