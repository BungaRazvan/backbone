from django.urls import path
from .views import (
    GetYoutubeTracksView,
    YoutubePlaylistSongsView,
    YoutubePlaylistView,
    MinecraftStatsView,
    MinecraftPlayersView,
)

urlpatterns = [
    path(
        "get-youtube-tracks",
        GetYoutubeTracksView.as_view(),
    ),
    path("youtube-playlist-songs", YoutubePlaylistSongsView.as_view()),
    path("youtube-playlist", YoutubePlaylistView.as_view()),
    path("minecraft-stats", MinecraftStatsView.as_view()),
    path("minecraft-players", MinecraftPlayersView.as_view()),
]
