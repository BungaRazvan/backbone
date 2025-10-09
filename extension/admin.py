from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import YoutubePlaylist


@admin.register(YoutubePlaylist)
class YoutubePlaylistAdmin(admin.ModelAdmin):
    fields = ("yp_name", "videos_table")
    readonly_fields = (
        "videos_table",
        "yp_name",
    )

    def videos_table(self, obj):
        if not obj.yp_videos:
            return "No videos available."

        headers = ["Title", "URL"]
        rows = ""
        for v in obj.yp_videos:
            rows += f"<tr><td>{v.get('title','')}</td><td><a href='{v.get('url','#')}' target='_blank'>Link</a></td></tr>"
        html = f"<table style='border-collapse:collapse; width:100%;' border='1'><tr>{''.join(rows)}</table>"
        return mark_safe(html)
