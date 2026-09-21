# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


class _FakeOllamaResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": {
                "content": '{"project":{"objective":"Déployer Odoo","tasks":[]}}'
            }
        }


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        return _FakeOllamaResponse()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_project(monkeypatch):
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/projects/generate",
        json={
            "project_name": "Projet Connect237",
            "client": "Client Test",
            "description": "Déployer une solution Odoo.",
            "project_type": "Projet Odoo",
        },
    )

    assert response.status_code == 200
    project = response.json()["project"]
    assert project["name"] == "Projet Connect237"
    assert project["client"] == "Client Test"
    assert project["objective"] == "Déployer Odoo"
    assert project["tasks"] == []
    assert project["phases"] == []
    assert project["risks"] == []
    assert project["deliverables"] == []


def test_generate_project_rejects_empty_name():
    response = client.post(
        "/projects/generate",
        json={"project_name": "", "description": "Description valide"},
    )
    assert response.status_code == 422


def test_generate_project_reports_invalid_ollama_json(monkeypatch):
    class InvalidResponse(_FakeOllamaResponse):
        def json(self):
            return {"message": {"content": "pas du json"}}

    class InvalidClient(_FakeAsyncClient):
        async def post(self, url, json):
            return InvalidResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", InvalidClient)
    response = client.post(
        "/projects/generate",
        json={"project_name": "Projet", "description": "Description"},
    )
    assert response.status_code == 502
    assert "JSON invalide" in response.json()["detail"]
