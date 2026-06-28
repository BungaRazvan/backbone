from django.views.generic import TemplateView

from common.utils import require_token
from discord.views.get_youtube_tracks import get_videos, get_youtube_info
from django.http import HttpResponse, HttpResponseBadRequest

from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from extension.models import YoutubePlaylist


@method_decorator(xframe_options_exempt, name="dispatch")
class YoutubePlaylistMissingVideos(TemplateView):
    http_method_names = ["get"]
    template_name = "missing_videos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["playlist_url"] = kwargs.get("url")

        return context

    def render_missing_videos(self, playlist_url):
        youtube_data = get_youtube_info(
            "https://www.youtube.com/playlist?list=" + playlist_url
        )
        youtube_videos = get_videos(youtube_data) or []

        if not youtube_data or not youtube_data.get("title"):
            return render_to_string(
                "missing_videos_list.html",
                {
                    "missing_videos": [],
                    "extra_videos": [],
                    "error": "Unable to load the playlist details right now.",
                },
            )

        try:
            saved_playlist = YoutubePlaylist.objects.get(
                yp_name=youtube_data.get("title")
            )
            saved_videos = saved_playlist.yp_videos or []

        except YoutubePlaylist.DoesNotExist:
            return render_to_string(
                "missing_videos_list.html",
                {
                    "missing_videos": [],
                    "extra_videos": [],
                    "error": "This playlist has not been saved yet.",
                },
            )

        saved_titles = {item.get("title") for item in saved_videos if item.get("title")}
        youtube_titles = {
            item.get("title") for item in youtube_videos if item.get("title")
        }

        missing_videos = [
            {"title": title} for title in sorted(saved_titles - youtube_titles)
        ]
        extra_videos = [
            {"title": title} for title in sorted(youtube_titles - saved_titles)
        ]

        return render_to_string(
            "missing_videos_list.html",
            {
                "missing_videos": missing_videos,
                "extra_videos": extra_videos,
            },
        )

    def get(self, request, *args, **kwargs):
        if kwargs.get("url") and request.headers.get("Hx-Trigger") == "videos-list":
            html = self.render_missing_videos(kwargs.get("url"))
            return HttpResponse(html)

        context = self.get_context_data(**kwargs)
        context["token"] = kwargs.get("token")

        return self.render_to_response(context)
