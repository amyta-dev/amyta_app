from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .forms import DepreciationGenerateForm
from .models import DepreciationWorkspace
from .views import generate_report_response


@admin.register(DepreciationWorkspace)
class DepreciationWorkspaceAdmin(admin.ModelAdmin):
    """Expose the stateless depreciation generator inside Jazzmin."""

    def get_urls(self):
        return [
            path(
                "workspace/",
                self.admin_site.admin_view(self.workspace_view),
                name="depreciation_workspace",
            )
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:depreciation_workspace"))

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def get_model_perms(self, request):
        allowed = self.has_module_permission(request)
        return {"add": False, "change": allowed, "delete": False, "view": allowed}

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def workspace_view(self, request):
        if request.method == "POST":
            form = DepreciationGenerateForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    return generate_report_response(
                        uploaded=form.cleaned_data["excel_file"],
                        client_name=form.cleaned_data.get("client_name", ""),
                        year=form.cleaned_data.get("year"),
                    )
                except Exception as exc:
                    messages.error(request, f"Generate report gagal: {exc}")
        else:
            form = DepreciationGenerateForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Depreciation Schedule Generator",
            "subtitle": "Upload asset register dan download schedule tanpa menyimpan file ke server.",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "depreciation/admin_workspace.html", context)
