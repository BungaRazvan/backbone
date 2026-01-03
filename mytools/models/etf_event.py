from django.db import models
from decimal import Decimal


class EtfEvent(models.Model):
    class Meta:
        db_table = "etf_events"
        app_label = "mytools"
        unique_together = ("ee_etf", "ee_ex_date")

    ee_id = models.AutoField(primary_key=True)
    ee_etf = models.ForeignKey(
        "mytools.Etf",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="events",
    )

    ee_ex_date = models.DateField()
    ee_payment_date = models.DateField(blank=True, null=True)

    ee_ex_estimated = models.BooleanField(default=False)
    ee_payment_estimated = models.BooleanField(default=False)

    ee_pay_per_share = models.DecimalField(
        max_digits=20, decimal_places=8, default=None, blank=True, null=True
    )

    ee_created_on = models.DateField(auto_now_add=True)

    @property
    def ee_eligible_shares_list(self):
        return self.ee_etf.shares.filter(efs_purchase_date__lte=self.ee_ex_date)

    @property
    def ee_eligible_shares_amount(self):
        result = self.ee_eligible_shares_list.aggregate(total=models.Sum("efs_amount"))
        return result["total"] or Decimal("0")
