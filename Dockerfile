FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2 and WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy everything needed for install
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
COPY reports/ reports/

# Install as a proper package (not editable)
RUN uv pip install --system .

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Run with uvicorn — Railway sets PORT
CMD ["sh", "-c", "uvicorn assay.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
