# SkinApp — CI/CD Pipeline

Projekt klasyfikacji zmian skórnych z pełnym pipeline'em CI/CD opartym na Jenkinsie, Dockerze i Ansible.

---

## Struktura repozytorium

```
melanoma-detector/
├── ai-service/                   # Serwis AI (istniejący model — VM2)
│   ├── api.py                    # FastAPI z modelem PyTorch
│   ├── src/
│   │   └── model.py              # (Twój plik — nie wchodzi do repo)
│   ├── model_gita.pth            # (Twój model — nie commituj do gita!)
│   ├── requirements.txt
│   └── Dockerfile
│
├── backend/                      # Serwer pośredni (VM3)
│   ├── main.py                   # FastAPI proxy → AI service
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_main.py          # Testy jednostkowe (pytest)
│
├── frontend/                     # Interfejs użytkownika (VM3)
│   ├── index.html
│   ├── style.css
│   ├── nginx.conf
│   ├── Dockerfile
│   └── tests/
│       ├── package.json
│       └── frontend.test.js      # Testy jednostkowe (Jest)
│
├── tests/
│   └── e2e/
│       └── test_e2e.py           # Testy end-to-end (pytest + requests)
│
├── ansible/
│   ├── inventory.ini             # Adresy VM
│   ├── deploy.yml                # Deploy frontendu + backendu na VM3
│   ├── deploy-ai.yml             # Deploy serwisu AI na VM2
│   └── roles/
│       └── docker/
│           └── tasks/main.yml    # Automatyczna instalacja Dockera
│
├── docker-compose.yml            # Lokalne dev
├── docker-compose.prod.yml       # Produkcja (używane przez Ansible)
├── Jenkinsfile                   # Deklaratywny pipeline
└── README.md
```

---

## Architektura

```
  Windows Host
      │
      ├─── VM1 (192.168.56.10) ─── Jenkins Master + Docker Registry :5000 + Ansible
      │         │
      │         │ SSH (Jenkins Agent)        │ ansible-playbook
      │         ▼                             ▼
      ├─── VM2 (192.168.56.20) ─── Jenkins Agent + AI Service :8000
      │
      └─── VM3 (192.168.56.30) ─── Frontend :80 + Backend :8080
                                        └─── calls ──► VM2:8000

Użytkownik wchodzi na: http://192.168.56.30
Frontend wysyła zdjęcie do: http://192.168.56.30/api/analyze (nginx proxy)
Nginx przekazuje do: backend:8080/analyze
Backend przekazuje do: http://192.168.56.20:8000/predict
```

