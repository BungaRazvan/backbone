from django.urls import path

from discord.views import GetYoutubeTracksView

urlpatterns = [path("get-youtube-tracks", GetYoutubeTracksView.as_view())]
