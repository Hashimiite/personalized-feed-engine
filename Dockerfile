FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/.models

WORKDIR /app

# Dependencies first so code changes don't invalidate this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time so containers start without network access to it
COPY embeddings.py .
RUN python -c "from embeddings import FastEmbedEmbeddings; FastEmbedEmbeddings()"

COPY . .

RUN useradd --create-home appuser && chown -R appuser /app/.models
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
