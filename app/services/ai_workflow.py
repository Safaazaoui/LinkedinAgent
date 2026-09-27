from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.config import BASE_DIR, Settings
from app.schemas import DraftResult, ResearchResult, ReviewResult, StoryCandidate
from app.services.demo_data import demo_draft, demo_review, demo_stories


class AIWorkflow:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            OpenAI(api_key=settings.openai_api_key)
            if settings.live_ai_enabled
            else None
        )

    @staticmethod
    def _prompt(name: str) -> str:
        return (BASE_DIR / "prompts" / name).read_text(encoding="utf-8")

    def research_news(self) -> list[StoryCandidate]:
        if self.client is None:
            local_today = datetime.now(ZoneInfo(self.settings.timezone)).date()
            return demo_stories(local_today)

        now = datetime.now(UTC)
        prompt = self._prompt("researcher.md").format(
            current_date=now.date().isoformat(),
            cutoff_date=(now - timedelta(hours=72)).date().isoformat(),
            student_profile=self.settings.student_profile,
        )
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            tools=[{"type": "web_search"}],
            include=["web_search_call.action.sources"],
            input=prompt,
            text_format=ResearchResult,
            text={"verbosity": "medium"},
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return structured research results.")
        return [
            candidate
            for candidate in response.output_parsed.stories
            if candidate.eligible
        ]

    def write_post(self, story: dict[str, Any]) -> DraftResult:
        if self.client is None:
            return demo_draft(story)

        prompt = self._prompt("writer.md").format(
            student_profile=self.settings.student_profile,
            story_json=json.dumps(story, ensure_ascii=False, indent=2),
        )
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            input=prompt,
            text_format=DraftResult,
            text={"verbosity": "medium"},
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return a structured LinkedIn draft.")
        return response.output_parsed

    def review_post(self, story: dict[str, Any], draft_text: str) -> ReviewResult:
        if self.client is None:
            return demo_review(draft_text)

        prompt = self._prompt("reviewer.md").format(
            student_profile=self.settings.student_profile,
            story_json=json.dumps(story, ensure_ascii=False, indent=2),
            draft_text=draft_text,
        )
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            input=prompt,
            text_format=ReviewResult,
            text={"verbosity": "medium"},
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI did not return a structured draft review.")
        return response.output_parsed
