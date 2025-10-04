from django.views.generic import TemplateView

from common.models import AppToken
from discord.views.get_youtube_tracks import get_videos, get_youtube_info
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden

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
        youtube_videos = get_videos(youtube_data)

        try:
            saved_videos = YoutubePlaylist.objects.get(
                yp_name=youtube_data.get("title")
            ).yp_videos
        except YoutubePlaylist.DoesNotExist:
            return "<h1>Youtube playlist not saved</h1>"

        saved_titles = [v.get("title") for v in saved_videos]
        youtube_titles = [v.get("title") for v in youtube_videos]

        missing_videos = [{"title": v} for v in saved_titles if v not in youtube_titles]

        return render_to_string(
            "missing_videos_list.html", {"missing_videos": missing_videos}
        )

    def get(self, request, *args, **kwargs):
        if kwargs.get("url") and request.headers.get("Hx-Trigger") == "videos-list":
            html = self.render_missing_videos(kwargs.get("url"))
            return HttpResponse(html)

        if not kwargs.get("token"):
            return HttpResponseBadRequest("Token not provided")

        try:
            AppToken.objects.get(
                at_app_token=kwargs.get("token"),
                at_is_active=True,
                at_app_name="extension",
            )
        except AppToken.DoesNotExist:
            return HttpResponseForbidden("Invalid or inactive token")

        context = self.get_context_data(**kwargs)
        context["token"] = kwargs.get("token")

        return self.render_to_response(context)
