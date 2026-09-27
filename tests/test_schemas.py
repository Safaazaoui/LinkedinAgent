from app.services.demo_data import demo_stories


def test_demo_stories_pass_quality_gate():
    stories = demo_stories()
    assert stories
    assert all(story.eligible for story in stories)


def test_story_records_serialize_urls_and_dates():
    record = demo_stories()[0].to_record()
    assert record["published_at"]
    assert record["primary_source_url"].startswith("https://")
