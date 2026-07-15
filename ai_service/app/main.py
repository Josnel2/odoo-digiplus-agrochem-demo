import json
import os
import re
from datetime import date
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "1024"))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

SYSTEM_PROMPT = """Tu es l'assistant IA operationnel de DigiPlus Consulting integre a Odoo. Structure les projets, phases, taches, cartes Kanban, livrables, risques et criteres d'acceptation. Reponds uniquement avec un objet JSON valide, sans Markdown. Sois realiste et adapte au contexte d'une PME technologique camerounaise. L'IA prepare et propose ; l'humain valide les decisions sensibles."""

app = FastAPI(title="DigiPlus AI Service", version="1.0.0")


class ProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1)
    client: str = ""
    deadline: date | None = None
    project_type: str | None = None
    model: str | None = None
    system_prompt: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/generate")
async def generate_project(payload: ProjectRequest) -> dict[str, Any]:
    prompt = _project_prompt(payload)
    ollama_payload = {
        "model": payload.model or OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "options": {"num_ctx": OLLAMA_NUM_CTX, "temperature": 0.2},
        "messages": [
            {"role": "system", "content": payload.system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(OLLAMA_URL, json=ollama_payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Ollama n'a pas repondu a temps") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama indisponible: {exc}") from exc

    try:
        content = response.json()["message"]["content"]
        generated = _parse_json(content)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Ollama a retourne une reponse JSON invalide") from exc
    project = generated.get("project", generated)
    if not isinstance(project, dict):
        raise HTTPException(status_code=502, detail="Le projet genere doit etre un objet JSON")
    project.setdefault("name", payload.project_name)
    project.setdefault("client", payload.client)
    project.setdefault("tasks", [])
    project.setdefault("phases", [])
    project.setdefault("risks", [])
    project.setdefault("deliverables", [])
    project.setdefault("acceptance_criteria", [])
    return {"project": project}


def _project_prompt(payload: ProjectRequest) -> str:
    return f"""Genere le brouillon structure du projet suivant.
Nom: {payload.project_name}
Client: {payload.client or 'Non precise'}
Type: {payload.project_type or 'Autre'}
Echeance: {payload.deadline.isoformat() if payload.deadline else 'Non precisee'}
Description: {payload.description}

Schema obligatoire:
{{"project": {{"name": "", "client": "", "objective": "", "phases": [], "tasks": [{{"title": "", "description": "", "priority": "low|medium|high|critical", "status": "backlog|todo|in_progress|review|blocked|done", "assignee_role": "", "estimated_duration": 0, "deadline": "YYYY-MM-DD ou null", "acceptance_criteria": [], "phase": "", "deliverables": []}}], "risks": [], "deliverables": [{{"name": "", "description": "", "deadline": "YYYY-MM-DD ou null"}}], "acceptance_criteria": []}}}}"""


def _parse_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("JSON root must be an object")
    return result
