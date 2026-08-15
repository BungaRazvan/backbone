from django.db import models
from decimal import Decimal


class Etf(models.Model):
    class Meta:
        db_table = "etfs"
        app_label = "mytools"

    ef_id = models.AutoField(primary_key=True)
    ef_name = models.CharField(blank=False, null=False, max_length=255)

    ef_isin = models.CharField(max_length=255, blank=True, null=True)
    ef_symbol = models.CharField(max_length=255, blank=True, null=True)
    ef_distribution = models.CharField(
        max_length=255,
        choices=[
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi-annually", "Semi-Annually"),
            ("annually", "Annually"),
        ],
        blank=True,
        null=True,
    )
    ef_pay_lag_days = models.IntegerField(default=0, blank=False, null=False)

    def to_upper_unit(self, amount: int, currency="GBP"):
        """Converts raw dividend data into major currency units (Pounds).

        Uses the explicit currency metadata provided by the data source.
        'GBp' (lowercase p) represents British Pence -> Needs division by 100.
        'GBP' (uppercase) represents British Pounds -> Does NOT need division.
        """

        if currency == "GBp":
            return Decimal(amount) / Decimal(100)

        return Decimal(amount)

    def __str__(self):
        return f"Etf(ef_id={self.ef_id} ef_name={self.ef_name})"
