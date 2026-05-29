"""
tests/e2e/test_e2e.py

Testy end-to-end — wymagają działającego środowiska (VM3 lub docker-compose).

Zmienne środowiskowe:
  FRONTEND_URL  — np. http://192.168.56.30        (domyślnie: http://localhost)
  BACKEND_URL   — np. http://192.168.56.30:8080   (domyślnie: http://localhost:8080)

Uruchamianie:
  pip install pytest requests pillow
  FRONTEND_URL=http://192.168.56.30 BACKEND_URL=http://192.168.56.30:8080 pytest tests/e2e/ -v
"""

import io
import os
import time
import pytest
import requests
from PIL import Image

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost").rstrip("/")
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8080").rstrip("/")
TIMEOUT      = 15  # s

# ── helpers ──────────────────────────────────────────────────────────────────

def make_jpeg(color=(180, 120, 100), size=(224, 224)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.read()


def wait_for_service(url: str, retries: int = 10, delay: float = 3.0):
    for i in range(retries):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(delay)
    return False


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def services_ready():
    assert wait_for_service(f"{BACKEND_URL}/health"), \
        f"Backend nie odpowiada pod {BACKEND_URL}/health"


# ── Frontend ─────────────────────────────────────────────────────────────────

class TestFrontend:
    def test_frontend_returns_200(self):
        r = requests.get(FRONTEND_URL, timeout=TIMEOUT)
        assert r.status_code == 200

    def test_frontend_returns_html(self):
        r = requests.get(FRONTEND_URL, timeout=TIMEOUT)
        assert "text/html" in r.headers.get("Content-Type", "")

    def test_frontend_contains_app_title(self):
        r = requests.get(FRONTEND_URL, timeout=TIMEOUT)
        assert "DermaScan" in r.text

    def test_frontend_contains_form(self):
        r = requests.get(FRONTEND_URL, timeout=TIMEOUT)
        assert "upload-form" in r.text

    def test_css_is_served(self):
        r = requests.get(f"{FRONTEND_URL}/style.css", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "text/css" in r.headers.get("Content-Type", "")


# ── Backend health ────────────────────────────────────────────────────────────

class TestBackendHealth:
    def test_health_endpoint_ok(self):
        r = requests.get(f"{BACKEND_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_health_returns_json(self):
        r = requests.get(f"{BACKEND_URL}/health", timeout=TIMEOUT)
        data = r.json()
        assert data["status"] == "ok"


# ── Pełny przepływ predykcji ──────────────────────────────────────────────────

class TestPredictionFlow:
    def _post_image(self, img_bytes: bytes, filename="skin.jpg", content_type="image/jpeg"):
        return requests.post(
            f"{BACKEND_URL}/analyze",
            files={"file": (filename, img_bytes, content_type)},
            timeout=TIMEOUT,
        )

    def test_jpeg_returns_200(self):
        r = self._post_image(make_jpeg())
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        r = self._post_image(make_jpeg())
        data = r.json()
        assert "prediction"  in data
        assert "confidence"  in data
        assert "model_used"  in data

    def test_prediction_is_valid_class(self):
        r = self._post_image(make_jpeg())
        assert r.json()["prediction"] in ("benign", "malignant")

    def test_confidence_in_range(self):
        r = self._post_image(make_jpeg())
        conf = r.json()["confidence"]
        assert 0.0 <= conf <= 1.0, f"confidence poza zakresem: {conf}"

    def test_non_image_rejected(self):
        r = requests.post(
            f"{BACKEND_URL}/analyze",
            files={"file": ("data.txt", b"hello world", "text/plain")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    def test_missing_file_returns_422(self):
        r = requests.post(f"{BACKEND_URL}/analyze", timeout=TIMEOUT)
        assert r.status_code == 422

    def test_oversized_file_returns_413(self):
        big = b"X" * (11 * 1024 * 1024)
        r = requests.post(
            f"{BACKEND_URL}/analyze",
            files={"file": ("big.jpg", big, "image/jpeg")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 413

    def test_frontend_api_proxy_works(self):
        """Nginx /api/analyze → backend /analyze"""
        r = requests.post(
            f"{FRONTEND_URL}/api/analyze",
            files={"file": ("skin.jpg", make_jpeg(), "image/jpeg")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        assert "prediction" in r.json()
