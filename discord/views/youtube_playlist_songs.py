from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponseBadRequest


from common.auth.backends import app_auth
from discord.models import YoutubeSong
from discord.views.get_youtube_tracks import get_videos, get_youtube_info
from dataclasses import dataclass
from django.utils.decorators import method_decorator
from common.auth.decorators import require_token, validate_arguments


@dataclass
class Args:
    playlist_id: str
    user_id: str
    guild_id: str


class YoutubePlaylistSongsView(APIView):
    @method_decorator([require_token(app_name="discord"), validate_arguments(Args)])
    def get(self, request, args: Args):
        playlist_id = args.playlist_id
        user_id = args.user_id
        guild_id = args.guild_id

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
