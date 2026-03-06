FROM python:3.12-slim AS base

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY src/ src/
COPY config/ config/

ENTRYPOINT ["python", "-m", "src.main"]
