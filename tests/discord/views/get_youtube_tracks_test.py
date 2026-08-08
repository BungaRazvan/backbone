from unittest.mock import patch


class TestGetYoutubeTracksView:
    URL = "/discord/get-youtube-tracks"

    @patch("discord.views.get_youtube_tracks.YoutubeDL")
    def test_returns_track_for_url(self, mock_youtube_dl, client):
        mock_ytdl = mock_youtube_dl.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {"id": "abc123", "title": "Song 1"}

        response = client.get(
            self.URL,
            {"url": "https://youtu.be/abc123"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.json() == [
            {"title": "Song 1", "url": "https://www.youtube.com/watch?v=abc123"}
        ]
        mock_youtube_dl.assert_called_once()
        mock_ytdl.extract_info.assert_called_once_with(
            "https://youtu.be/abc123", download=False
        )

    @patch("discord.views.get_youtube_tracks.YoutubeDL")
    def test_returns_tracks_for_title_search(self, mock_youtube_dl, client):
        mock_ytdl = mock_youtube_dl.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {"id": "abc123", "title": "Song 1"}

        response = client.get(
            self.URL,
            {"title": "Song 1"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.json() == [
            {"title": "Song 1", "url": "https://www.youtube.com/watch?v=abc123"}
        ]
        mock_youtube_dl.assert_called_once()
        mock_ytdl.extract_info.assert_called_once_with(
            "ytsearch:Song 1", download=False
        )

    @patch("discord.views.get_youtube_tracks.YoutubeDL")
    def test_returns_tracks_for_playlist_entries(self, mock_youtube_dl, client):
        mock_ytdl = mock_youtube_dl.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {
            "entries": [{"id": "abc123", "title": "Song 1"}]
        }

        response = client.get(
            self.URL,
            {"url": "https://youtu.be/abc123"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.json() == [
            {"title": "Song 1", "url": "https://www.youtube.com/watch?v=abc123"}
        ]
        mock_youtube_dl.assert_called_once()
        mock_ytdl.extract_info.assert_called_once_with(
            "https://youtu.be/abc123", download=False
        )

    def test_returns_bad_request_for_missing_args(self, client):
        response = client.get(
            self.URL,
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.content.decode() == "Missing Url or Title"
