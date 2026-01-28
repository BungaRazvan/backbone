from rest_framework.views import APIView
from django.http.response import JsonResponse

from common.utils import require_token
from extension.tasks.scan_playlist import scan_youtube_playlist

from celery.result import AsyncResult


class ScanYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @require_token("extension")
    def get(self, request):
        args = request.GET

        url = args.get("url")
        task_result = scan_youtube_playlist.delay(
            "https://www.youtube.com/playlist?list=" + url
        )

        print(task_result.id, "///////////////////")

        return JsonResponse({"task_id": task_result.id})


class PollYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @require_token("extension")
    def get(self, request):
        args = request.GET
        task = args.get("task_id")

        if not task:
            return JsonResponse({})

        res = AsyncResult(task)

        if res.state == "PROGRESS":
            response = {
                "state": res.state,
                "current": res.info.get("current", 0),
                "total": res.info.get("total", 1),
                "percent": res.info.get("percent", 0),
            }
        elif res.state == "SUCCESS":
            response = {
                "state": res.state,
                "percent": 100,
                "result": res.result,
            }
        else:
            response = {"state": res.state, "percent": 0}

        return JsonResponse(response)
