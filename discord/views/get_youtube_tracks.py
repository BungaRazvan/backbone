from typing import Optional

import sentry_sdk


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

            sentry_sdk.capture_exception(e)

            return HttpResponse({"error": str(e)}, status=500)

        return JsonResponse(tracks, safe=False)


def resolve_ytld_opts(
    url, title: Optional[str] = None, allow_rd_playlist: bool = False
):
    ydl_opts = {
        "dump_single_json": True,
        "quiet": True,
        "extract_flat": True,
    }

    if not title and ("list=RD" in (url or "") and not allow_rd_playlist):
        ydl_opts["noplaylist"] = True
        # raise Exception()

    return ydl_opts


def get_youtube_info(
    url: str, title: Optional[str] = None, *, allow_rd_playlist: bool = False
):
    ydl_opts = resolve_ytld_opts(url, title, allow_rd_playlist=allow_rd_playlist)

    with YoutubeDL(ydl_opts) as ydl:
        if title:
            data = ydl.extract_info(f"ytsearch:{title}", download=False)
        else:
            data = ydl.extract_info(url, download=False)

    if allow_rd_playlist:
        return data

    # If YoutubeTab URL pointing to a playlist, fast re-fetch
    # or url is part of a auto-gen mix fetch just the one song
    if data.get("_type") == "url" and (
        "playlist?list=" in data.get("url", "")
        or "list=RD" in data.get("original_url", "")
    ):
        refetch_url = data.get("url")
        ydl_opts = resolve_ytld_opts(refetch_url)

        with YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(data["url"], download=False)

    with open("yt.json", "w") as f:
        import json

        f.write(json.dumps(data, indent=2))

    return data


def get_videos(data):
    tracks = []

    if "entries" in data:

        for entry in data["entries"]:
            video_id = entry.get("id") or entry.get("url")
            tracks.append(
                {
                    "title": entry.get("title"),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )
    else:
        tracks.append(
            {
                "title": data.get("title"),
                "url": f"https://www.youtube.com/watch?v={data['id']}",
            }
        )

    return tracks
