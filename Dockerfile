FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY src/ src/

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Run with uvicorn — Railway sets PORT
CMD ["sh", "-c", "uvicorn assay.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
