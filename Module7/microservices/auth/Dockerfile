# syntax=docker/dockerfile:1

# ---- builder: install dependencies into a venv, with a cached pip download dir ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ---- runtime: copy only the built venv + source, no pip cache or build layer ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT}"]
