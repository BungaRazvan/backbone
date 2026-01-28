from django.urls import path

from extension.views import (
    YoutubePlaylistMissingVideos,
    YoutubeSavePlaylist,
    ScanYoutubePlaylist,
    PollYoutubePlaylist,
)

urlpatterns = [
    path(
        "scan-youtube-playlist-missing-videos/<token>/<url>",
        YoutubePlaylistMissingVideos.as_view(),
    ),
    path(
        "trigger-scan-youtube-playlist",
        ScanYoutubePlaylist.as_view(),
    ),
    path(
        "poll-scan-youtube-playlist",
        PollYoutubePlaylist.as_view(),
    ),
    path("youtube-save-playlist", YoutubeSavePlaylist.as_view()),
]
