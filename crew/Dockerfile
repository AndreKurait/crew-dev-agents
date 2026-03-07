FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

FROM python:3.12-slim AS runtime

# Create non-root user
RUN groupadd -r crew && useradd -r -g crew crew

WORKDIR /app

# Copy only what's needed from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src/ src/
COPY config/ config/

# Set ownership and permissions
RUN chown -R crew:crew /app

USER crew

ENTRYPOINT ["python", "-m", "src.main"]
