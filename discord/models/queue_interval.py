# discord/models.py
from django.db import models


class QueueInterval(models.Model):
    SCHEDULE_TYPE_CHOICES = [
        ("interval", "Every X minutes"),
        ("daily", "Daily at specific time"),
        ("weekly", "Weekly on specific day(s)"),
        ("monthly", "Monthly on specific day"),
    ]

    class Meta:
        db_table = "queue_intervals"
        app_label = "discord"

    qi_id = models.AutoField(primary_key=True)
    qi_name = models.CharField(max_length=255)
    qi_description = models.CharField(max_length=255, blank=True, null=True)

    qi_created_at = models.DateTimeField(auto_now_add=True)
    qi_user_id = models.CharField(max_length=255)
    qi_channel_id = models.CharField(max_length=255)
    qi_quild_id = models.CharField(max_length=255)

    qi_time = models.TimeField(null=True, blank=True)
    qi_schedule_type = models.CharField(
        max_length=10, choices=SCHEDULE_TYPE_CHOICES, blank=False, null=False
    )
    qi_weekday = models.PositiveSmallIntegerField(blank=True, null=True)
    qi_day_of_month = models.PositiveSmallIntegerField(blank=True, null=True)
    qi_interval_minutes = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.qi_name} ({self.qi_schedule_type})"
