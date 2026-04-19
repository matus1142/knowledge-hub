import sqlite3
from fastapi import APIRouter, Query
from database import DB_PATH
from schemas import SearchResult

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResult])
def search(q: str = Query(..., min_length=1), limit: int = 50):
    q = q.strip()
    if not q:
        return []

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = []

    # Try FTS5 first
    try:
        # Wrap each token with * for prefix matching, quote to handle special chars
        tokens = q.split()
        fts_query = " ".join(f'"{t}"*' for t in tokens if t)
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
            (fts_query, limit),
        ).fetchall()
    except Exception:
        rows = []

    # Fallback: LIKE search across both name and extracted_text
    if not rows:
        like_q = f"%{q}%"
        try:
            rows = con.execute(
                """
                SELECT id, name, folder_id, file_type,
                       CASE
                         WHEN instr(lower(extracted_text), lower(?)) > 0
                         THEN '…' || substr(extracted_text,
                               max(1, instr(lower(extracted_text), lower(?)) - 60), 160) || '…'
                         ELSE ''
                       END AS snippet,
                       0.0 AS rank
                FROM topics
                WHERE lower(name) LIKE lower(?) OR lower(extracted_text) LIKE lower(?)
                LIMIT ?
                """,
                (q, q, like_q, like_q, limit),
            ).fetchall()
        except Exception:
            rows = []

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
