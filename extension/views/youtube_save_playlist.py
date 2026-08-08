import json

from rest_framework.views import APIView
from django.http import HttpResponseBadRequest, HttpResponse

from discord.views.get_youtube_tracks import get_videos, get_youtube_info
from extension.models import YoutubePlaylist
from django.views.decorators.csrf import csrf_exempt

from django.utils.decorators import method_decorator

from common.auth.decorators import require_token, validate_arguments
from dataclasses import dataclass


@dataclass
class Args:
    url: str


@method_decorator(csrf_exempt, name="dispatch")
class YoutubeSavePlaylist(APIView):

    @method_decorator([require_token(app_name=("extension")), validate_arguments(Args)])
    def post(self, request, args: Args):

        data = get_youtube_info("https://www.youtube.com/playlist?list=" + args.url)
        videos = get_videos(data)

        if not data.get("title"):
            return HttpResponseBadRequest("Youtube title not present")

        if not videos:
            return HttpResponseBadRequest("No videos found")

        obj, created = YoutubePlaylist.objects.get_or_create(
            yp_name=data.get("title"),
            defaults={"yp_name": data.get("title"), "yp_videos": videos},
        )

        if not created:
            obj.yp_videos = videos
            obj.save()

        return HttpResponse("Save & Reload")
