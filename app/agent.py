from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.database import Database
from app.services.ai_workflow import AIWorkflow
from app.services.linkedin import LinkedInPublisher


DRAFT_START = "<!-- SIGNALPOST:DRAFT:START -->"
DRAFT_END = "<!-- SIGNALPOST:DRAFT:END -->"


class AgentError(RuntimeError):
    """Raised when an agent command cannot be completed safely."""


@dataclass(frozen=True)
class AgentRunResult:
    stories_found: int
    new_stories: int
    drafts_created: int
    flagged_drafts: int
    duplicate_stories: int
    post_ids: tuple[int, ...]


class ContentAgent:
    """Coordinates research, curation, writing, review, and publishing."""

    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        workflow: AIWorkflow | None = None,
        publisher: LinkedInPublisher | None = None,
    ):
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.workflow = workflow or AIWorkflow(settings)
        self.publisher = publisher or LinkedInPublisher(settings)

    def initialize(self) -> None:
        self.database.initialize()
        self.settings.outbox_path.mkdir(parents=True, exist_ok=True)

    def run(self) -> AgentRunResult:
        self.initialize()
        candidates = self.workflow.research_news()
        new_stories = 0
        duplicates = 0
        pending_story_ids: list[int] = []

        for candidate in candidates:
            if not candidate.eligible:
                continue
            story_id, created = self.database.add_story(candidate.to_record())
            new_stories += int(created)
            duplicates += int(not created)
            if self.database.get_post_by_story(story_id) is None:
                pending_story_ids.append(story_id)

        post_ids: list[int] = []
        flagged = 0
        for story_id in pending_story_ids[: self.settings.max_drafts_per_run]:
            story = self._require_story(story_id)
            draft = self.workflow.write_post(story)
            review = self.workflow.review_post(story, draft.linkedin_text)
            status = "needs_review" if review.approved else "ai_flagged"
            flagged += int(not review.approved)
            post_id = self.database.upsert_post(
                story_id=story_id,
                draft_text=review.corrected_draft,
                review=review.model_dump(),
                status=status,
            )
            self.database.set_story_status(story_id, "drafted")
            self.write_outbox(post_id)
            post_ids.append(post_id)

        return AgentRunResult(
            stories_found=len(candidates),
            new_stories=new_stories,
            drafts_created=len(post_ids),
            flagged_drafts=flagged,
            duplicate_stories=duplicates,
            post_ids=tuple(post_ids),
        )

    def review(self, post_id: int) -> dict[str, object]:
        self.initialize()
        post = self._require_post(post_id)
        story = self._require_story(int(post["story_id"]))
        edited_text = self.read_outbox_draft(post_id)
        review = self.workflow.review_post(story, edited_text)
        status = "needs_review" if review.approved else "ai_flagged"
        self.database.update_review(
            post_id,
            review.corrected_draft,
            review.model_dump(),
            status,
        )
        self.write_outbox(post_id)
        return self._require_post(post_id)

    def approve(self, post_id: int, publish: bool = False) -> dict[str, object]:
        post = self.review(post_id)
        if not post.get("review", {}).get("approved", False):
            summary = post.get("review", {}).get(
                "reviewer_summary", "The AI review found unresolved issues."
            )
            raise AgentError(f"Draft #{post_id} was not approved: {summary}")

        self.database.update_post(post_id, str(post["draft_text"]), "approved")
        self.write_outbox(post_id)
        if publish:
            return self.publish(post_id)
        return self._require_post(post_id)

    def reject(self, post_id: int) -> dict[str, object]:
        self.initialize()
        post = self._require_post(post_id)
        if post.get("status") == "published":
            raise AgentError("A published LinkedIn post cannot be rejected locally.")
        self.database.update_post(post_id, str(post["draft_text"]), "rejected")
        self.write_outbox(post_id)
        return self._require_post(post_id)

    def publish(self, post_id: int) -> dict[str, object]:
        self.initialize()
        post = self._require_post(post_id)
        if post.get("linkedin_post_urn"):
            return post
        if post.get("status") != "approved":
            raise AgentError(
                f"Draft #{post_id} must be approved before it can be published."
            )

        result = self.publisher.publish_text(str(post["draft_text"]))
        self.database.mark_published(post_id, result.post_urn)
        self.write_outbox(post_id)
        return self._require_post(post_id)

    def read_outbox_draft(self, post_id: int) -> str:
        post = self._require_post(post_id)
        path = self.outbox_file(post_id)
        if not path.exists():
            return str(post["draft_text"])
        content = path.read_text(encoding="utf-8")
        try:
            edited = content.split(DRAFT_START, 1)[1].split(DRAFT_END, 1)[0].strip()
        except IndexError as exc:
            raise AgentError(
                f"Draft markers are missing from {path}. Restore them before approval."
            ) from exc
        if len(edited) < 80:
            raise AgentError("The edited LinkedIn draft must be at least 80 characters.")
        return edited

    def write_outbox(self, post_id: int) -> Path:
        post = self._require_post(post_id)
        review = post.get("review", {})
        findings = {
            "unsupported_claims": review.get("unsupported_claims", []),
            "exaggerated_phrases": review.get("exaggerated_phrases", []),
            "possible_misrepresentations": review.get(
                "possible_misrepresentations", []
            ),
            "missing_context": review.get("missing_context", []),
        }
        content = (
            f"# LinkedIn draft #{post_id}\n\n"
            f"- Status: `{post['status']}`\n"
            f"- Story: {post['story_title']}\n"
            f"- Source: {post['source_url']}\n"
            f"- AI review: {review.get('reviewer_summary', 'Not reviewed')}\n"
            f"- LinkedIn post: {post.get('linkedin_post_urn') or 'Not published'}\n\n"
            "Edit only the text between the markers. The agent reads that section "
            "when you review or approve.\n\n"
            f"{DRAFT_START}\n"
            f"{post['draft_text'].strip()}\n"
            f"{DRAFT_END}\n\n"
            "## Review details\n\n"
            f"```json\n{json.dumps(findings, indent=2)}\n```\n"
        )
        path = self.outbox_file(post_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        return path

    def outbox_file(self, post_id: int) -> Path:
        return self.settings.outbox_path / f"post-{post_id}.md"

    def get_post(self, post_id: int) -> dict[str, object]:
        self.initialize()
        return self._require_post(post_id)

    def list_posts(self, limit: int = 30) -> list[dict[str, object]]:
        self.initialize()
        return self.database.list_posts(limit=limit)

    def _require_story(self, story_id: int) -> dict[str, object]:
        story = self.database.get_story(story_id)
        if story is None:
            raise AgentError(f"Story #{story_id} was not found.")
        return story

    def _require_post(self, post_id: int) -> dict[str, object]:
        post = self.database.get_post(post_id)
        if post is None:
            raise AgentError(f"Draft #{post_id} was not found.")
        return post
