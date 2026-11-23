FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Copy uv binary directly from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependencies configuration & package info
COPY pyproject.toml README.md ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source code
COPY src ./src

EXPOSE 8000

# Railway dynamically injects $PORT at runtime
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
