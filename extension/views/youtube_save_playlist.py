from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse

import json
from discord.views.get_youtube_tracks import get_videos, get_youtube_info
from extension.models import YoutubePlaylists


class YoutubeSavePlaylist(View):
    http_method_names = ["post"]

    def post(self, request):

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid request")

        if not data.get("url"):
            return HttpResponseBadRequest("Invalid request")

        # fixme
        data = get_youtube_info(
            "https://www.youtube.com/playlist?list=" + data.get("url")
        )
        videos = get_videos(data)

        if not data.get("title"):
            return HttpResponseBadRequest("Youtube title not present")

        if not videos:
            return HttpResponseBadRequest("No videos found")

        obj, created = YoutubePlaylists.object.get_or_create(
            yp_name=data.get("title"),
            defults={"yp_name": data.get("title"), "yp_vidoes": videos},
        )

        if not created:
            obj.yp_videos = videos
            obj.save()

        return HttpResponse("Playlist saved")
