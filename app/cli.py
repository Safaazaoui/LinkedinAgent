from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta

from app.agent import AgentError, ContentAgent
from app.config import Settings, get_settings
from app.services.linkedin import LinkedInPublishError, LinkedInPublisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="Research, draft, review, and publish positive AI news to LinkedIn.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("run", help="Research news and create reviewed draft files.")

    list_parser = commands.add_parser("list", help="List saved drafts and statuses.")
    list_parser.add_argument("--limit", type=int, default=30)

    show_parser = commands.add_parser("show", help="Print one draft and its metadata.")
    show_parser.add_argument("post_id", type=int)

    review_parser = commands.add_parser(
        "review", help="Run the AI reviewer on an edited outbox draft."
    )
    review_parser.add_argument("post_id", type=int)

    approve_parser = commands.add_parser(
        "approve", help="Approve a draft after a fresh AI review."
    )
    approve_parser.add_argument("post_id", type=int)
    approve_parser.add_argument(
        "--publish",
        action="store_true",
        help="Immediately publish this approved draft to your personal LinkedIn.",
    )

    publish_parser = commands.add_parser(
        "publish", help="Publish a previously approved draft to LinkedIn."
    )
    publish_parser.add_argument("post_id", type=int)

    reject_parser = commands.add_parser("reject", help="Reject a draft.")
    reject_parser.add_argument("post_id", type=int)

    watch_parser = commands.add_parser(
        "watch", help="Keep the agent running and create drafts on an interval."
    )
    watch_parser.add_argument("--interval-hours", type=float, default=24.0)

    commands.add_parser("doctor", help="Check local agent configuration.")
    commands.add_parser(
        "linkedin-whoami",
        help="Read the member ID associated with the configured LinkedIn token.",
    )
    return parser


def _print_run(agent: ContentAgent, settings: Settings) -> None:
    result = agent.run()
    mode = "live OpenAI research" if settings.live_ai_enabled else "demo mode"
    print(f"Agent run complete ({mode}).")
    print(
        f"Stories: {result.stories_found} found, {result.new_stories} new, "
        f"{result.duplicate_stories} already known."
    )
    print(
        f"Drafts: {result.drafts_created} created, "
        f"{result.flagged_drafts} flagged by the AI reviewer."
    )
    for post_id in result.post_ids:
        print(f"  Draft #{post_id}: {agent.outbox_file(post_id)}")
    if not result.post_ids:
        print("No new draft was needed. Existing source URLs are not duplicated.")


def _print_list(agent: ContentAgent, limit: int) -> None:
    posts = agent.list_posts(limit)
    if not posts:
        print("No drafts yet. Run `python -m app run` first.")
        return
    print(f"{'ID':>4}  {'STATUS':<14}  STORY")
    for post in posts:
        title = str(post["story_title"])
        if len(title) > 64:
            title = f"{title[:61]}..."
        print(f"{post['id']:>4}  {post['status']:<14}  {title}")


def _doctor(settings: Settings) -> None:
    print(f"Agent: {settings.app_name}")
    print(f"AI mode: {'live' if settings.live_ai_enabled else 'demo'}")
    print(f"Database: {settings.database_path}")
    print(f"Draft outbox: {settings.outbox_path}")
    print(f"OpenAI key: {'configured' if settings.openai_api_key else 'missing'}")
    print(
        "LinkedIn token: "
        f"{'configured' if settings.linkedin_access_token else 'missing'}"
    )
    print(
        "LinkedIn person URN: "
        f"{'configured' if settings.linkedin_person_urn else 'missing'}"
    )
    print(
        "Publishing: "
        f"{'ready' if settings.linkedin_enabled else 'locked until LinkedIn is configured'}"
    )


def _watch(agent: ContentAgent, settings: Settings, interval_hours: float) -> None:
    if interval_hours <= 0:
        raise AgentError("--interval-hours must be greater than zero.")
    while True:
        _print_run(agent, settings)
        next_run = datetime.now().astimezone() + timedelta(hours=interval_hours)
        print(f"Next research run: {next_run.isoformat(timespec='minutes')}")
        print("Press Ctrl+C to stop. The agent creates drafts but never auto-publishes.")
        time.sleep(interval_hours * 3600)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    agent = ContentAgent(settings)

    try:
        if args.command == "run":
            _print_run(agent, settings)
        elif args.command == "list":
            _print_list(agent, args.limit)
        elif args.command == "show":
            post = agent.get_post(args.post_id)
            print(agent.outbox_file(args.post_id))
            print()
            print(post["draft_text"])
        elif args.command == "review":
            post = agent.review(args.post_id)
            print(f"Draft #{args.post_id}: {post['status']}")
            print(post["review"].get("reviewer_summary", "Review complete."))
        elif args.command == "approve":
            post = agent.approve(args.post_id, publish=args.publish)
            if post["status"] == "published":
                print(
                    f"Draft #{args.post_id} published: {post['linkedin_post_urn']}"
                )
            else:
                print(f"Draft #{args.post_id} approved and ready to publish.")
        elif args.command == "publish":
            post = agent.publish(args.post_id)
            print(f"Draft #{args.post_id} published: {post['linkedin_post_urn']}")
        elif args.command == "reject":
            agent.reject(args.post_id)
            print(f"Draft #{args.post_id} rejected.")
        elif args.command == "watch":
            _watch(agent, settings, args.interval_hours)
        elif args.command == "doctor":
            _doctor(settings)
        elif args.command == "linkedin-whoami":
            profile = LinkedInPublisher(settings).member_profile()
            member_id = profile.get("sub")
            if not member_id:
                raise LinkedInPublishError(
                    "LinkedIn did not return a member ID. Generate a token with "
                    "the openid and profile scopes."
                )
            print(f"Signed in as: {profile.get('name', 'LinkedIn member')}")
            print(f"Set LINKEDIN_PERSON_URN=urn:li:person:{member_id}")
        return 0
    except KeyboardInterrupt:
        print("\nAgent stopped.")
        return 130
    except (AgentError, LinkedInPublishError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
