import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, init_fts
from models import Base
from schemas import AppConfig
from routers import folders, topics, comments, search, ollama

# Create tables
Base.metadata.create_all(bind=engine)
init_fts()

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
