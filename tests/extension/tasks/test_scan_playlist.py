from extension.tasks.scan_playlist import get_unavailable_tracks


def test_get_unavailable_tracks_marks_private_and_deleted_items():
    playlist_data = {
        "entries": [
            {"id": "ok-1", "title": "Available", "availability": "public"},
            {"id": "bad-1", "title": "Private", "availability": "private"},
            {"id": "bad-2", "title": "Deleted", "availability": "unavailable"},
            {"id": "bad-3", "title": "Removed", "availability": "removed"},
        ]
    }

    unavailable = get_unavailable_tracks(playlist_data)

    assert [item["id"] for item in unavailable] == ["bad-1", "bad-2", "bad-3"]
    assert unavailable[0]["reason"] == "private"
    assert unavailable[1]["reason"] == "unavailable"
    assert unavailable[2]["reason"] == "removed"
