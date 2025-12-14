# discord/tasks.py
import json
from celery import shared_task
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from discord.models import QueueInterval


@shared_task
def sync_queueinterval_to_beat():
    scheds = QueueInterval.objects.all()
    active_ids = set()

    for sched in scheds:
        task_name = f"discord_queue_{sched.qi_id}"
        active_ids.add(task_name)

        # ---------------------------
        # Interval schedule
        # ---------------------------
        if sched.qi_schedule_type == "interval":
            interval, _ = IntervalSchedule.objects.get_or_create(
                every=sched.qi_interval_minutes or 5, period=IntervalSchedule.MINUTES
            )
            schedule_kwargs = {"interval": interval}

        # ---------------------------
        # Daily / Weekly / Monthly
        # ---------------------------
        else:
            if not sched.qi_time:
                continue  # skip invalid entries

            hour = sched.qi_time.hour
            minute = sched.qi_time.minute

            day_of_week = (
                sched.qi_weekday if sched.qi_schedule_type == "weekly" else "*"
            )
            day_of_month = (
                sched.qi_day_of_month if sched.qi_schedule_type == "monthly" else "*"
            )

            crontab, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year="*",
            )
            schedule_kwargs = {"crontab": crontab}

        # Create or update PeriodicTask
        PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults={
                "task": "discord.tasks.send_image_to_discord",
                "args": json.dumps([sched.qi_id]),
                "enabled": True,
                **schedule_kwargs,
            },
        )

    # Disable tasks no longer active
    PeriodicTask.objects.exclude(name__in=active_ids).update(enabled=False)
