from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from yt_dlp import YoutubeDL


class GetYoutubeTracksView(APIView):
    http_method_names = ["get"]

    def get(self, request):
        url = request.GET.get("url") or None
        title = request.GET.get("title") or None

        if not url and not title:
            return HttpResponseBadRequest("Missing Url or Title")

        try:
            data = get_youtube_info(url, title)
            tracks = get_videos(data)
        except Exception as e:
            return HttpResponse({"error": str(e)}, status=500)

        return JsonResponse(tracks, safe=False)


def get_youtube_info(url, title=None):

    ydl_opts = {
        "dump_single_json": True,
        "extract_flat": True,
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        if title:
            data = ydl.extract_info(f"ytsearch:{title}", download=False)
        else:
            data = ydl.extract_info(url, download=False)

    return data


def get_videos(data):

    tracks = []

    import json

    print(json.dumps(data, indent=2))

    if "entries" in data:
        # Playlist
        for entry in data["entries"]:
            tracks.append(
                {
                    "title": entry.get("title"),
                    "url": entry.get("url"),
                }
            )
    else:
        # Single video
        tracks.append(
            {
                "title": data.get("title"),
                "url": data.get("url"),
            }
        )

    return tracks
