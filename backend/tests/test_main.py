"""
backend/tests/test_main.py

Testy jednostkowe backendu.
Uruchamianie: cd backend && pytest tests/ -v
"""

import io
import sys
import os
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image

# Ścieżka do modułu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app

client = TestClient(app)


# ── helpers ─────────────────────────────────────────────────────────────────

def make_jpeg(width=100, height=100, color="red") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


def make_png(width=100, height=100) -> bytes:
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


FAKE_AI_RESPONSE = {
    "prediction": "benign",
    "confidence": 0.92,
    "model_used": "resnet50-test",
}


# ── /health ──────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_returns_ok_status(self):
        r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_identifies_as_backend(self):
        r = client.get("/health")
        assert r.json()["service"] == "backend"


# ── /analyze — walidacja wejścia ─────────────────────────────────────────────

class TestAnalyzeValidation:
    def test_rejects_missing_file(self):
        r = client.post("/analyze")
        assert r.status_code == 422

    def test_rejects_text_file(self):
        r = client.post(
            "/analyze",
            files={"file": ("doc.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400

    def test_rejects_json_file(self):
        r = client.post(
            "/analyze",
            files={"file": ("data.json", b'{"x":1}', "application/json")},
        )
        assert r.status_code == 400

    def test_rejects_oversized_file(self):
        big = b"X" * (11 * 1024 * 1024)  # 11 MB
        r = client.post(
            "/analyze",
            files={"file": ("big.jpg", big, "image/jpeg")},
        )
        assert r.status_code == 413

    def test_rejects_corrupt_image(self):
        r = client.post(
            "/analyze",
            files={"file": ("bad.jpg", b"not-an-image-bytes", "image/jpeg")},
        )
        assert r.status_code == 422


# ── /analyze — poprawna ścieżka ───────────────────────────────────────────────

class TestAnalyzeSuccess:
    def _mock_client(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = FAKE_AI_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        return mock_http

    @patch("main.httpx.AsyncClient")
    def test_jpeg_returns_200(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert r.status_code == 200

    @patch("main.httpx.AsyncClient")
    def test_response_has_prediction(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert "prediction" in r.json()

    @patch("main.httpx.AsyncClient")
    def test_response_has_confidence(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert "confidence" in r.json()

    @patch("main.httpx.AsyncClient")
    def test_png_also_accepted(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.png", make_png(), "image/png")},
        )
        assert r.status_code == 200

    @patch("main.httpx.AsyncClient")
    def test_confidence_is_float_between_0_1(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        conf = r.json()["confidence"]
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    @patch("main.httpx.AsyncClient")
    def test_prediction_is_valid_class(self, mock_cls):
        mock_cls.return_value = self._mock_client()
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert r.json()["prediction"] in ("benign", "malignant")


# ── /analyze — błędy serwisu AI ───────────────────────────────────────────────

class TestAnalyzeAIErrors:
    def _mk_throwing(self, exc):
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(side_effect=exc)
        return mock_http

    @patch("main.httpx.AsyncClient")
    def test_503_when_ai_connect_error(self, mock_cls):
        mock_cls.return_value = self._mk_throwing(httpx.ConnectError("refused"))
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert r.status_code == 503

    @patch("main.httpx.AsyncClient")
    def test_504_when_ai_timeout(self, mock_cls):
        mock_cls.return_value = self._mk_throwing(httpx.TimeoutException("timeout"))
        r = client.post(
            "/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
        )
        assert r.status_code == 504
