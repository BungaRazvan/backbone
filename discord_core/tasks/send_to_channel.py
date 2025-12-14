from celery import shared_task
from discord_core.models import QueueInterval
import discord_core as d


@shared_task
def send_to_channel():
    pass
