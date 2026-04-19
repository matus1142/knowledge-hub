from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Folder ────────────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

class FolderUpdate(BaseModel):
    name: str

class FolderOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime
    children: list["FolderOut"] = []

    model_config = {"from_attributes": True}

FolderOut.model_rebuild()


# ── Topic ─────────────────────────────────────────────────────────────────────

class TopicOut(BaseModel):
    id: int
    name: str
    folder_id: Optional[int]
    file_type: str
    last_opened: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class TopicUpdate(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[int] = None


# ── Comment ───────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str

class CommentUpdate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    topic_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Search ────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    id: int
    name: str
    folder_id: Optional[int]
    file_type: str
    snippet: str
    rank: float


# ── Config ────────────────────────────────────────────────────────────────────

class AppConfig(BaseModel):
    autosave_interval_ms: int
    ollama_url: str
    ollama_model: str
