import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ollama", tags=["ollama"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class SuggestRequest(BaseModel):
    text: str
    available_folders: list[str] = []


class SuggestResponse(BaseModel):
    suggested_name: str
    suggested_folder: str


@router.get("/status")
async def ollama_status():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                return {"available": True, "model": OLLAMA_MODEL}
    except Exception:
        pass
    return {"available": False}


@router.post("/suggest", response_model=SuggestResponse)
async def suggest(body: SuggestRequest):
    folders_str = ", ".join(body.available_folders) if body.available_folders else "None"
    prompt = f"""You are a knowledge management assistant.
Given the following text extracted from a document, suggest:
1. A concise and descriptive topic name (max 60 characters)
2. The most appropriate folder from the list (or "Root" if none fit)

Available folders: {folders_str}

Document text (first 2000 chars):
{body.text[:2000]}

Respond ONLY with valid JSON in this exact format:
{{"suggested_name": "Topic Name Here", "suggested_folder": "Folder Name or Root"}}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            if r.status_code != 200:
                raise HTTPException(502, "Ollama returned an error")
            data = r.json()
            response_text = data.get("response", "")

            import json, re
            match = re.search(r"\{.*?\}", response_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return SuggestResponse(
                    suggested_name=parsed.get("suggested_name", "Untitled"),
                    suggested_folder=parsed.get("suggested_folder", "Root"),
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Ollama error: {str(e)}")

    raise HTTPException(500, "Could not parse Ollama response")
