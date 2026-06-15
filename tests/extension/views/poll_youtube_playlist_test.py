import pytest
from unittest.mock import patch


@pytest.fixture
def mock_celery_started():
    with patch("extension.views.scan_youtube_playlist.AsyncResult") as mock_async:
        mock_async.return_value.state = "STARTED"
        mock_async.return_value.info = {
            "current": 1,
            "total": 1,
            "percent": 100,
            "last_title": "Started title",
        }
        yield mock_async


@pytest.fixture
def mock_celery_progress():
    with patch("extension.views.scan_youtube_playlist.AsyncResult") as mock_async:
        mock_async.return_value.state = "PROGRESS"
        mock_async.return_value.info = {
            "current": 5,
            "total": 10,
            "percent": 50,
            "last_title": "Example title",
        }
        yield mock_async


class TestPollYoutubePlaylist:
    URL = "/extension/poll-scan-youtube-playlist"

    def test_poll_includes_last_title_in_progress_state(
        self, db, client, mock_celery_progress
    ):
        response = client.get(
            self.URL,
            data={"task_id": "task-123"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200

        data = response.json()
        assert data["state"] == "PROGRESS"
        assert data["current"] == 5
        assert data["total"] == 10
        assert data["percent"] == 50
        assert data["last_title"] == "Example title"

    def test_poll_accepts_started_state_as_progress(
        self, db, client, mock_celery_started
    ):
        response = client.get(
            self.URL,
            data={"task_id": "task-123"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200

        data = response.json()
        assert data["state"] == "STARTED"
        assert data["percent"] == 100
        assert data["last_title"] == "Started title"
