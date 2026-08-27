#!/usr/bin/env python3
"""
Feedback Service  (Port 8007)
───────────────────────────────
Stores per-response thumbs-up / thumbs-down feedback in a local SQLite DB.

n8n integration:
  After sending reply to Messenger, send a quick-reply with two buttons:
    payload: "FEEDBACK_GOOD_<response_id>"
    payload: "FEEDBACK_BAD_<response_id>"
  Then route the postback to POST /feedback.

Endpoints:
  POST /feedback            Record a feedback event
  GET  /feedback/summary    Aggregate stats per category / time window
  GET  /feedback/recent     Last N feedback entries
  GET  /feedback/worst      Responses with most 👎 (for review)
  GET  /health
"""

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("feedback-service")

DB_PATH = Path("./feedback.db")


# ── Database ───────────────────────────────────────────────────────────────────

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id            TEXT PRIMARY KEY,
                response_id   TEXT NOT NULL,
                sender_id     TEXT NOT NULL,
                rating        INTEGER NOT NULL CHECK(rating IN (1, -1)),
                question      TEXT,
                response_text TEXT,
                category      TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_response  ON feedback(response_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_sender    ON feedback(sender_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_created   ON feedback(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_rating    ON feedback(rating)")
        conn.commit()
    logger.info("Feedback DB initialized at %s", DB_PATH)


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_init_db()


# ── Models ─────────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    response_id:   str
    sender_id:     str
    rating:        int           # +1 = 👍, -1 = 👎
    question:      Optional[str] = None
    response_text: Optional[str] = None
    category:      Optional[str] = None   # e.g. "ব্যথা", "জ্বর", etc.


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Feedback Service", version="1.0.0")


@app.post("/feedback", status_code=201)
async def record_feedback(req: FeedbackRequest):
    """Record a 👍/👎 feedback event."""
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 (👍) or -1 (👎)")

    fb_id = str(uuid.uuid4())
    now   = datetime.utcnow().isoformat()

    with _db() as conn:
        conn.execute(
            """INSERT INTO feedback
               (id, response_id, sender_id, rating, question, response_text, category, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fb_id, req.response_id, req.sender_id, req.rating,
             req.question, req.response_text, req.category, now),
        )
        conn.commit()

    logger.info("Feedback recorded: %s  rating=%+d  sender=%s", fb_id, req.rating, req.sender_id)
    return {"id": fb_id, "status": "recorded"}


@app.get("/feedback/summary")
async def feedback_summary(days: int = Query(default=30, ge=1, le=365)):
    """Aggregate thumbs-up/down stats for the last N days."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    with _db() as conn:
        row = conn.execute(
            """SELECT
                 COUNT(*)                             AS total,
                 SUM(CASE WHEN rating=1  THEN 1 END)  AS thumbs_up,
                 SUM(CASE WHEN rating=-1 THEN 1 END)  AS thumbs_down
               FROM feedback WHERE created_at >= ?""",
            (since,),
        ).fetchone()

        by_category = conn.execute(
            """SELECT category,
                 COUNT(*)                             AS total,
                 SUM(CASE WHEN rating=1  THEN 1 END)  AS thumbs_up,
                 SUM(CASE WHEN rating=-1 THEN 1 END)  AS thumbs_down
               FROM feedback WHERE created_at >= ? AND category IS NOT NULL
               GROUP BY category ORDER BY total DESC""",
            (since,),
        ).fetchall()

    total      = row["total"] or 0
    thumbs_up  = row["thumbs_up"]  or 0
    thumbs_down= row["thumbs_down"] or 0
    positive_rate = round(thumbs_up / total, 4) if total else 0.0

    return {
        "period_days":    days,
        "total_feedback": total,
        "thumbs_up":      thumbs_up,
        "thumbs_down":    thumbs_down,
        "positive_rate":  positive_rate,
        "by_category": [
            {
                "category":      r["category"],
                "total":         r["total"],
                "thumbs_up":     r["thumbs_up"]   or 0,
                "thumbs_down":   r["thumbs_down"] or 0,
                "positive_rate": round((r["thumbs_up"] or 0) / r["total"], 4),
            }
            for r in by_category
        ],
    }


@app.get("/feedback/recent")
async def recent_feedback(limit: int = Query(default=20, ge=1, le=200)):
    """Return the most recent N feedback entries."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"results": [dict(r) for r in rows], "count": len(rows)}


@app.get("/feedback/worst")
async def worst_responses(limit: int = Query(default=10, ge=1, le=100)):
    """
    Responses with the highest negative feedback ratio.
    Useful for identifying which RAG retrievals need improvement.
    """
    with _db() as conn:
        rows = conn.execute(
            """SELECT
                 response_id,
                 question,
                 COUNT(*)                             AS total,
                 SUM(CASE WHEN rating=-1 THEN 1 END)  AS thumbs_down,
                 ROUND(CAST(SUM(CASE WHEN rating=-1 THEN 1 END) AS REAL) / COUNT(*), 4) AS negative_rate
               FROM feedback
               GROUP BY response_id
               HAVING total >= 2
               ORDER BY negative_rate DESC, thumbs_down DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"results": [dict(r) for r in rows]}


@app.get("/health")
async def health():
    with _db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    return {"status": "healthy", "service": "feedback-service", "total_feedback": total}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
