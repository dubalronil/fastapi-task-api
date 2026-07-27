FROM python:3.11-slim

# PYTHONUNBUFFERED matters in a container: without it Python buffers stdout and
# log lines appear late or not at all in `docker logs` and in hosted log viewers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Dependencies before application code. Docker caches each layer and rebuilds
# from the first one that changed, so editing a router does not reinstall
# everything. requirements.txt is runtime only — no pytest, no ruff.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# alembic.ini and alembic/ are needed at runtime, not just at build time, so
# that `alembic upgrade head` can run against the deployed database.
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

# Run as an unprivileged user. If the process is ever compromised it should not
# already own the filesystem it is standing on.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000

# --host 0.0.0.0, not the default 127.0.0.1: inside a container, loopback is
# only reachable from that same container, so a published port would hit nothing.
#
# PORT is read from the environment because hosts such as Railway assign one.
# `exec` replaces the shell with uvicorn so it becomes PID 1 and receives the
# SIGTERM sent at shutdown; without it the shell would swallow the signal and
# the container would be killed rather than closing connections cleanly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
