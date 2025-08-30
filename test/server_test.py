from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from youtube_note.server import app
from youtube_note.model import YouTubeNote
from youtube_note.storage import get_db

client = TestClient(app)

def test_transcript_endpoint_renders_html_and_writes_db():
    fake_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    class Segment:
        def __init__(self, start: float, text: str) -> None:
            self.start = start
            self.text = text

    fake_transcript = [
        Segment(5.0, "Intro"),
        Segment(62.3, "Main content"),
    ]

    fake_llm_response = Mock()
    fake_llm_response.content = "# Test Summary\n\n- Bullet 1\n- Bullet 2"

    with patch("youtube_note.server.yt_client.fetch", return_value=fake_transcript), \
         patch("youtube_note.server.chain.invoke", return_value=fake_llm_response):
        response = client.post("/transcript", json={"youtube_url": fake_video_url})
        assert response.status_code == 200
        # Should return server-rendered HTML fragment (not JSON)
        assert "text/html" in response.headers.get("content-type", "")
        assert "Summary" in response.text
        assert "Transcript" in response.text

    # Verify database interaction
    with get_db() as db:
        note = db.query(YouTubeNote).filter(YouTubeNote.youtube_url == fake_video_url).first()
        assert note is not None
        assert "[00:05] Intro" in note.transcript
        assert "[01:02] Main content" in note.transcript
        assert isinstance(note.summary, str) and len(note.summary) > 0

def test_transcript_endpoint_validates_input():
    # Missing field
    response = client.post("/transcript", json={})
    assert response.status_code == 422

    # Wrong type
    response = client.post("/transcript", json={"youtube_url": 12345})
    assert response.status_code == 422

def test_transcript_endpoint_handles_youtube_errors():
    fake_video_url = "https://www.youtube.com/watch?v=no-transcript"
    with patch("youtube_note.server.yt_client.fetch", side_effect=Exception("Could not retrieve a transcript")):
        response = client.post("/transcript", json={"youtube_url": fake_video_url})
        assert response.status_code == 400
        assert "No transcript available" in response.text or "Failed to get transcript" in response.text

