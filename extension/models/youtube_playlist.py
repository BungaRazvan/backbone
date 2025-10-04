from common.models.youtube_playlist import BaseYoutubePlaylist


class YoutubePlaylist(BaseYoutubePlaylist):
    class Meta:
        db_table = "youtube_playlist"
        app_label = "extension"
