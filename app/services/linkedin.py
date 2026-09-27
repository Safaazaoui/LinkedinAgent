from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


class LinkedInPublishError(RuntimeError):
    """Raised when a LinkedIn request cannot be completed safely."""


@dataclass(frozen=True)
class LinkedInPublishResult:
    post_urn: str


class LinkedInPublisher:
    POSTS_URL = "https://api.linkedin.com/rest/posts"
    USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
    ):
        self.settings = settings
        self.client = client or httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        if not self.settings.linkedin_access_token:
            raise LinkedInPublishError(
                "LINKEDIN_ACCESS_TOKEN is missing. Run `python -m app doctor`."
            )
        return {
            "Authorization": f"Bearer {self.settings.linkedin_access_token}",
            "Content-Type": "application/json",
            "Linkedin-Version": self.settings.linkedin_api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def member_profile(self) -> dict[str, Any]:
        response = self.client.get(self.USERINFO_URL, headers=self._headers())
        if response.status_code != 200:
            raise LinkedInPublishError(self._api_error(response))
        payload = response.json()
        if not isinstance(payload, dict):
            raise LinkedInPublishError("LinkedIn returned an invalid profile response.")
        return payload

    def publish_text(self, text: str) -> LinkedInPublishResult:
        cleaned = text.strip()
        if not cleaned:
            raise LinkedInPublishError("Refusing to publish an empty post.")
        if len(cleaned) > 3000:
            raise LinkedInPublishError(
                "LinkedIn text posts are limited to 3,000 characters. "
                "Shorten the draft before publishing."
            )
        if not self.settings.linkedin_person_urn:
            raise LinkedInPublishError(
                "LINKEDIN_PERSON_URN is missing. Run `python -m app linkedin-whoami`."
            )

        author = self.settings.linkedin_person_urn
        if not author.startswith("urn:li:person:"):
            author = f"urn:li:person:{author}"

        response = self.client.post(
            self.POSTS_URL,
            headers=self._headers(),
            json={
                "author": author,
                "commentary": cleaned,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
        if response.status_code != 201:
            raise LinkedInPublishError(self._api_error(response))

        post_urn = response.headers.get("x-restli-id", "").strip()
        if not post_urn:
            raise LinkedInPublishError(
                "LinkedIn accepted the request but did not return a post identifier."
            )
        return LinkedInPublishResult(post_urn=post_urn)

    @staticmethod
    def _api_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            detail = payload.get("message") or payload.get("error_description")
        except (ValueError, AttributeError):
            detail = response.text[:300]
        detail = detail or "No error details were returned."
        return f"LinkedIn API error {response.status_code}: {detail}"
