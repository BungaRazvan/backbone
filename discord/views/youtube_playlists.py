import json
import re

from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from common.auth.backends import app_auth
from discord.models import YoutubePlaylist, YoutubeSong

from discord.views.get_youtube_tracks import get_videos, get_youtube_info

from distutils.util import strtobool
from dataclasses import dataclass
from django.utils.decorators import method_decorator
from common.auth.decorators import require_token, validate_arguments
from discord.views.minecraft_players import Args


@dataclass
class ArgsGet:
    user_id: str
    guild_id: str
    playlist_id: str = None
    play_mode: bool = False


@dataclass
class ArgsPost:
    user_id: str
    guild_id: str
    playlist_name: str
    playlist_songs: str


@dataclass
class ArgsPut:
    user_id: str
    guild_id: str
    playlist_id: str
    playlist_name: str
    playlist_songs: str


@dataclass
class ArgsDelete:
    user_id: str
    guild_id: str
    playlist_id: str


class YoutubePlaylistView(APIView):

    @method_decorator([require_token(app_name="discord"), validate_arguments(ArgsGet)])
    def get(self, request, args: ArgsGet):

        user_id = args.user_id
        guild_id = args.guild_id
        playlist_id = args.playlist_id
        play_mode = args.play_mode

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
                    yt_info = get_youtube_info(song.ys_url, allow_rd_playlist=True)
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

    @method_decorator([require_token(app_name="discord"), validate_arguments(ArgsPost)])
    def post(self, request, args: ArgsPost):

        user_id = args.user_id
        guild_id = args.guild_id
        name = args.playlist_name
        songs_list = args.playlist_songs

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

    @method_decorator([require_token(app_name="discord"), validate_arguments(ArgsPut)])
    def put(self, request, args: ArgsPut):
        user_id = args.user_id
        guild_id = args.guild_id
        playlist_id = args.playlist_id
        songs_list = args.playlist_songs
        name = args.playlist_name

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

    @method_decorator(
        [require_token(app_name="discord"), validate_arguments(ArgsDelete)]
    )
    def delete(self, request, args: ArgsDelete):
        user_id = args.user_id
        guild_id = args.guild_id
        playlist_id = args.playlist_id

        try:
            playlist = YoutubePlaylist.objects.get(
                yp_id=playlist_id, yp_user_id=user_id, yp_guild_id=guild_id
            )
            playlist.delete()

        except YoutubePlaylist.DoesNotExist:
            return HttpResponseBadRequest("Invalid request")

        return HttpResponse("Playlist Deleted")
