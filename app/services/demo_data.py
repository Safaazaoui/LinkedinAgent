from __future__ import annotations

from datetime import date

from app.schemas import DraftResult, ReviewResult, StoryCandidate


def demo_stories(today: date | None = None) -> list[StoryCandidate]:
    """
    Return fake AI news stories for testing the agent without an API key.

    These stories are demonstrations only. They are not real news.
    """

    today = today or date.today()

    return [
        StoryCandidate(
            title=(
                "Demo: Open-source AI tool makes local experimentation "
                "easier for students"
            ),
            summary=(
                "This fictional demonstration story describes an open-source "
                "AI tool designed to help students run small experiments on "
                "their own computers with clearer setup instructions."
            ),
            why_positive=(
                "Accessible open-source tools can help students understand how "
                "AI systems work instead of interacting only with closed "
                "commercial products."
            ),
            student_angle=(
                "Computer science students could use a tool like this to learn "
                "about model evaluation, document technical tradeoffs, and "
                "create a small portfolio experiment."
            ),
            published_at=today,
            primary_source_url=(
                "https://example.com/demo-open-source-ai-tool"
            ),
            additional_source_urls=[],
            credibility_score=9,
            positivity_score=8,
            student_relevance_score=9,
            confidence_score=9,
        ),
        StoryCandidate(
            title=(
                "Demo: AI accessibility research improves interface "
                "descriptions"
            ),
            summary=(
                "This fictional research story explores an AI system that "
                "creates clearer descriptions of application interfaces for "
                "people who use assistive technology."
            ),
            why_positive=(
                "Clearer interface descriptions could make digital products "
                "easier to use and encourage development teams to include "
                "accessibility earlier in the software process."
            ),
            student_angle=(
                "The story gives computer science students a practical reason "
                "to consider accessibility during requirements, design, "
                "implementation, and testing."
            ),
            published_at=today,
            primary_source_url=(
                "https://example.com/demo-ai-accessibility-research"
            ),
            additional_source_urls=[],
            credibility_score=8,
            positivity_score=9,
            student_relevance_score=8,
            confidence_score=8,
        ),
        StoryCandidate(
            title=(
                "Demo: Energy-efficient AI model reduces computing "
                "requirements"
            ),
            summary=(
                "This fictional demonstration story describes a smaller AI "
                "model that performs a focused programming task while using "
                "less computing power than a much larger general-purpose model."
            ),
            why_positive=(
                "More efficient models could reduce infrastructure costs and "
                "make useful AI experiments available to schools and developers "
                "with limited computing resources."
            ),
            student_angle=(
                "Students could compare model size, response quality, speed, "
                "and resource consumption to better understand engineering "
                "tradeoffs in machine learning systems."
            ),
            published_at=today,
            primary_source_url=(
                "https://example.com/demo-efficient-ai-model"
            ),
            additional_source_urls=[],
            credibility_score=8,
            positivity_score=8,
            student_relevance_score=9,
            confidence_score=8,
        ),
    ]


def demo_draft(story: dict[str, object]) -> DraftResult:
    """
    Turn a fake story into a predictable LinkedIn draft.

    This replaces the OpenAI writing call while the agent is in demo mode.
    """

    return DraftResult(
        hook=(
            "A useful AI update becomes more interesting when we ask "
            "what students can learn from it."
        ),
        body=(
            f"{story['summary']}\n\n"
            f"What makes this development constructive is that "
            f"{story['why_positive']}\n\n"
            f"For computer science students, the learning opportunity is "
            f"also practical: {story['student_angle']}\n\n"
            "I am trying to look beyond exciting AI headlines and focus on "
            "the engineering decisions, limitations, and real problems behind "
            "each development."
        ),
        closing_question=(
            "What recent AI development has given you an idea for a "
            "student project?"
        ),
        hashtags=["AI", "ComputerScience"],
        factual_claims=[
            str(story["summary"]),
            str(story["why_positive"]),
        ],
    )


def demo_review(draft_text: str) -> ReviewResult:
    """
    Return a predictable successful review for a demonstration draft.

    This replaces the OpenAI reviewer call while testing locally.
    """

    return ReviewResult(
        approved=True,
        unsupported_claims=[],
        exaggerated_phrases=[],
        possible_misrepresentations=[],
        missing_context=[],
        corrected_draft=draft_text,
        reviewer_summary=(
            "Demo review passed. The post uses an appropriate student voice, "
            "avoids exaggerated language, and does not invent personal "
            "experience."
        ),
    )