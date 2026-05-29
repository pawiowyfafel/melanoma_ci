# ai-service/Dockerfile
# UWAGA: model_gita.pth (90 MB) musi znajdować się w tym katalogu przed budowaniem.
# Katalog src/ z model.py też musi tu być.

FROM python:3.11-slim

WORKDIR /app

# System deps dla OpenCV / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod źródłowy
COPY api.py .
COPY src/ ./src/

# Model — 90 MB; przy CI/CD warto go montować jako wolumen lub pobierać z S3
COPY model_gita.pth .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
