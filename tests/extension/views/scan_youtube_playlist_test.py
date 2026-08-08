import pytest
from unittest.mock import patch
from extension.tasks.scan_playlist import scan_youtube_playlist


@pytest.fixture
def celery_includes():
    return ["extension.tasks.scan_playlist"]


@pytest.fixture
def mock_yt_dlp():
    """A factory fixture that allows passing custom entries/info per test."""

    def _factory(entries=None, video_info=None):
        if entries is None:
            entries = [{"id": "abc123", "title": "Example title"}]

        if video_info is None:
            video_info = {"title": "Example title", "availability": None}

        class MockYoutubeDL:
            def __init__(self, opts=None):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download=False, process=False):
                if process is False:
                    return {"entries": entries}

                return video_info

        return patch("extension.tasks.scan_playlist.YoutubeDL", MockYoutubeDL)

    return _factory


class TestScanYoutubePlaylistView:
    URL = "/extension/scan-youtube-playlist/PL123"

    @pytest.mark.django_db(transaction=True)
    def test_dispatches_task(self, client, celery_app, celery_worker, mock_yt_dlp):

        with mock_yt_dlp() as mock_dl:
            response = client.get(
                self.URL,
                HTTP_X_API_KEY="test-token",
            )

            assert response.status_code == 200
            task_id = response.json()["task_id"]

            result = celery_app.AsyncResult(task_id)
            result.get(timeout=2.0)
            assert result.state == "SUCCESS"
