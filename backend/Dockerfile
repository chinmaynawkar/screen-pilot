FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the backend package (imports expect `backend.app...`).
COPY backend /app/backend

ENV PORT=8000
EXPOSE 8000

CMD ["bash", "-lc", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]

