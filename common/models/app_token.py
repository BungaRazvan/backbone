from django.db import models

import secrets


class AppToken(models.Model):
    class Meta:
        db_table = "app_token"
        app_label = "common"

    at_app_name = models.CharField(null=False, blank=False, max_length=255, unique=True)
    at_app_token = models.CharField(null=False, blank=True, max_length=64)
    at_is_active = models.BooleanField(default=True)
    at_created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.at_app_token:
            self.at_app_token = secrets.token_hex(32)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.at_app_name} -> {self.at_app_token}"
