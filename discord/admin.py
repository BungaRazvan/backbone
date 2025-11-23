from django.contrib import admin


from discord.models import QueueInterval, QueuePicture, YoutubePlaylist, YoutubeSong


@admin.register(YoutubePlaylist)
class YoutubePlaylistAdmin(admin.ModelAdmin):
    pass


@admin.register(YoutubeSong)
class YoutubeSongAdmin(admin.ModelAdmin):
    pass
