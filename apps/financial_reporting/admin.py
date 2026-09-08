from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .forms import BankStatementParseForm, DepreciationGenerateForm, FinancialReportGenerateForm
from .models import BankStatementWorkspace, DepreciationScheduleWorkspace, GenerateFinancialReportWorkspace
from .services.bank_statement.exceptions import StatementParserError
from .services.generator import ProcessingValidationError
from .views import (
    generate_bank_statement_response,
    generate_depreciation_response,
    generate_financial_report_response,
)


class WorkspaceAdminMixin:
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


@admin.register(GenerateFinancialReportWorkspace)
class GenerateFinancialReportWorkspaceAdmin(WorkspaceAdminMixin, admin.ModelAdmin):
    def get_urls(self):
        return [
            path("workspace/", self.admin_site.admin_view(self.workspace_view), name="financial_reporting_generate_workspace")
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:financial_reporting_generate_workspace"))

    def workspace_view(self, request):
        form = FinancialReportGenerateForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                return generate_financial_report_response(form.cleaned_data)
            except ProcessingValidationError as exc:
                messages.error(request, f"Strict validation menemukan {len(exc.issues)} issue.")
                for issue in exc.issues[:10]:
                    messages.warning(request, f"{issue.category} - {issue.reference}: {issue.message}")
            except Exception as exc:
                messages.error(request, f"Generate laporan gagal: {exc}")
        context = {
            **self.admin_site.each_context(request),
            "title": "Generate Financial Reports",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "financial_reporting/admin_workspace.html", context)


@admin.register(DepreciationScheduleWorkspace)
class DepreciationScheduleWorkspaceAdmin(WorkspaceAdminMixin, admin.ModelAdmin):
    def get_urls(self):
        return [
            path("workspace/", self.admin_site.admin_view(self.workspace_view), name="financial_reporting_depreciation_workspace")
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:financial_reporting_depreciation_workspace"))

    def workspace_view(self, request):
        form = DepreciationGenerateForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                return generate_depreciation_response(form.cleaned_data)
            except Exception as exc:
                messages.error(request, f"Generate depreciation schedule gagal: {exc}")
        context = {
            **self.admin_site.each_context(request),
            "title": "Depreciation Schedule",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "financial_reporting/depreciation_workspace.html", context)


@admin.register(BankStatementWorkspace)
class BankStatementWorkspaceAdmin(WorkspaceAdminMixin, admin.ModelAdmin):
    def get_urls(self):
        return [
            path("workspace/", self.admin_site.admin_view(self.workspace_view), name="financial_reporting_bank_statement_workspace")
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:financial_reporting_bank_statement_workspace"))

    def workspace_view(self, request):
        form = BankStatementParseForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                return generate_bank_statement_response(form.cleaned_data)
            except StatementParserError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f"Konversi bank statement gagal: {exc}")
        context = {
            **self.admin_site.each_context(request),
            "title": "Bank Statement PDF Parsing",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "financial_reporting/bank_statement_workspace.html", context)
