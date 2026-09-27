# NewsAgent AI

NewsAgent AI is a human-in-the-loop Python agent that researches positive AI and technology news, generates professional LinkedIn drafts, and publishes them only after explicit user approval.

## Features

- Researches current positive AI and technology news
- Generates structured LinkedIn content using the OpenAI API
- Reviews drafts for unsupported claims and exaggeration
- Stores generated drafts in a Markdown outbox
- Prevents duplicate sources using SQLite
- Requires explicit approval before publishing
- Publishes approved content through the LinkedIn Posts API
- Includes automated tests and a demo mode

## Tech Stack

- Python
- OpenAI Responses API
- Pydantic
- SQLite
- HTTPX
- LinkedIn Posts API
- Pytest

## Workflow

1. The agent researches recent positive AI news.
2. It selects a relevant story.
3. It generates and reviews a LinkedIn draft.
4. The draft is saved locally for review.
5. The user approves the draft.
6. Only the approved draft can be published to LinkedIn.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate