from django.urls import path
from .views import GetYoutubeTracksView

urlpatterns = [
    path(
        "get-youtube-tracks",
        GetYoutubeTracksView.as_view(),
        name="get_youtube_tracks",
    ),
]
