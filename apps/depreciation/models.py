from django.db import models


class DepreciationWorkspace(models.Model):
    """Navigation-only admin model for the stateless depreciation feature.

    No table is created and uploaded files are never persisted. The model exists
    only so Jazzmin can expose this feature as a first-class sidebar module.
    """

    class Meta:
        managed = False
        verbose_name = "Depreciation Schedule"
        verbose_name_plural = "Depreciation Schedule"
        default_permissions = ()

    def __str__(self):
        return "Depreciation Schedule"
