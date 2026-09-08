from django.db import models


class TaxReviewWorkspace(models.Model):
    """Navigation-only model. No tax-review transaction is stored in the DB."""

    class Meta:
        managed = False
        verbose_name = "Review Pajak"
        verbose_name_plural = "Review Pajak"
        default_permissions = ()

    def __str__(self):
        return "Review Pajak"
