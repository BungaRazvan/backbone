from rest_framework.views import APIView
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator

from common.auth.decorators import require_token
from extension.tasks.scan_playlist import scan_youtube_playlist

from celery.result import AsyncResult


class ScanYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @method_decorator(require_token(app_name=("extension")))
    def get(self, request, *args, **kwargs):

        url = kwargs.get("url")
        task_result = scan_youtube_playlist.delay(
            "https://www.youtube.com/playlist?list=" + url
        )

        return JsonResponse({"task_id": task_result.id})


class PollYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @method_decorator(require_token(app_name=("extension")))
    def get(self, request):
        args = request.GET
        task = args.get("task_id")

        if not task:
            return JsonResponse({})

        res = AsyncResult(task)

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
