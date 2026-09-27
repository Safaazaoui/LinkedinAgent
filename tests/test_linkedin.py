from pathlib import Path

import httpx

from app.config import Settings
from app.services.linkedin import LinkedInPublisher


def test_linkedin_publisher_uses_person_urn_and_official_posts_api(tmp_path: Path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            201,
            headers={"x-restli-id": "urn:li:share:123"},
            request=request,
        )

    settings = Settings(
        app_name="Test",
        timezone="America/Toronto",
        openai_api_key=None,
        openai_model="test-model",
        demo_mode=True,
        database_path=tmp_path / "test.db",
        outbox_path=tmp_path / "outbox",
        max_drafts_per_run=3,
        student_profile="Student",
        linkedin_access_token="private-token",
        linkedin_person_urn="urn:li:person:abc123",
        linkedin_api_version="202609",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = LinkedInPublisher(settings, client=client).publish_text(
        "A carefully reviewed LinkedIn post."
    )

    request = captured["request"]
    assert str(request.url) == "https://api.linkedin.com/rest/posts"
    assert request.headers["linkedin-version"] == "202609"
    assert b'"author":"urn:li:person:abc123"' in request.content
    assert result.post_urn == "urn:li:share:123"
