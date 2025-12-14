import json

from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse


from common.utils import require_token
from discord_core.models import YoutubeSong
from discord_core.views.get_youtube_tracks import get_videos, get_youtube_info


class YoutubePlaylistSongsView(APIView):
    http_method_names = ["post"]

    @require_token("discord")
    def get(self, request):
        args = request.GET

        playlist_id = args.get("playlist_id")
        user_id = args.get("user_id")
        guild_id = args.get("guild_id")

        if not playlist_id or not user_id or not guild_id:
            return HttpResponseBadRequest("Missing arguments")

        songs = YoutubeSong.objects.filter(
            ys_playlist_id=playlist_id,
            ys_playlist__yp_user_id=user_id,
            ys_playlist__yp_guild_id=guild_id,
        )

        data = []

        for song in songs:
            yt_info = get_youtube_info(song.ys_url)
            vidoes = get_videos(yt_info)
            data.extend(vidoes)

        return JsonResponse({"songs": data})
