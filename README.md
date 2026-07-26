# Task API

A simple REST API for managing tasks, built with FastAPI, SQLAlchemy and SQLite.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Run

```bash
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
tests/
examples/
```

## Notes

- No migrations yet, so changing a model means deleting the SQLite file. Alembic is next.
- No auth yet, every endpoint is public.
