# Task API

[![CI](https://github.com/dubalronil/fastapi-task-api/actions/workflows/ci.yml/badge.svg)](https://github.com/dubalronil/fastapi-task-api/actions/workflows/ci.yml)

A production-style REST API for managing tasks — FastAPI, PostgreSQL, Alembic
migrations, Pydantic validation, structured logging, Docker and CI. The domain
is deliberately simple so the engineering is the visible part.

**Live API:** https://fastapi-task-api-production.up.railway.app —
[interactive docs](https://fastapi-task-api-production.up.railway.app/docs)

**Live demo:** https://task-api-frontend-ten.vercel.app — a Next.js frontend
consuming this API ([repo](https://github.com/dubalronil/task-api-frontend))

[**Design decisions**](docs/DESIGN.md) — why it is built this way, and what each
choice cost.

[**Learnings**](docs/LEARNINGS.md) — understanding of how this project works and the engineering concepts behind it

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d       # starts Postgres
alembic upgrade head       # build or update the database
uvicorn app.main:app --reload
pytest
```

Docs at http://127.0.0.1:8000/docs. `.env` is optional — the defaults match
`docker-compose.yml`. Only Postgres is containerised, so `--reload` keeps
working; `docker compose --profile app up -d` runs the full stack, which is what
deploys. Tests use their own auto-created databases on the same container, so
engine-specific bugs surface here rather than in production.

## Endpoints

| Method   | Path          | Description                                         |
| -------- | ------------- | --------------------------------------------------- |
| `GET`    | `/`           | Health check (`503` if the database is unreachable) |
| `GET`    | `/tasks`      | List tasks (`completed`, `skip`, `limit`)           |
| `POST`   | `/tasks`      | Create a task                                       |
| `GET`    | `/tasks/{id}` | Get one task                                        |
| `PUT`    | `/tasks/{id}` | Replace a task, all fields required                 |
| `PATCH`  | `/tasks/{id}` | Update some fields, the rest are left alone         |
| `DELETE` | `/tasks/{id}` | Delete a task (`204`, no body)                      |

Reads are public. Writes need an `X-API-Key` header matching `API_KEY`; unset,
writes stay open for local development and the app warns at startup. It is a
gate, not authentication — the key belongs on a server, never in browser code.

## Errors and logging

Every failure returns the same shape, so a client needs one code path:

```json
{
  "status": 404,
  "title": "Not Found",
  "detail": "Task not found",
  "request_id": "d4e2d4359c7a"
}
```

Validation failures add an `errors` list naming the fields. Unexpected errors
return a plain `500` and nothing about our internals; the real exception goes to
the log under the same `request_id`.

That id is returned in `X-Request-ID` and sits on every log line for the
request, so a user quoting it is enough to find what happened. An incoming id is
reused rather than replaced. `LOG_JSON=true` gives one JSON object per line.

## Layout

```
Client → routers/tasks.py → schemas.py (422 stops here) → models.py,
database.py → Postgres → schemas.py → Client

app/       main, config, database, models, schemas, errors, security,
           logging_config, middleware, routers/
alembic/   versions/ — migration scripts
tests/     docs/, .github/workflows/, Dockerfile, railway.json
```

Validation runs before the endpoint, which is why no endpoint contains an
`if not title` check. `models.py` and `schemas.py` look like duplicates but ask
different questions: what the database can store, versus what we accept from a
stranger and send back.

## Migrations

```bash
alembic upgrade head                          # apply pending migrations
alembic revision --autogenerate -m "message"  # draft one from a model change
alembic downgrade -1                          # undo the last one
```

Always read what `--autogenerate` writes: it compares the schema, not the rows,
so backfills are added by hand, and it cannot see a `VARCHAR` gain a length.

## Deployment

Railway, from this repository; pushing to `main` triggers a build. `railway.json`
runs `alembic upgrade head` as a `preDeployCommand` — once per deploy, in its own
container, so replicas never race to migrate — and healthchecks `/`, which queries
the database. Set `DATABASE_URL` (a service reference), `LOG_JSON=true` and
`API_KEY`; `config.py` rewrites the provider's URL to `postgresql+psycopg://`.
