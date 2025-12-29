import os
import sys

from django.core.management.base import BaseCommand
from subprocess import Popen


class Command(BaseCommand):
    help = "Run Celery worker with auto-reload on code changes (development only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loglevel",
            type=str,
            default="info",
            help="Celery log level (default: info)",
        )

    def handle(self, *args, **options):
        loglevel = options["loglevel"]

        # Command to run Celery worker
        cmd = ["celery", "-A", "backbone", "worker", "--loglevel", loglevel]

        self.stdout.write(
            self.style.SUCCESS(f"Starting Celery worker with auto-reload...")
        )

        # Use watchmedo to restart on file changes
        watch_cmd = [
            "watchmedo",
            "auto-restart",
            "--directory=.",
            "--pattern=*.py",
            "--recursive",
            "--",
        ] + cmd

        # Run the command
        process = Popen(watch_cmd)
        process.communicate()
