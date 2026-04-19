import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, init_fts, DB_PATH
from models import Base
from schemas import AppConfig
from routers import folders, topics, comments, search, ollama

# Create tables
Base.metadata.create_all(bind=engine)
init_fts()

# Re-sync FTS index from existing topics (handles fresh deploys + existing DBs)
def sync_fts():
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        # Find topics missing from FTS
        missing = con.execute("""
            SELECT t.id, t.name, t.extracted_text
            FROM topics t
            LEFT JOIN topics_fts f ON f.topic_id = t.id
            WHERE f.topic_id IS NULL
        """).fetchall()
        for row in missing:
            con.execute(
                "INSERT INTO topics_fts(topic_id, name, extracted_text) VALUES (?,?,?)",
                (row["id"], row["name"] or "", row["extracted_text"] or ""),
            )
        if missing:
            con.commit()
            print(f"[FTS] Re-indexed {len(missing)} existing topic(s)")
        con.close()
    except Exception as e:
        print(f"[FTS] sync warning: {e}")

sync_fts()

app = FastAPI(title="Knowledge Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(folders.router)
app.include_router(topics.router)
app.include_router(comments.router)
app.include_router(search.router)
app.include_router(ollama.router)


@app.get("/config", response_model=AppConfig)
def get_config():
    return AppConfig(
        autosave_interval_ms=int(os.getenv("AUTOSAVE_INTERVAL_MS", "5000")),
        ollama_url=os.getenv("OLLAMA_URL", "http://host.docker.internal:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
