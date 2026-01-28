from celery import shared_task
from yt_dlp import YoutubeDL
import json


@shared_task(bind=True)
def scan_youtube_playlist(self, url: str) -> dict:
    ydl_opts_flat = {
        "extract_flat": True,
        "quiet": True,
    }

    with YoutubeDL(ydl_opts_flat) as ydl:
        playlist_data = ydl.extract_info(url, download=False, process=False)

        if "entries" not in playlist_data:
            return {"error": "No videos found or not a playlist"}

        entries = list(playlist_data["entries"])
        total_count = len(entries)
        results = []

        ydl_opts_detail = {
            "quiet": True,
            "no_warnings": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }

        for i, entry in enumerate(entries, 1):
            video_id = entry.get("id")
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            try:
                with YoutubeDL(ydl_opts_detail) as ydl_inner:
                    info = ydl_inner.extract_info(video_url, download=False)

                results.append(
                    {
                        "id": video_id,
                        "title": info.get("title"),
                        "availability": info.get("availability"),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "id": video_id,
                        "title": entry.get("title", "Unavailable"),
                        "availability": "private_or_deleted",
                    }
                )

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_count,
                    "percent": int((i / total_count) * 100),
                    "last_title": entry.get("title"),
                },
            )

    return {"status": "Complete", "videos": results}
