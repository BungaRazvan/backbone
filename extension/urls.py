from django.urls import path

from extension.views import YoutubePlaylistMissingVideos, YoutubeSavePlaylist

urlpatterns = [
    path(
        "youtube-playlist-missing-videos/<url>", YoutubePlaylistMissingVideos.as_view()
    ),
    path("youtube-save-playlist", YoutubeSavePlaylist.as_view()),
]
