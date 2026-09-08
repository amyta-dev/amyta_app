from django.db import models


class GenerateFinancialReportWorkspace(models.Model):
    """Navigation-only workspace for generating the seven financial reports."""

    class Meta:
        managed = False
        verbose_name = "Generate Financial Reports"
        verbose_name_plural = "Generate Financial Reports"
        default_permissions = ()

    def __str__(self):
        return "Generate Financial Reports"


class DepreciationScheduleWorkspace(models.Model):
    """Navigation-only workspace for depreciation schedule generation."""

    class Meta:
        managed = False
        verbose_name = "Depreciation Schedule"
        verbose_name_plural = "Depreciation Schedule"
        default_permissions = ()

    def __str__(self):
        return "Depreciation Schedule"


class BankStatementWorkspace(models.Model):
    """Navigation-only workspace for bank statement PDF parsing."""

    class Meta:
        managed = False
        verbose_name = "Bank Statement PDF Parsing"
        verbose_name_plural = "Bank Statement PDF Parsing"
        default_permissions = ()

    def __str__(self):
        return "Bank Statement PDF Parsing"
