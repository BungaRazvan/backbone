from dataclasses import dataclass

from rest_framework.views import APIView
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator

from common.auth.decorators import require_token, validate_arguments
from extension.tasks.scan_playlist import scan_youtube_playlist

from celery.result import AsyncResult


@dataclass
class Args:
    task_id: str


class PollYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @method_decorator([require_token(app_name=("extension")), validate_arguments(Args)])
    def get(self, request, args):

        res = AsyncResult(args.task_id)

        if res.state in ("PROGRESS", "STARTED"):
            response = {
                "state": res.state,
                "current": res.info.get("current", 0),
                "total": res.info.get("total", 1),
                "percent": res.info.get("percent", 0),
                "last_title": res.info.get("last_title", "Scanning playlist..."),
            }
        elif res.state == "SUCCESS":
            result = res.result or {}
            response = {
                "state": res.state,
                "percent": 100,
                "result": result,
                "last_title": "Scan complete",
                "total": result.get("videos", []) and len(result.get("videos", [])),
            }
        else:
            response = {
                "state": res.state,
                "percent": 0,
                "last_title": "Scan is starting...",
            }

        return JsonResponse(response)
