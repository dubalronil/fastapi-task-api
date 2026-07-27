# Task API

[![CI](https://github.com/dubalronil/fastapi-task-api/actions/workflows/ci.yml/badge.svg)](https://github.com/dubalronil/fastapi-task-api/actions/workflows/ci.yml)

A production-style REST API for managing tasks built with FastAPI and PostgreSQL.

**Live API:** https://fastapi-task-api-production.up.railway.app —
[interactive docs](https://fastapi-task-api-production.up.railway.app/docs)

**Live demo:** https://task-api-frontend-ten.vercel.app —
a small Next.js frontend consuming this API
([repo](https://github.com/dubalronil/task-api-frontend))

This project focuses on backend engineering fundamentals rather than application complexity. It demonstrates API design, validation, database migrations, testing, logging, and deployment practices using a simple task management domain.

## Features

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic migrations
- Request validation with Pydantic
- Structured logging
- Consistent error responses
- API key on write endpoints
- PostgreSQL integration tests
- Docker image and Compose stack
- GitHub Actions CI
- Deployed on Railway, with a Next.js frontend consuming it

## Architecture

```
Client
  │
  │  HTTP request with JSON
  ▼
main.py            creates the app and mounts the routers
  │
  ▼
routers/tasks.py   matches the URL to a Python function
  │
  ▼
schemas.py         checks the incoming JSON   ──►  422, request stops here
  │
  ▼
models.py          describes the tasks table
database.py        opens a session, closes it when the request ends
  │
  ▼
Postgres
  │
  ▼
schemas.py         decides which fields go back to the client
  │
  ▼
Client
```

`config.py` sits outside this flow. It reads `.env` at startup and tells
`database.py` which database to connect to.

Each file has one job. `main.py` builds the app and plugs in the routers. The
router picks the function for a URL like `GET /tasks/3`. Before that function
runs, `schemas.py` checks the incoming JSON — an empty title or a negative id
is rejected with a 422 and the function is never called, which is why the
endpoint code has no `if not title` checks in it. Then `models.py` describes
the `tasks` table, `database.py` provides a session and closes it afterwards,
and on the way out `schemas.py` decides which fields the client sees.

`models.py` and `schemas.py` look like duplicates but answer different
questions. `models.py` is shaped by what the database can store, `schemas.py`
by what we accept from a stranger and what we send back. Keeping them separate
means the API's rules can change without touching the database.

### Where Alembic fits

Alembic isn't part of handling a request. It runs only when the database
structure changes.

Many projects use `Base.metadata.create_all()`, which builds missing tables at
startup. It fails quietly: it checks whether a _table_ exists, never whether
its columns match your models. Add a column, restart, and an existing database
is untouched — the app boots fine and 500s on the first request that needs it.

Alembic uses small numbered scripts instead. Each describes one change, the
database records which have run, and `alembic upgrade head` applies the rest.
Existing data survives, and every schema change is written down and reviewable.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d          # starts Postgres
```

`.env` is optional — the defaults already match `docker-compose.yml`. Copy
`.env.example` to `.env` if you want to change anything.

## Run

```bash
alembic upgrade head       # build or update the database
uvicorn app.main:app --reload
```

Docs at http://127.0.0.1:8000/docs

## Test

```bash
pytest
```

Tests run against Postgres, on the same container, in their own databases
(`tasks_test` and `tasks_migrations`) which are created automatically. Running
them on the engine we deploy to means engine-specific bugs surface here rather
than in production.

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

## Errors

Every failure returns the same shape, so a client needs one code path rather
than one per kind of error.

```json
{
  "status": 404,
  "title": "Not Found",
  "detail": "Task not found",
  "request_id": "d4e2d4359c7a"
}
```

Validation failures add an `errors` list naming the fields:

```json
{
  "status": 422,
  "title": "Unprocessable Entity",
  "detail": "Request validation failed",
  "request_id": "d4e2d4359c7a",
  "errors": [
    {
      "field": "body.title",
      "message": "String should have at least 1 character"
    }
  ]
}
```

Unexpected errors return a plain `500` and nothing about our internals. The
real exception goes to the log instead, under the same `request_id`.

## CORS

Configured but unused, deliberately. Browsers block cross-origin calls unless
the API approves them, so an origin calling from a browser has to be listed:

```bash
CORS_ORIGINS=http://localhost:3000
```

The frontend never needs this. It calls its own server route, which forwards to
this API — a server-to-server request, which no browser is involved in and CORS
does not apply to. The deployed frontend's origin is not in `CORS_ORIGINS` and
the app works anyway.

It stays for anything that does call the API from a browser, since the read
endpoints are public. `X-Request-ID` is in `expose_headers` so page scripts can
read it; a browser hides response headers the server does not explicitly expose.

CORS is enforced by the browser, not the server: `curl` and other non-browser
clients ignore it entirely.

## Write protection

Reads are public so the API can be browsed and demonstrated. Anything that
changes data needs an `X-API-Key` header matching `API_KEY`:

```bash
curl -X POST .../tasks -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"title":"..."}'
```

Leaving `API_KEY` unset leaves writes open, which suits local development; the
app logs a warning at startup when that happens. Keys are compared with
`secrets.compare_digest`, so the time taken does not depend on how much of the
key matched.

This is a gate, not authentication — there are no users, and anyone holding the
key can write.

**The key belongs on a server, never in browser code.** Anything a browser
sends is visible to whoever is using that browser. A frontend should call its
own server route, which holds the key and forwards the request.

## Logging

Every request gets an id, returned in the `X-Request-ID` header and included
in error responses. The same id is on every log line for that request, so a
user quoting it is enough to find what happened. An incoming `X-Request-ID` is
reused rather than replaced, so the id survives across services.

```
14:45:24 INFO  [265044088f5d] app.access: request method=POST path=/tasks status=201 duration_ms=9.5
```

`LOG_JSON=true` switches to one JSON object per line for production:

```json
{
  "time": "...",
  "level": "INFO",
  "logger": "app.access",
  "message": "request",
  "request_id": "d4e2d4359c7a",
  "method": "POST",
  "path": "/tasks",
  "status": 201,
  "duration_ms": 8.9
}
```

## Layout

```
app/
  main.py             app setup
  config.py           settings from .env
  database.py         engine and session
  models.py           database tables
  schemas.py          request and response shapes
  errors.py           one error shape for the whole API
  security.py         API key check for write endpoints
  logging_config.py   log format and the request-id context
  middleware.py       request ids and the access log
  routers/            endpoints
alembic/
  versions/           migration scripts
tests/
.github/workflows/    CI: lint, format, tests, image build
Dockerfile            production image, app only
docker-compose.yml    local stack: Postgres, plus the app behind a profile
railway.json          deployment configuration
```

## Migrations

Alembic owns the schema, so the app never creates tables on startup.

```bash
alembic upgrade head                          # apply pending migrations
alembic revision --autogenerate -m "message"  # draft one from a model change
alembic downgrade -1                          # undo the last one
alembic current                               # what version this database is on
```

Always read what `--autogenerate` writes. It compares the schema, not the
rows, so anything involving existing data (backfills, defaults) has to be
added by hand. It also cannot see an unbounded `VARCHAR` becoming
`VARCHAR(n)`, so column length changes need writing manually too.

## Docker

Two ways to run it. By default only Postgres is containerised and the app runs
on the host, which keeps `--reload` working. The `app` profile runs everything
in containers, which is what the deployed image does.

```bash
docker compose up -d                 # Postgres only
docker compose --profile app up -d   # Postgres + the app on :8000

docker compose down                  # stop, keeping the data
docker compose down -v               # stop and delete the data
docker compose logs -f app           # follow the app logs
docker compose exec db psql -U tasks -d tasks
```

The image runs as a non-root user and contains only runtime dependencies —
no tests, no `pytest`, no `ruff`. In Compose, `alembic upgrade head` runs in the
app's start command, which is fine for one instance. With several replicas each
would race to migrate on boot, which is why the deployed setup runs migrations
as a separate step instead — see below.

## Deployment

Deployed on Railway from this repository. Pushing to `main` triggers a build.

`railway.json` holds the configuration:

```json
{
  "build": { "builder": "DOCKERFILE" },
  "deploy": {
    "preDeployCommand": ["alembic upgrade head"],
    "healthcheckPath": "/"
  }
}
```

`preDeployCommand` runs migrations once per deploy, in its own container,
before any app instance starts — so replicas never race to migrate. The
healthcheck hits `/`, which queries the database, so an instance that cannot
reach Postgres is never sent traffic.

Environment variables on the service:

| Variable       | Value                                     |
| -------------- | ----------------------------------------- |
| `DATABASE_URL` | reference to the Postgres service         |
| `LOG_JSON`     | `true`                                    |
| `API_KEY`      | a long random string, required for writes |

`CORS_ORIGINS` is not set in production: the frontend calls the API from its
own server, so no browser ever makes a cross-origin request.

`PORT` is injected by Railway and read by the container's start command.
`DATABASE_URL` is stored as a reference rather than a copied string, so it
stays correct if the database is ever replaced.

Hosting providers hand out `postgresql://` URLs, which SQLAlchemy maps to
psycopg2 — a driver this project does not install. `config.py` normalises them
to `postgresql+psycopg://`, so `DATABASE_URL` can be used exactly as given.

## Notes

- No auth yet, every endpoint is public.
