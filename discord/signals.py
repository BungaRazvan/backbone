from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import QueueInterval
from .tasks import sync_queueinterval_to_beat


@receiver([post_save, post_delete], sender=QueueInterval)
def update_beat(sender, **kwargs):
    sync_queueinterval_to_beat.delay()
