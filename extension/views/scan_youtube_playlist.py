from rest_framework.views import APIView
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator

from common.auth.decorators import require_token
from extension.tasks.scan_playlist import scan_youtube_playlist


class ScanYoutubePlaylist(APIView):
    http_method_names = ["get"]

    @method_decorator(require_token(app_name=("extension")))
    def get(self, request, *args, **kwargs):

        url = kwargs.get("url")
        task_result = scan_youtube_playlist.delay(
            "https://www.youtube.com/playlist?list=" + url
        )

        return JsonResponse({"task_id": task_result.id})
