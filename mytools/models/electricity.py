from django.db import models

from common.mixins import AutoStrMixin


class Electricity(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"

    e_bill = models.OneToOneField("Bill", on_delete=models.CASCADE, related_name="+")
    e_kwh_used = models.DecimalField(max_digits=8, decimal_places=4)
    e_unit_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
    )
    e_standing_charge_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )
    e_total_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
