import pytest

from unittest.mock import patch

from extension.models import YoutubePlaylist


@pytest.fixture
def mock_youtube_api():
    """
    Globally mocks out the yt-dlp/YouTube API calls.
    Yields a tuple of (mock_get_info, mock_get_videos).
    """

    with patch(
        "extension.views.youtube_playlist_missing_videos.get_youtube_info"
    ) as mock_info, patch(
        "extension.views.youtube_playlist_missing_videos.get_videos"
    ) as mock_videos:
        yield mock_info, mock_videos


@pytest.fixture
def playlist(db):
    return YoutubePlaylist.objects.create(
        yp_name="SQLite Demo Playlist",
        yp_videos=[{"title": "Track A"}, {"title": "Track B"}],
    )


class TestYoutubePlaylistMissingVideos:
    URL = "/extension/youtube-playlist-missing-videos/test-token/a"

    def test_base_page_shell_renders_without_htmx(self, client):
        """
        Tests the initial non-HTMX page load. It shouldn't trigger
        the YouTube API or look up playlists yet.
        """

        response = client.get(self.URL)
        assert response.status_code == 200

        html = response.content.decode("utf-8")
        assert "Save & Reload" in html
        assert "Full Scan" in html

    def test_happy_path_calculates_missing_and_extra_videos(
        self, client, playlist, mock_youtube_api
    ):
        """
        Tests that when live YouTube tracks differ from saved database tracks,
        the view correctly determines what's missing and what's extra.
        """
        mock_info, mock_videos = mock_youtube_api

        # Match the playlist fixture name to trick the get() query
        mock_info.return_value = {"title": "SQLite Demo Playlist"}

        # Playlist fixture has: Track A, Track B
        # Live YouTube has: Track A, Track C
        mock_videos.return_value = [{"title": "Track A"}, {"title": "Track C"}]

        response = client.get(self.URL, HTTP_HX_TRIGGER="videos-list")
        assert response.status_code == 200

        html = response.content.decode("utf-8")

        # Track B is in DB but not on YouTube -> Missing
        assert "Track B" in html
        # Track C is on YouTube but not in DB -> Extra / Not saved
        assert "Track C" in html

    def test_api_failure_returns_graceful_error_message(self, client, mock_youtube_api):
        """
        Tests how the view handles yt-dlp returning empty data or None.
        """
        mock_info, mock_videos = mock_youtube_api
        mock_info.return_value = None  # Simulate API drop/parsing failure
        mock_videos.return_value = []

        response = client.get(self.URL, HTTP_HX_TRIGGER="videos-list")
        assert response.status_code == 200

        html = response.content.decode("utf-8")
        assert "Unable to load the playlist details right now." in html

    def test_playlist_not_yet_saved_in_database(self, client, mock_youtube_api):
        """
        Tests behavior when the user opens a playlist that exists on YouTube
        but has never been committed to our Django database.
        """
        mock_info, mock_videos = mock_youtube_api
        mock_info.return_value = {"title": "A Brand New Playlist"}
        mock_videos.return_value = [{"title": "Some Track"}]

        response = client.get(self.URL, HTTP_HX_TRIGGER="videos-list")
        assert response.status_code == 200

        html = response.content.decode("utf-8")
        assert "This playlist has not been saved yet." in html
