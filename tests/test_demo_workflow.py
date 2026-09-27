from pathlib import Path

from app.config import Settings
from app.services.ai_workflow import AIWorkflow


def test_demo_workflow_runs_without_api_key(tmp_path: Path):
    settings = Settings(
        app_name="Test",
        timezone="America/Toronto",
        openai_api_key=None,
        openai_model="test-model",
        demo_mode=True,
        database_path=tmp_path / "test.db",
        outbox_path=tmp_path / "outbox",
        max_drafts_per_run=3,
        student_profile="Third-year computer science student.",
        linkedin_access_token=None,
        linkedin_person_urn=None,
        linkedin_api_version="202609",
    )
    workflow = AIWorkflow(settings)
    story = workflow.research_news()[0].to_record()
    draft = workflow.write_post(story)
    review = workflow.review_post(story, draft.linkedin_text)

    assert draft.linkedin_text
    assert review.approved is True
    assert review.corrected_draft == draft.linkedin_text
