from django.db import models
from django.db.models import Q
from common.mixins.auto_str import AutoStrMixin
from mytools.services.parse_bill.parameters import UtilityCategory


class BillingCycleQuerySet(models.QuerySet):
    def covering_year(self, year, *, cycle_type, category):
        return self.filter(
            Q(start_date__year__lte=year)
            & (Q(end_date__year__isnull=True) | Q(end_date__year__gte=year)),
            type=cycle_type,
            category=category,
        )


class BillingCycle(AutoStrMixin, models.Model):
    objects = BillingCycleQuerySet.as_manager()

    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=True)
    cycle_day = models.PositiveSmallIntegerField()
    type = models.CharField(
        max_length=255,
        choices=[
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
            ("weekly", "Weekly"),
            ("daily", "Daily"),
            ("quarterly", "Quarterly"),
        ],
    )
    category = models.CharField(
        max_length=255,
        choices=[
            (UtilityCategory.ELECTRICITY.value, "Electricity"),
            (UtilityCategory.GAS.value, "Gas"),
        ],
        null=False,
        blank=False,
    )
