import os
import json

from celery import shared_task
from cs2.lib.performance_processor import MatchTelemetryProcessor
from cs2.lib.aim_processor import LiveEngagementProcessor
from backbone.settings import BASE_DIR


@shared_task
def process_cs2_demo_file():
    """
    Process the CS2 demo file.
    """

    processor = LiveEngagementProcessor(
        os.path.join(
            BASE_DIR,
            "cs2",
            "tasks",
            "match730_003827123743319130174_0525370194_271.dem",
        )
    )
    data = processor.evaluate_performance()

    with open("cs2/tasks/performance_output.json", "w") as f:
        f.write(json.dumps(data, indent=4))
