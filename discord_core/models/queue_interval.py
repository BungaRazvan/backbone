from django.db import models

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


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

    qi_created_at = models.DateTimeField()

    qi_user_id = models.CharField(max_length=255, blank=False, null=False)
    qi_channel_id = models.CharField(max_length=255, blank=False, null=False)
    qi_quild_id = models.CharField(max_length=255, blank=False, null=False)

    qi_time = models.TimeField(null=False, blank=False)
    qi_schedule_type = models.CharField(
        max_length=10, choices=SCHEDULE_TYPE_CHOICES, blank=False, null=False
    )
    qi_weekday = models.PositiveSmallIntegerField(blank=True, null=True)
    qi_day_of_month = models.PositiveSmallIntegerField(blank=True, null=True)

    def get_trigger(self):
        hour = self.qi_time.hour
        minutes = self.qi_time.minute

        if self.qi_schedule_type == "interval":

            return IntervalTrigger(minutes=minutes)

        if self.qi_schedule_type == "daily":
            return CronTrigger(hour=hour, minute=minutes)

        if self.qi_schedule_type == "weekly" and self.qi_weekday is not None:
            return CronTrigger(day_of_week=self.qi_weekday, hour=hour, minute=minutes)

        if self.qi_schedule_type == "monthly" and self.qi_day_of_month:
            return CronTrigger(day=self.qi_weekday, hour=hour, minute=minutes)
