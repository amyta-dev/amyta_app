from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    return JsonResponse({"status": "ok", "application": "erp-workspace"})


def home(request):
    return redirect("admin:index")


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("core.accounts.urls")),
    path("api/depreciation/", include("apps.depreciation.urls")),
    path("api/financial-reporting/", include("apps.financial_reporting.urls")),
    path("api/tax-review/", include("apps.tax_review.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("health/", health_check, name="health_check"),
]
