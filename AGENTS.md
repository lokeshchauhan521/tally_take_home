# AGENTS.md

## Project purpose

This repository implements a FastAPI service that ingests Tally XML exports, preserves parent-child ownership and repeated list ordering, and exposes normalized vouchers and import metadata.

## FastAPI architecture

- `app/main.py`: app bootstrap
- `app/api/routes/`: HTTP routes
- `app/core/`: settings, security, logging
- `app/models/`: SQLAlchemy models
- `app/schemas/`: Pydantic request/response schemas
- `app/services/`: XML parsing and normalization logic
- `app/repositories/`: DB access and transaction logic
- `app/db/`: database engine and Alembic migrations
- `app/utils/`: XML sanitization, hashing, utility helpers

## Development commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing commands

```bash
pytest -q
```

## Database commands

```bash
alembic upgrade head
alembic revision --autogenerate -m "message"
```

## API conventions

- Use FastAPI route handlers for thin orchestration.
- Put business logic in services and repositories.
- Use Pydantic schemas for request/response validation.
- Return structured JSON errors; do not expose stack traces or raw XML.
- Use meaningful status codes: `200`, `201`, `400`, `404`, `422`, `413`, `500`.

## Coding conventions

- Prefer clear, narrow functions and explicit models.
- Keep source text and money values as strings when lossless conversion is required.
- Never flatten repeated XML arrays without preserving order/ownership.
- Keep DB access separated from API route logic.
- Use environment variables for configuration; do not hard-code secrets.

## Security rules

- Reject or disable DTD/external entity processing.
- Enforce upload-size limits.
- Never log raw accounting XML.
- Validate and sanitize file inputs.
- Do not expose local file paths or stack traces to clients.

## Environment variables

Use `.env` locally. Keep only non-secret configuration there.

```env
APP_NAME=Tally XML Ingestion API
APP_ENV=development
UPLOAD_MAX_SIZE_MB=10
DATABASE_URL=sqlite:///./tally.db
```

## Avoid unnecessary repository exploration

- Start from the assignment docs and fixtures.
- Read only the files directly relevant to the requested change.
- Prefer targeted tests and a small set of route/service files over whole-repo reads.
