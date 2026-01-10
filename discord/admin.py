from django.contrib import admin
from django.utils.safestring import mark_safe


from discord.models import (
    YoutubePlaylist,
    YoutubeSong,
    MinecraftServer,
    MinecraftPlayer,
    MinecraftStat,
)


@admin.register(YoutubePlaylist)
class YoutubePlaylistAdmin(admin.ModelAdmin):
    fields = ("yp_name", "videos_table")
    readonly_fields = ("videos_table",)

    def videos_table(self, obj):

        rows = ""
        for song in obj.songs.all():
            rows += f"<tr><td>{song.ys_url}</td><tr>"
        html = f"<table style='border-collapse:collapse; width:100%;' border='1'><tr>{''.join(rows)}</table>"
        return mark_safe(html)


@admin.register(YoutubeSong)
class YoutubeSongAdmin(admin.ModelAdmin):
    pass


@admin.register(MinecraftServer)
class MinecraftServerAdmin(admin.ModelAdmin):
    pass


@admin.register(MinecraftPlayer)
class MinecraftPlayerAdmin(admin.ModelAdmin):
    pass


@admin.register(MinecraftStat)
class MinecraftStatAdmin(admin.ModelAdmin):
    pass
