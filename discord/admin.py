from django.contrib import admin


from discord.models import (
    QueueInterval,
    QueuePicture,
    YoutubePlaylist,
    YoutubeSong,
    MinecraftServer,
    MinecraftPlayer,
    MinecraftStat,
)


@admin.register(YoutubePlaylist)
class YoutubePlaylistAdmin(admin.ModelAdmin):
    pass


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
