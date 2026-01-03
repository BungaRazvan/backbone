from django.db import models


class EtfShare(models.Model):
    class Meta:
        db_table = "etf_shares"
        app_label = "mytools"

    efs_id = models.AutoField(primary_key=True)
    efs_ef = models.ForeignKey(
        "mytools.Etf",
        on_delete=models.CASCADE,
        db_column="efs_ef_id",
        related_name="shares",
    )
    efs_amount = models.DecimalField(
        max_digits=20, decimal_places=8, blank=False, null=False
    )
    efs_total_price = models.DecimalField(
        max_digits=20, decimal_places=8, blank=False, null=False
    )
    efs_purchase_date = models.DateField(blank=False, null=False)
    efs_created_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"EtfShare(efs_id={self.efs_id})"
