from django.urls import path

from .views import ProcessTaxReviewView

app_name = "tax_review"

urlpatterns = [
    path("process/", ProcessTaxReviewView.as_view(), name="process"),
]
