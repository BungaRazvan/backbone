import time
import logging

from django.core.management.base import BaseCommand

from apscheduler.schedulers.background import BackgroundScheduler
from discord_core.models import QueueInterval
from discord_core.tasks import send_image_to_discord

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run APScheduler with dynamic DB syncing"

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("Scheduler started")

        known_jobs = {}

        try:
            while True:
                scheds = list(QueueInterval.objects.filter(active=True))
                current_ids = {sched.qi_id for sched in scheds}

                # ----------------------
                # 1) REMOVE DELETED or INACTIVE JOBS
                # ----------------------
                for job in scheduler.get_jobs():
                    job_id = int(job.id.replace("user_schedule_", ""))

                    if job_id not in current_ids:
                        scheduler.remove_job(job.id)
                        known_jobs.pop(job_id, None)
                        logger.info(f"Removed job: {job.id}")

                # ----------------------
                # 2) ADD / UPDATE JOBS
                # ----------------------
                for sched in scheds:
                    job_id = f"user_schedule_{sched.qi_id}"
                    trigger = sched.get_trigger()

                    # Detect new or changed triggers
                    if sched.qi_id not in known_jobs or known_jobs[sched.qi_id] != str(
                        trigger
                    ):
                        scheduler.add_job(
                            send_image_to_discord.delay,
                            trigger=trigger,
                            id=job_id,
                            replace_existing=True,
                            args=[sched.qi_id],
                        )
                        known_jobs[sched.qi_id] = str(trigger)
                        logger.info(f"Registered/Updated job {job_id}")

                # prevent CPU exhaustion
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped cleanly")
