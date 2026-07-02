import os

from django.db import models

from common.mixins import AutoStrMixin


class EnergyProvider(models.TextChoices):
    OCTOPUS = "OCTOPUS", "Octopus Energy"
    EDF = "EDF", "EDF Energy"
    EON = "EON", "E.ON Next"
    OVO = "OVO", "OVO Energy"
    BRITISH_GAS = "BG", "British Gas"


def edf_upload_path(instance, filename):
    return os.path.join("edf_bills", filename)


class Bill(AutoStrMixin, models.Model):
    class Meta:
        db_table = "bills"
        app_label = "mytools"

    b_file = models.FileField(upload_to=edf_upload_path)
    b_from_period = models.DateField(blank=False, null=False)
    b_to_period = models.DateField(blank=False, null=False)
    b_provider = models.CharField(
        blank=False, null=False, max_length=255, choices=EnergyProvider.choices
    )
    b_total_amount_due = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Grand total in Pounds (£)"
    )
