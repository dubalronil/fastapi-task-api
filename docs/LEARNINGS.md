# Learning Notes

This document explains my understanding of how this project works and the engineering concepts behind it.

While Claude Code generated much of the implementation, I used this project to learn how a production-style backend is structured. I studied the codebase, architecture, and design decisions to understand why each component exists and how they work together.

---

## Project Overview

This project is a production-style REST API built with FastAPI and PostgreSQL.

Although the application itself is a simple task manager, the primary goal was to learn backend engineering rather than build a complex product. Through this project I learned how HTTP requests flow through an API, how data is validated, stored, tested, logged, containerized, and deployed.

---

## Request Lifecycle

A typical request follows this flow:

```
Client
    ↓
FastAPI
    ↓
Middleware
    ↓
Pydantic Validation
    ↓
Router
    ↓
SQLAlchemy
    ↓
PostgreSQL
    ↓
Response
```

1. A client sends an HTTP request.
2. Middleware generates a request ID and begins request logging.
3. Pydantic validates the incoming data.
4. The router performs the requested database operation.
5. SQLAlchemy communicates with PostgreSQL.
6. The response is validated and returned to the client.

---

## Main Components

### `main.py`

Creates the FastAPI application and registers middleware, routers, logging, and error handlers.

### `routers/tasks.py`

Implements the CRUD endpoints for managing tasks.

### `schemas.py`

Defines request and response models using Pydantic and validates incoming data.

### `models.py`

Maps Python classes to PostgreSQL tables using SQLAlchemy.

### `database.py`

Creates the database engine and manages database sessions.

### `middleware.py`

Adds request IDs and logs information about every request.

### `errors.py`

Provides a consistent error response format across the API.

### `config.py`

Loads configuration from environment variables.

---

## Database

SQLAlchemy acts as the bridge between Python and PostgreSQL.

Instead of writing SQL manually for every operation, SQLAlchemy converts Python objects into SQL statements.

Database schema changes are managed using Alembic migrations, allowing the schema to evolve without recreating the database.

---

## Testing

The test suite runs against PostgreSQL instead of SQLite so the development environment closely matches production.

Each test runs inside a transaction that is rolled back afterward, allowing tests to remain isolated while keeping the suite fast.

---

## Deployment

Docker packages the application into a portable container.

Railway deploys the container and executes Alembic migrations before starting the application, ensuring the database schema is up to date.

---

## Biggest Lessons

This project taught me that backend engineering is much more than implementing CRUD endpoints.

A production-ready backend also requires:

- Input validation
- Database migrations
- Logging
- Error handling
- Testing
- Configuration management
- Docker
- CI/CD
- Cloud deployment

Even a simple application can demonstrate many real-world software engineering practices.

---

## Reflection

Claude Code generated much of the implementation, but I used this project as a way to understand how modern backend systems are designed.

I spent time reading the code, following the request flow, understanding the database interactions, and studying the reasoning behind design decisions such as multiple request schemas, Alembic migrations, structured logging, request IDs, and consistent error handling.

The goal was to build a working API and to understand the engineering principles that make production software reliable and maintainable.
