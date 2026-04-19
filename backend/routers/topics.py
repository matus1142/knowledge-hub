import os
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db, DB_PATH
from models import Topic
from schemas import TopicOut, TopicUpdate

router = APIRouter(prefix="/topics", tags=["topics"])

UPLOADS_DIR = os.getenv("UPLOADS_DIR", "/app/data/uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".html", ".htm", ".pdf", ".md", ".markdown"}


def ext_to_file_type(ext: str) -> str:
    if ext in (".html", ".htm"):
        return "html"
    if ext == ".pdf":
        return "pdf"
    if ext in (".md", ".markdown"):
        return "markdown"
    raise ValueError(f"Unsupported extension: {ext}")


def extract_text_from_html(content: bytes) -> str:
    import re
    text = content.decode("utf-8", errors="ignore")
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500000]


def extract_text_from_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        parts = [page.extract_text() or "" for page in reader.pages]
        return " ".join(parts)[:500000]
    except Exception:
        return ""


def extract_text_from_markdown(content: bytes) -> str:
    import re
    text = content.decode("utf-8", errors="ignore")
    # Strip markdown syntax for indexing
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_~]{1,3}", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500000]


def fts_insert(topic_id: int, name: str, extracted_text: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO topics_fts(topic_id, name, extracted_text) VALUES (?,?,?)",
        (topic_id, name, extracted_text or ""),
    )
    con.commit()
    con.close()


def fts_update(topic_id: int, name: str, extracted_text: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM topics_fts WHERE topic_id=?", (topic_id,))
    con.execute(
        "INSERT INTO topics_fts(topic_id, name, extracted_text) VALUES (?,?,?)",
        (topic_id, name, extracted_text or ""),
    )
    con.commit()
    con.close()


def fts_delete(topic_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM topics_fts WHERE topic_id=?", (topic_id,))
    con.commit()
    con.close()


def do_extract(file_type: str, content: bytes, file_path: str) -> str:
    if file_type == "html":
        return extract_text_from_html(content)
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    if file_type == "markdown":
        return extract_text_from_markdown(content)
    return ""


@router.get("", response_model=list[TopicOut])
def list_topics(folder_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Topic)
    if folder_id is not None:
        q = q.filter(Topic.folder_id == folder_id)
    return q.order_by(Topic.updated_at.desc()).all()


@router.get("/recent", response_model=list[TopicOut])
def recent_topics(limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(Topic)
        .filter(Topic.last_opened.isnot(None))
        .order_by(Topic.last_opened.desc())
        .limit(limit)
        .all()
    )


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    return topic


@router.post("", response_model=TopicOut)
async def create_topic(
    name: str = Form(...),
    folder_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only HTML, PDF, and Markdown files are supported")

    file_type = ext_to_file_type(ext)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    extracted_text = do_extract(file_type, content, file_path)

    topic = Topic(
        name=name,
        folder_id=folder_id if folder_id else None,
        file_type=file_type,
        file_path=filename,
        extracted_text=extracted_text,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)

    fts_insert(topic.id, topic.name, extracted_text)
    return topic


@router.put("/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, body: TopicUpdate, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    if body.name is not None:
        topic.name = body.name
    if body.folder_id is not None:
        topic.folder_id = body.folder_id if body.folder_id != 0 else None
    topic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(topic)
    fts_update(topic.id, topic.name, topic.extracted_text or "")
    return topic


@router.delete("/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    file_path = os.path.join(UPLOADS_DIR, topic.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    fts_delete(topic_id)
    db.delete(topic)
    db.commit()
    return {"ok": True}


@router.patch("/{topic_id}/file", response_model=TopicOut)
async def replace_file(
    topic_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only HTML, PDF, and Markdown files are supported")

    old_path = os.path.join(UPLOADS_DIR, topic.file_path)
    if os.path.exists(old_path):
        os.remove(old_path)

    file_type = ext_to_file_type(ext)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    extracted_text = do_extract(file_type, content, file_path)

    topic.file_path = filename
    topic.file_type = file_type
    topic.extracted_text = extracted_text
    topic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(topic)

    fts_update(topic.id, topic.name, extracted_text)
    return topic


@router.patch("/{topic_id}/content", response_model=TopicOut)
async def edit_content(
    topic_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    if topic.file_type not in ("html", "markdown"):
        raise HTTPException(400, "Only HTML and Markdown topics can be edited in-place")

    file_path = os.path.join(UPLOADS_DIR, topic.file_path)
    encoded = content.encode("utf-8")
    with open(file_path, "wb") as f:
        f.write(encoded)

    extracted_text = do_extract(topic.file_type, encoded, file_path)
    topic.extracted_text = extracted_text
    topic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(topic)

    fts_update(topic.id, topic.name, extracted_text)
    return topic


@router.patch("/{topic_id}/opened")
def mark_opened(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    topic.last_opened = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/{topic_id}/file")
def serve_file(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    file_path = os.path.join(UPLOADS_DIR, topic.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk")
    media_map = {"html": "text/html", "pdf": "application/pdf", "markdown": "text/plain"}
    return FileResponse(file_path, media_type=media_map.get(topic.file_type, "application/octet-stream"))


@router.get("/{topic_id}/download")
def download_file(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    file_path = os.path.join(UPLOADS_DIR, topic.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk")
    ext = os.path.splitext(topic.file_path)[-1]
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in topic.name)
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"{safe_name}{ext}",
    )


@router.get("/{topic_id}/raw")
def get_raw_content(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    if topic.file_type not in ("html", "markdown"):
        raise HTTPException(400, "Only HTML and Markdown topics have raw content")
    file_path = os.path.join(UPLOADS_DIR, topic.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk")
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return {"content": f.read(), "file_type": topic.file_type}
