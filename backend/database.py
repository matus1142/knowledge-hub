import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = os.getenv("DB_PATH", "/app/data/db/knowledge.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_fts(db_path: str = DB_PATH):
    import sqlite3
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Standard (non-contentless) FTS5 so snippet() works and rows persist
    cur.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
            topic_id UNINDEXED,
            name,
            extracted_text,
            tokenize='unicode61'
        );
    """)
    con.commit()
    con.close()
