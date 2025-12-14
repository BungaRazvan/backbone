import json
import re

from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from common.utils import require_token
from discord_core.models import YoutubePlaylist, YoutubeSong

from discord_core.views.get_youtube_tracks import get_videos, get_youtube_info

from distutils.util import strtobool


class YoutubePlaylistView(APIView):
    @require_token("discord")
    def get(self, request):

        args = request.GET
        user_id = args.get("user_id")
        guild_id = args.get("guild_id")
        playlist_id = args.get("playlist_id")
        play_mode = strtobool(args.get("play_mode", "false"))

        if not user_id or not guild_id:
            return HttpResponseBadRequest("Missing arguments")

        if playlist_id is not None:
            try:
                playlists = []
                playlist = YoutubePlaylist.objects.get(
                    yp_user_id=user_id, yp_guild_id=guild_id, yp_id=playlist_id
                )
                playlists.append(playlist)
            except YoutubePlaylist.DoesNotExist:
                return HttpResponseBadRequest("Cannot find playlist")
        else:
            playlists = YoutubePlaylist.objects.filter(
                yp_user_id=user_id,
                yp_guild_id=guild_id,
            )

        data = []

        for playlist in playlists:
            if not play_mode:
                songs = [song.ys_url for song in playlist.songs.all()]
            else:
                songs = []

                for song in playlist.songs.all():
                    yt_info = get_youtube_info(song.ys_url)
                    vidoes = get_videos(yt_info)
                    songs.extend(vidoes)

            data.append(
                {
                    "id": playlist.yp_id,
                    "name": playlist.yp_name,
                    "songs": songs,
                }
            )

        return JsonResponse({"playlists": data})

    @require_token("discord")
    def post(self, request):

        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("Invalid request")

        user_id = data.get("user_id")
        guild_id = data.get("guild_id")
        name = data.get("playlist_name")
        songs_list = data.get("playlist_songs")

        if not user_id or not guild_id or not name or not songs_list:
            return HttpResponseBadRequest("Missing arguments")

        songs = [s.strip() for s in re.split(r"[,\s]+", songs_list) if s.strip()]

        if not songs:
            return HttpResponseBadRequest("Missing songs")

        playlist = YoutubePlaylist.objects.create(
            yp_name=name, yp_user_id=user_id, yp_guild_id=guild_id
        )

        to_create = []
        for song in songs:
            to_create.append(YoutubeSong(ys_url=song, ys_playlist=playlist))

        if not to_create:
            return HttpResponseBadRequest("No valid youtube urls")

        YoutubeSong.objects.bulk_create(to_create)
        return HttpResponse("Playlist created")

    @require_token("discord")
    def put(self, request):
        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("Invalid request")

        user_id = data.get("user_id")
        guild_id = data.get("guild_id")
        playlist_id = data.get("playlist_id")
        songs_list = data.get("playlist_songs")
        name = data.get("playlist_name")

        if not user_id or not guild_id or not playlist_id or not name or not songs_list:
            return HttpResponseBadRequest("Missing arguments")

        songs = [s.strip() for s in re.split(r"[,\s]+", songs_list) if s.strip()]

        if not songs:
            return HttpResponseBadRequest("Missing songs")

        try:
            playlist = YoutubePlaylist.objects.get(
                yp_id=playlist_id, yp_user_id=user_id, yp_guild_id=guild_id
            )
            playlist.yp_name = name

            to_create = []
            for song in songs:
                to_create.append(YoutubeSong(ys_url=song, ys_playlist=playlist))

            if not to_create:
                return HttpResponseBadRequest("No valid youtube urls")

            playlist.songs.all().delete()
            YoutubeSong.objects.bulk_create(to_create)
            playlist.save()

        except YoutubePlaylist.DoesNotExist:
            return HttpResponseBadRequest("Invalid request")

        return HttpResponse("Playlist Modified")

    @require_token("discord")
    def delete(self, request):
        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("Invalid request")

        user_id = data.get("user_id")
        guild_id = data.get("guild_id")
        playlist_id = data.get("playlist_id")

        if not user_id or not guild_id or not playlist_id:
            return HttpResponseBadRequest("Missing arguments")

        try:
            playlist = YoutubePlaylist.objects.get(
                yp_id=playlist_id, yp_user_id=user_id, yp_guild_id=guild_id
            )
            playlist.delete()

        except YoutubePlaylist.DoesNotExist:
            return HttpResponseBadRequest("Invalid request")

        return HttpResponse("Playlist Deleted")
