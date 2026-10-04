from django.db import models

from common.mixins.auto_str import AutoStrMixin


class AnnualEnergySummary(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"
        db_table = "annual_energy_summarys"

    year = models.PositiveIntegerField(null=False, blank=False)
    last_proccessed_month = models.PositiveSmallIntegerField(null=False, blank=False)
