from pathlib import Path

from app.database import Database
from app.services.demo_data import demo_stories


def test_story_and_post_lifecycle(tmp_path: Path):
    database = Database(tmp_path / "test.db")
    database.initialize()

    story_id, created = database.add_story(demo_stories()[0].to_record())
    assert created is True

    duplicate_id, duplicate_created = database.add_story(
        demo_stories()[0].to_record()
    )
    assert duplicate_id == story_id
    assert duplicate_created is False

    post_id = database.upsert_post(
        story_id,
        "A sufficiently long test draft that contains enough detail to be useful "
        "during database lifecycle testing for this portfolio application.",
        {"approved": True, "reviewer_summary": "Passed"},
    )
    post = database.get_post(post_id)
    assert post is not None
    assert post["story_id"] == story_id
    assert post["review"]["approved"] is True

    database.update_post(post_id, post["draft_text"], "approved")
    assert database.get_post(post_id)["status"] == "approved"
    assert database.stats() == {
        "stories": 1,
        "drafts": 1,
        "approved": 1,
        "published": 0,
    }
