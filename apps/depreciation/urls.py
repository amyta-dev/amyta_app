from django.urls import path

from .views import DepreciationGenerateView

urlpatterns = [
    path("generate/", DepreciationGenerateView.as_view(), name="depreciation_generate"),
]
