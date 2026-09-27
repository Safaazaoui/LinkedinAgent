from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    why_positive TEXT NOT NULL,
                    student_angle TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    primary_source_url TEXT NOT NULL UNIQUE,
                    additional_source_urls TEXT NOT NULL DEFAULT '[]',
                    credibility_score INTEGER NOT NULL,
                    positivity_score INTEGER NOT NULL,
                    student_relevance_score INTEGER NOT NULL,
                    confidence_score INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER NOT NULL UNIQUE,
                    draft_text TEXT NOT NULL,
                    review_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'needs_review',
                    linkedin_post_urn TEXT,
                    published_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_stories_created_at
                    ON stories(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_posts_status
                    ON posts(status);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(posts)").fetchall()
            }
            if "linkedin_post_urn" not in columns:
                connection.execute(
                    "ALTER TABLE posts ADD COLUMN linkedin_post_urn TEXT"
                )
            if "published_at" not in columns:
                connection.execute("ALTER TABLE posts ADD COLUMN published_at TEXT")

    @staticmethod
    def _story(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        story = dict(row)
        story["additional_source_urls"] = json.loads(
            story.get("additional_source_urls") or "[]"
        )
        return story

    @staticmethod
    def _post(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        post = dict(row)
        post["review"] = json.loads(post.pop("review_json") or "{}")
        return post

    def add_story(self, candidate: dict[str, Any]) -> tuple[int, bool]:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM stories WHERE primary_source_url = ?",
                (candidate["primary_source_url"],),
            ).fetchone()
            if existing:
                return int(existing["id"]), False

            cursor = connection.execute(
                """
                INSERT INTO stories (
                    title, summary, why_positive, student_angle, published_at,
                    primary_source_url, additional_source_urls,
                    credibility_score, positivity_score,
                    student_relevance_score, confidence_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate["title"],
                    candidate["summary"],
                    candidate["why_positive"],
                    candidate["student_angle"],
                    candidate["published_at"],
                    candidate["primary_source_url"],
                    json.dumps(candidate.get("additional_source_urls", [])),
                    candidate["credibility_score"],
                    candidate["positivity_score"],
                    candidate["student_relevance_score"],
                    candidate["confidence_score"],
                    utc_now(),
                ),
            )
            return int(cursor.lastrowid), True

    def list_stories(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM stories
                ORDER BY published_at DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._story(row) for row in rows if row is not None]

    def get_story(self, story_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM stories WHERE id = ?", (story_id,)
            ).fetchone()
        return self._story(row)

    def set_story_status(self, story_id: int, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE stories SET status = ? WHERE id = ?", (status, story_id)
            )

    def upsert_post(
        self,
        story_id: int,
        draft_text: str,
        review: dict[str, Any],
        status: str = "needs_review",
    ) -> int:
        now = utc_now()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM posts WHERE story_id = ?", (story_id,)
            ).fetchone()
            if existing:
                post_id = int(existing["id"])
                connection.execute(
                    """
                    UPDATE posts
                    SET draft_text = ?, review_json = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (draft_text, json.dumps(review), status, now, post_id),
                )
                return post_id

            cursor = connection.execute(
                """
                INSERT INTO posts (
                    story_id, draft_text, review_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (story_id, draft_text, json.dumps(review), status, now, now),
            )
            return int(cursor.lastrowid)

    def list_posts(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    posts.*,
                    stories.title AS story_title,
                    stories.primary_source_url AS source_url
                FROM posts
                JOIN stories ON stories.id = posts.story_id
                ORDER BY posts.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._post(row) for row in rows if row is not None]

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    posts.*,
                    stories.title AS story_title,
                    stories.summary AS story_summary,
                    stories.why_positive AS why_positive,
                    stories.student_angle AS student_angle,
                    stories.primary_source_url AS source_url,
                    stories.published_at AS story_published_at
                FROM posts
                JOIN stories ON stories.id = posts.story_id
                WHERE posts.id = ?
                """,
                (post_id,),
            ).fetchone()
        return self._post(row)

    def get_post_by_story(self, story_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM posts WHERE story_id = ?", (story_id,)
            ).fetchone()
        return self._post(row)

    def update_post(self, post_id: int, draft_text: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE posts
                SET draft_text = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (draft_text, status, utc_now(), post_id),
            )

    def update_review(
        self, post_id: int, draft_text: str, review: dict[str, Any], status: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE posts
                SET draft_text = ?, review_json = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (draft_text, json.dumps(review), status, utc_now(), post_id),
            )

    def mark_published(self, post_id: int, linkedin_post_urn: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE posts
                SET status = 'published', linkedin_post_urn = ?,
                    published_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (linkedin_post_urn, utc_now(), utc_now(), post_id),
            )

    def stats(self) -> dict[str, int]:
        with self.connect() as connection:
            stories = connection.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
            drafts = connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            approved = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE status = 'approved'"
            ).fetchone()[0]
            published = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE status = 'published'"
            ).fetchone()[0]
        return {
            "stories": stories,
            "drafts": drafts,
            "approved": approved,
            "published": published,
        }
