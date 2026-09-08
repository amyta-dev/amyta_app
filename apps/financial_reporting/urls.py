from django.urls import path

from .views import (
    BankStatementConvertView,
    DepreciationGenerateView,
    FinancialReportGenerateView,
)

app_name = "financial_reporting"

urlpatterns = [
    path("generate/", FinancialReportGenerateView.as_view(), name="generate"),
    path("depreciation/generate/", DepreciationGenerateView.as_view(), name="depreciation-generate"),
    path("bank-statement/convert/", BankStatementConvertView.as_view(), name="bank-statement-convert"),
]
