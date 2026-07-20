from django.db import models

from common.mixins import AutoStrMixin


class Electricity(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"
        db_table = "electricity"

    e_bill = models.ForeignKey(
        "Bill",
        on_delete=models.CASCADE,
        related_name="electricity",
    )

    e_from_date = models.DateField()
    e_to_date = models.DateField()

    e_kwh_used = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Energy used in kWh"
    )
    e_unit_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
    )
    e_total_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    e_subtotal_before_vat = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )

    e_standing_charge_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        help_text="Daily charge in Pounds",
        blank=True,
        null=True,
    )
    e_standing_charge_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )
