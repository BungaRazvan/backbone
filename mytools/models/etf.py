from django.db import models
from decimal import Decimal


class Etf(models.Model):
    class Meta:
        db_table = "etfs"
        app_label = "mytools"

    ef_id = models.AutoField(primary_key=True)
    ef_name = models.CharField(blank=False, null=False, max_length=255)

    ef_isin = models.CharField(max_length=255)
    ef_symbol = models.CharField(max_length=255, blank=True, null=True)
    ef_distribution = models.CharField(
        max_length=255,
        choices=[("monthly", "Monthly"), ("quarterly", "Quarterly")],
        blank=False,
        null=False,
    )
    ef_pay_lag_days = models.IntegerField(default=0, blank=False, null=False)

    def to_upper_unit(self, amount: int):
        if self.ef_symbol.endswith(".L") and amount > 1:
            return Decimal(amount) / Decimal(100)

        return Decimal(amount)

    def __str__(self):
        return f"Etf(ef_id={self.ef_id} ef_name={self.ef_name})"
