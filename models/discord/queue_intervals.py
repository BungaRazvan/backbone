from django.db import models


class QueueIntervals(models.Model):
    class Meta:
        managed = False
        db_table = 'queue_intervals'
        app_label = 'discord'

    qi_id = models.AutoField(primary_key=True)
    qi_description = models.CharField(max_length=255, blank=True, null=True)
    qi_user_id = models.CharField(max_length=255)
    qi_name = models.CharField(max_length=255)
    qi_created_at = models.DateTimeField()
    qi_at = models.CharField(max_length=16)
    qi_channel = models.CharField(max_length=255, blank=True, null=True)

