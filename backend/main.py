"""
backend/main.py

Pośredni serwer FastAPI.
- Odbiera zdjęcie od frontendu
- Przekazuje je do serwisu AI (VM2)
- Zwraca wynik klientowi
"""

import os
import io
import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

app = FastAPI(
    title="DermaScan Backend",
    description="Backend proxy between frontend and AI service",
    version="1.0.0",
)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": "backend"}


@app.get("/ready")
async def ready():
    """Readiness probe — sprawdza połączenie z serwisem AI."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{AI_SERVICE_URL}/health")
            r.raise_for_status()
        return {"status": "ready", "ai_service": "reachable"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")


@app.post("/analyze")
async def analyze(file: UploadFile = File(..., description="Zdjęcie zmiany skórnej")):
    """
    Analizuje przesłane zdjęcie przy użyciu modelu AI.
    Zwraca: prediction, confidence, model_used.
    """
    # --- walidacja content-type ---
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Plik musi być obrazem (otrzymano: {file.content_type})",
        )

    contents = await file.read()

    # --- walidacja rozmiaru ---
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Plik przekracza dozwolony rozmiar 10 MB",
        )

    # --- walidacja że to naprawdę obraz ---
    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
    except Exception:
        raise HTTPException(status_code=422, detail="Nie można otworzyć pliku jako obraz")

    # --- przekazanie do serwisu AI ---
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/predict",
                files={"file": (file.filename, contents, file.content_type)},
            )
            response.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Serwis AI jest niedostępny — spróbuj ponownie",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Serwis AI nie odpowiedział w czasie",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Błąd serwisu AI: {exc.response.status_code}",
        )

    return response.json()
