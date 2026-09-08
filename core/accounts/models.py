from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    password_changed_at = models.DateTimeField(default=timezone.now)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()
