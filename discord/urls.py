from django.urls import path
from .views import GetYoutubeTracksView, YoutubePlaylistSongsView, YoutubePlaylistView

urlpatterns = [
    path(
        "get-youtube-tracks",
        GetYoutubeTracksView.as_view(),
    ),
    path("youtube-playlist-songs", YoutubePlaylistSongsView.as_view()),
    path("youtube-playlist", YoutubePlaylistView.as_view()),
]
