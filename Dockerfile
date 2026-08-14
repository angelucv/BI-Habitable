# BI Habitable (PDNA) — imagen para Render
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2
ENV BI_ENV=production
EXPOSE 10000

CMD streamlit run app.py \
    --server.port=${PORT:-10000} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.maxUploadSize=80 \
    --browser.gatherUsageStats=false
