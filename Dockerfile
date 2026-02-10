FROM python:3.11-slim-bookworm

COPY pyproject.toml README.md /app/
WORKDIR /app

RUN pip install --no-cache-dir .[dev]

COPY src/ /src/
COPY tests/ /tests/

ENV PYTHONPATH=/src
WORKDIR /src
