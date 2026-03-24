FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend code + backend (shared models/paths imported by frontend)
COPY frontend/ frontend/
COPY backend/ backend/

ENV PYTHONPATH=/app

EXPOSE 8050

CMD ["python", "frontend/app.py"]
