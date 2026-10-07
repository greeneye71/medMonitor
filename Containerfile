FROM docker.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Rome \
    DATA_DIR=/data \
    Z2M_CONFIG=/z2m/configuration.yaml \
    UI_PORT=8090

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

VOLUME ["/data"]
CMD exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${UI_PORT}" --proxy-headers
