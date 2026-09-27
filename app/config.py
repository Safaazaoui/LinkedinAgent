import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    parsed = int(value)
    if parsed < 1:
        raise ValueError("Integer settings must be at least 1.")
    return parsed


def _project_path(value: str, default: str) -> Path:
    configured = Path(value or default)
    return configured if configured.is_absolute() else BASE_DIR / configured


@dataclass(frozen=True)
class Settings:
    app_name: str
    timezone: str
    openai_api_key: str | None = field(repr=False)
    openai_model: str
    demo_mode: bool
    database_path: Path
    outbox_path: Path
    max_drafts_per_run: int
    student_profile: str
    linkedin_access_token: str | None = field(repr=False)
    linkedin_person_urn: str | None
    linkedin_api_version: str

    @property
    def live_ai_enabled(self) -> bool:
        return bool(self.openai_api_key) and not self.demo_mode

    @property
    def linkedin_enabled(self) -> bool:
        return bool(
            self.linkedin_access_token
            and self.linkedin_person_urn
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "SignalPost AI"),
        timezone=os.getenv("APP_TIMEZONE", "America/Toronto"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-6-astra"),
        demo_mode=_as_bool(os.getenv("DEMO_MODE"), default=False),
        database_path=_project_path(
            os.getenv("DATABASE_PATH", ""), "data/agent.db"
        ),
        outbox_path=_project_path(os.getenv("OUTBOX_PATH", ""), "outbox"),
        max_drafts_per_run=_as_int(os.getenv("MAX_DRAFTS_PER_RUN"), 3),
        student_profile=os.getenv(
            "STUDENT_PROFILE",
            "Third-year computer science student interested in AI, software "
            "development, developer tools, and emerging technology.",
        ),
        linkedin_access_token=(
            os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or None
        ),
        linkedin_person_urn=(
            os.getenv("LINKEDIN_PERSON_URN", "").strip() or None
        ),
        linkedin_api_version=os.getenv(
            "LINKEDIN_API_VERSION", "202609"
        ).strip(),
    )
    
