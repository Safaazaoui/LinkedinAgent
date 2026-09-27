from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class StoryCandidate(BaseModel):
    title: str = Field(min_length=8, max_length=240)
    summary: str = Field(min_length=30, max_length=1600)
    why_positive: str = Field(min_length=20, max_length=900)
    student_angle: str = Field(min_length=20, max_length=900)
    published_at: str
    primary_source_url: str
    additional_source_urls: list[str] = Field(default_factory=list, max_length=4)
    credibility_score: int = Field(ge=0, le=10)
    positivity_score: int = Field(ge=0, le=10)
    student_relevance_score: int = Field(ge=0, le=10)
    confidence_score: int = Field(ge=0, le=10)

    @field_validator("title", "summary", "why_positive", "student_angle")
    @classmethod
    def normalize_whitespace(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("published_at", mode="before")
    @classmethod
    def validate_publication_date(cls, value: object) -> str:
        normalized = value.isoformat() if isinstance(value, date) else str(value)
        date.fromisoformat(normalized)
        return normalized

    @field_validator("primary_source_url")
    @classmethod
    def validate_primary_url(cls, value: str) -> str:
        return cls._validated_https_url(value)

    @field_validator("additional_source_urls")
    @classmethod
    def validate_additional_urls(cls, values: list[str]) -> list[str]:
        return [cls._validated_https_url(value) for value in values]

    @staticmethod
    def _validated_https_url(value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Source URLs must be complete HTTPS URLs.")
        return value

    @property
    def eligible(self) -> bool:
        return (
            self.credibility_score >= 8
            and self.positivity_score >= 7
            and self.student_relevance_score >= 6
            and self.confidence_score >= 8
        )

    def to_record(self) -> dict[str, object]:
        return {
            "title": self.title,
            "summary": self.summary,
            "why_positive": self.why_positive,
            "student_angle": self.student_angle,
            "published_at": self.published_at,
            "primary_source_url": self.primary_source_url,
            "additional_source_urls": self.additional_source_urls,
            "credibility_score": self.credibility_score,
            "positivity_score": self.positivity_score,
            "student_relevance_score": self.student_relevance_score,
            "confidence_score": self.confidence_score,
        }


class ResearchResult(BaseModel):
    stories: list[StoryCandidate] = Field(min_length=1, max_length=5)


class DraftResult(BaseModel):
    hook: str = Field(min_length=5, max_length=300)
    body: str = Field(min_length=80, max_length=3000)
    closing_question: str = Field(min_length=5, max_length=300)
    hashtags: list[str] = Field(default_factory=list, max_length=2)
    factual_claims: list[str] = Field(default_factory=list, max_length=12)

    @property
    def linkedin_text(self) -> str:
        sections = [self.hook.strip(), self.body.strip(), self.closing_question.strip()]
        tags = " ".join(
            tag if tag.startswith("#") else f"#{tag}" for tag in self.hashtags
        )
        if tags:
            sections.append(tags)
        return "\n\n".join(section for section in sections if section)


class ReviewResult(BaseModel):
    approved: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    exaggerated_phrases: list[str] = Field(default_factory=list)
    possible_misrepresentations: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    corrected_draft: str = Field(min_length=80, max_length=4000)
    reviewer_summary: str = Field(min_length=5, max_length=600)
