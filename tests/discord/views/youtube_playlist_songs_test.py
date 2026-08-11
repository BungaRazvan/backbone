from unittest.mock import patch

from discord.models import YoutubePlaylist, YoutubeSong


class TestYoutubePlaylistSongsView:
    URL = "/discord/youtube-playlist-songs"

    @patch("discord.views.youtube_playlist_songs.get_youtube_info")
    @patch("discord.views.youtube_playlist_songs.get_videos")
    def test_returns_video_tracks(self, mock_get_videos, mock_get_youtube_info, client):
        playlist = YoutubePlaylist.objects.create(
            yp_name="My Playlist",
            yp_user_id="user1",
            yp_guild_id="guild1",
        )
        YoutubeSong.objects.create(
            ys_url="https://youtu.be/abc123", ys_playlist=playlist
        )

        mock_get_youtube_info.return_value = {"id": "abc123", "title": "Song 1"}
        mock_get_videos.return_value = [
            {"title": "Song 1", "url": "https://www.youtube.com/watch?v=abc123"}
        ]

        response = client.get(
            self.URL,
            {
                "playlist_id": str(playlist.yp_id),
                "user_id": "user1",
                "guild_id": "guild1",
            },
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.json() == {
            "songs": [
                {"title": "Song 1", "url": "https://www.youtube.com/watch?v=abc123"}
            ]
        }
