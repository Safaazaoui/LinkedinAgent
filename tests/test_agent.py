from pathlib import Path

import pytest

from app.agent import AgentError, DRAFT_END, DRAFT_START, ContentAgent
from app.config import Settings
from app.services.linkedin import LinkedInPublishResult


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        app_name="Test Agent",
        timezone="America/Toronto",
        openai_api_key=None,
        openai_model="test-model",
        demo_mode=True,
        database_path=tmp_path / "agent.db",
        outbox_path=tmp_path / "outbox",
        max_drafts_per_run=3,
        student_profile="Third-year computer science student.",
        linkedin_access_token=None,
        linkedin_person_urn=None,
        linkedin_api_version="202609",
    )


def test_agent_creates_editable_drafts_and_approves_one(tmp_path: Path):
    agent = ContentAgent(settings_for(tmp_path))

    result = agent.run()

    assert result.new_stories == 3
    assert result.drafts_created == 3
    first_post_id = result.post_ids[0]
    outbox = agent.outbox_file(first_post_id)
    assert outbox.exists()
    assert DRAFT_START in outbox.read_text(encoding="utf-8")

    content = outbox.read_text(encoding="utf-8")
    edited = (
        "I am interested in how this constructive AI development can make "
        "experimentation more accessible to computer science students. "
        "The source provides a useful starting point for evaluating tradeoffs."
    )
    before, remainder = content.split(DRAFT_START, 1)
    _, after = remainder.split(DRAFT_END, 1)
    outbox.write_text(
        f"{before}{DRAFT_START}\n{edited}\n{DRAFT_END}{after}",
        encoding="utf-8",
    )

    approved = agent.approve(first_post_id)
    assert approved["status"] == "approved"
    assert approved["draft_text"] == edited

    second_run = agent.run()
    assert second_run.new_stories == 0
    assert second_run.drafts_created == 0


def test_unapproved_post_cannot_be_published(tmp_path: Path):
    agent = ContentAgent(settings_for(tmp_path))
    post_id = agent.run().post_ids[0]

    with pytest.raises(AgentError, match="must be approved"):
        agent.publish(post_id)


def test_published_post_is_idempotent(tmp_path: Path):
    class FakePublisher:
        def __init__(self):
            self.calls = 0

        def publish_text(self, _: str) -> LinkedInPublishResult:
            self.calls += 1
            return LinkedInPublishResult("urn:li:share:published-once")

    publisher = FakePublisher()
    agent = ContentAgent(settings_for(tmp_path), publisher=publisher)
    post_id = agent.run().post_ids[0]
    agent.approve(post_id)

    first = agent.publish(post_id)
    second = agent.publish(post_id)

    assert first["status"] == "published"
    assert second["linkedin_post_urn"] == "urn:li:share:published-once"
    assert publisher.calls == 1
