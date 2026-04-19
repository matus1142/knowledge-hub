import sqlite3
from fastapi import APIRouter, Query
from database import DB_PATH
from schemas import SearchResult

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResult])
def search(q: str = Query(..., min_length=1), limit: int = 50):
    if not q.strip():
        return []

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Use FTS5 MATCH for full-text search
    safe_q = q.replace('"', '""')
    try:
        rows = con.execute(
            """
            SELECT
                t.id,
                t.name,
                t.folder_id,
                t.file_type,
                snippet(topics_fts, 2, '<mark>', '</mark>', '…', 32) AS snippet,
                topics_fts.rank AS rank
            FROM topics_fts
            JOIN topics t ON t.id = topics_fts.topic_id
            WHERE topics_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (safe_q, limit),
        ).fetchall()
    except Exception:
        # Fallback to LIKE search if FTS fails (e.g. special chars)
        like_q = f"%{q}%"
        rows = con.execute(
            """
            SELECT id, name, folder_id, file_type,
                   SUBSTR(extracted_text, 1, 200) AS snippet,
                   0.0 AS rank
            FROM topics
            WHERE name LIKE ? OR extracted_text LIKE ?
            LIMIT ?
            """,
            (like_q, like_q, limit),
        ).fetchall()

    con.close()
    results = []
    for r in rows:
        results.append(
            SearchResult(
                id=r["id"],
                name=r["name"],
                folder_id=r["folder_id"],
                file_type=r["file_type"],
                snippet=r["snippet"] or "",
                rank=float(r["rank"]),
            )
        )
    return results
