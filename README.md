# Task API

A simple REST API for managing tasks, built with FastAPI, SQLAlchemy and SQLite.

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
SQLite (tasks.db)
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
startup. It fails quietly: it checks whether a *table* exists, never whether
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
cp .env.example .env
```

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

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `GET` | `/tasks` | List tasks (`completed`, `skip`, `limit`) |
| `POST` | `/tasks` | Create a task |
| `GET` | `/tasks/{id}` | Get one task |
| `PUT` | `/tasks/{id}` | Replace a task, all fields required |
| `PATCH` | `/tasks/{id}` | Update some fields, the rest are left alone |
| `DELETE` | `/tasks/{id}` | Delete a task |

## Layout

```
app/
  main.py       app setup
  config.py     settings from .env
  database.py   engine and session
  models.py     database tables
  schemas.py    request and response shapes
  routers/      endpoints
alembic/
  versions/     migration scripts
tests/
examples/
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
added by hand.

## Notes

- No auth yet, every endpoint is public.
