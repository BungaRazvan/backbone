from django.contrib import admin


from discord_core.models import (
    QueueInterval,
    QueuePicture,
    YoutubePlaylist,
    YoutubeSong,
)


@admin.register(YoutubePlaylist)
class YoutubePlaylistAdmin(admin.ModelAdmin):
    pass


@admin.register(YoutubeSong)
class YoutubeSongAdmin(admin.ModelAdmin):
    pass
