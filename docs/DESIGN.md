# Design decisions

Why the project is built this way; the [README](../README.md) covers what it
does. Most came from something breaking first, so the error is included.

## 1. One schema per operation, not one per table

`TaskCreate`, `TaskReplace`, `TaskUpdate` and `TaskResponse`, where one `Task`
schema was used before. That version lost data silently: `PUT` with a partial
body nulled the fields the client had not sent. A schema describing a table
cannot describe the difference between create, replace and modify. The three
inputs share their rules through the `Title` and `Description` annotations, and
differ only in what is required, optional or nullable.

## 2. Alembic owns the schema, not `create_all()`

`create_all()` checks whether a *table* exists and stops — it never compares
columns. Adding `created_at` changed nothing about the existing database:

```
app startup: OK, no errors
GET /tasks -> OperationalError: no such column: tasks.created_at
```

Tests stayed green, because the test database is rebuilt from the models every
run and can never be stale. No test of that shape catches this.

## 3. Autogenerate writes a draft, not a migration

It compares the schema; it cannot see the rows. Making `completed` NOT NULL
produced a migration that failed on one hand-inserted `NULL` row, and only a
human knows the backfill is needed — written `= FALSE` not `= 0`, since `0`
works on SQLite and fails on Postgres. It is also blind to `VARCHAR` becoming
`VARCHAR(200)`, so those `alter_column` calls are hand-written. `alembic check`
passing is a signal, not a guarantee.

## 4. Postgres, and the tests run on it

SQLite hid real behaviour: no date type, so timestamps came back with nothing
saying they were UTC; negative `OFFSET` ignored; advisory typing. Moving the
tests mattered more than moving the app — reverting the `FALSE`/`0` fix proves
it, and a bug that needed a human reviewer is now caught in under a second:

```
DatatypeMismatch: column "completed" is boolean but expression is integer
```

Cost: `pytest` now requires a running Postgres.

## 5. Tests roll back instead of rebuilding

Schema built once per session, each test wrapped in a transaction and rolled
back. Endpoints call `db.commit()`, which a naive rollback cannot undo;
`join_transaction_mode="create_savepoint"` makes the session join the open
transaction through a SAVEPOINT, so `commit()` releases that savepoint and the
outer rollback still wins. Cost: sequences are not transactional, so ids are
consumed even for discarded rows — any test asserting `id == 1` is a bug.

## 6. One error shape for every failure

One envelope, modelled on RFC 9457, replacing three different shapes:

```json
{ "status": 404, "title": "Not Found", "detail": "Task not found", "request_id": "d4e2d4359c7a" }
```

Registered on Starlette's `HTTPException` rather than FastAPI's, so an unmatched
URL or wrong method looks the same. Unhandled exceptions get a generic `500`,
since stack traces disclose paths, versions and sometimes connection strings. A
test plants a secret in an exception and asserts the client never sees it *and*
that the log does — checking only the first passes if the error is swallowed.

## 7. Writes need a key; reads do not

Writes require `X-API-Key`; `GET` stays open so the API stays browsable. This is
a gate, not authentication — there are no users. Keys are compared with
`secrets.compare_digest`, because `==` returns as soon as characters differ and
leaks the key a character at a time; both sides are encoded to bytes first,
since headers arrive as latin-1 and `compare_digest` raises `TypeError` on
non-ASCII, turning a wrong key into a 500. A test asserts no write method in the
OpenAPI schema lacks a security requirement — a `PATCH` once shipped without.

## 8. The key never reaches browser code

The browser calls a server route on the frontend, which holds the key and
forwards the request. Anything a browser sends is visible in its network tab, so
a key in client-side JavaScript is a slightly inconvenient public string, not a
secret. It also removes the cross-origin request, so CORS stops applying.

## Absent, and known limits

No auth, Redis, background workers, caching, service layer or repository pattern
— each defensible in a larger system, none justified here. What that leaves:

- **No authentication.** Tasks have no owner, so everyone shares one list.
- **CORS headers are missing on unhandled 500s.** Starlette handles those
  outside every user middleware, so nothing can wrap it.
- **`alembic check` cannot see column length changes.** See decision 3.
- **Reads are unrated.** Rate limiting was built and removed once the key made
  it redundant; the remaining risk is a read flood on an unadvertised URL.
