FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY web ./web

ENV PYTHONPATH=/app/src
ENV PORT=8080

# Cloud Run provides $PORT; shell form lets it expand. exec keeps uvicorn as PID 1.
CMD exec python -m uvicorn web.app:app --host 0.0.0.0 --port ${PORT}
