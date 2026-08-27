#!/usr/bin/env python3
"""
Local Analytics Service  (Port 8008)
───────────────────────────────────────
Tracks every query event so you can see:
  • Which symptoms / topics appear most often
  • Cache hit rate over time
  • Response latency trends
  • Daily/weekly active users

All data stays on your machine — zero cloud, zero cost.

Data sources:
  • n8n calls POST /event after every processed message
  • GET  /dashboard  — full summary for Metabase / Grafana JSON datasource
  • GET  /export     — download raw events as JSON
  • GET  /top-queries — most frequent questions
  • GET  /daily-stats — per-day counters

Metabase / Grafana:
  Point a "JSON / HTTP API" datasource at http://localhost:8008/dashboard
  to get live charts with no extra setup.
"""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analytics-service")

DB_PATH = Path("./analytics.db")


# ── Database ───────────────────────────────────────────────────────────────────

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id              TEXT PRIMARY KEY,
                event_type      TEXT NOT NULL,   -- 'query', 'cache_hit', 'cache_miss', 'error', 'voice'
                sender_id       TEXT,
                question        TEXT,
                normalized_q    TEXT,
                category        TEXT,            -- top symptom category detected
                cache_hit       INTEGER,         -- 1 / 0 / NULL
                latency_ms      INTEGER,         -- end-to-end latency
                response_length INTEGER,
                model_used      TEXT,
                created_at      TEXT NOT NULL,
                date_only       TEXT NOT NULL    -- YYYY-MM-DD for fast daily grouping
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_type    ON events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_date    ON events(date_only)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_sender  ON events(sender_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_cat     ON events(category)")
        conn.commit()
    logger.info("Analytics DB initialized at %s", DB_PATH)


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_init_db()


# ── Category detection (simple keyword matching) ───────────────────────────────

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "ব্যথা":        ["ব্যথা", "বেদনা", "ব্যাথা"],
    "জ্বর":         ["জ্বর", "তাপমাত্রা", "গরম"],
    "কাশি":         ["কাশি", "সর্দি", "ঠান্ডা"],
    "পেট সমস্যা":   ["পেটব্যথা", "ডায়রিয়া", "গ্যাস্ট্রিক", "বদহজম"],
    "মাথাব্যথা":    ["মাথাব্যথা", "মাইগ্রেন"],
    "ডায়াবেটিস":   ["ডায়াবেটিস", "সুগার", "ইনসুলিন"],
    "হৃদরোগ":       ["হার্ট", "বুকব্যথা", "রক্তচাপ"],
    "শ্বাসকষ্ট":   ["শ্বাসকষ্ট", "হাঁপানি", "শ্বাস"],
    "ত্বক":         ["চর্মরোগ", "চুলকানি", "ফুসকুড়ি", "ঘা"],
    "ঘুম":          ["ঘুম", "অনিদ্রা", "ঘুমাতে পারি না"],
}


def _detect_category(text: str) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "অন্যান্য"


# ── Models ─────────────────────────────────────────────────────────────────────

class EventRequest(BaseModel):
    event_type:      str                    # 'query', 'cache_hit', 'cache_miss', 'error', 'voice'
    sender_id:       Optional[str] = None
    question:        Optional[str] = None
    normalized_q:    Optional[str] = None
    cache_hit:       Optional[bool] = None
    latency_ms:      Optional[int] = None
    response_length: Optional[int] = None
    model_used:      Optional[str] = None


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Analytics Service", version="1.0.0")


@app.post("/event", status_code=201)
async def record_event(req: EventRequest):
    """Record a single analytics event from n8n or any service."""
    now = datetime.utcnow()
    category = _detect_category(req.normalized_q or req.question or "")

    with _db() as conn:
        conn.execute(
            """INSERT INTO events
               (id, event_type, sender_id, question, normalized_q, category,
                cache_hit, latency_ms, response_length, model_used, created_at, date_only)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                req.event_type,
                req.sender_id,
                req.question,
                req.normalized_q,
                category,
                int(req.cache_hit) if req.cache_hit is not None else None,
                req.latency_ms,
                req.response_length,
                req.model_used,
                now.isoformat(),
                now.strftime("%Y-%m-%d"),
            ),
        )
        conn.commit()

    return {"status": "recorded", "category": category}


@app.get("/dashboard")
async def dashboard(days: int = Query(default=30, ge=1, le=365)):
    """
    Full analytics summary — use this as the JSON datasource in Metabase/Grafana.
    """
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    with _db() as conn:
        # Overall counts
        overview = conn.execute(
            """SELECT
                 COUNT(*)                                          AS total_events,
                 COUNT(DISTINCT sender_id)                        AS unique_users,
                 SUM(CASE WHEN event_type='query' THEN 1 END)     AS total_queries,
                 SUM(CASE WHEN cache_hit=1        THEN 1 END)     AS cache_hits,
                 SUM(CASE WHEN event_type='voice' THEN 1 END)     AS voice_queries,
                 SUM(CASE WHEN event_type='error' THEN 1 END)     AS errors,
                 ROUND(AVG(latency_ms), 0)                        AS avg_latency_ms,
                 ROUND(AVG(response_length), 0)                   AS avg_response_length
               FROM events WHERE date_only >= ?""",
            (since,),
        ).fetchone()

        # Cache hit rate
        cache_row = conn.execute(
            """SELECT
                 SUM(cache_hit)                                    AS hits,
                 COUNT(CASE WHEN cache_hit IS NOT NULL THEN 1 END) AS lookups
               FROM events WHERE date_only >= ?""",
            (since,),
        ).fetchone()

        # Top categories
        categories = conn.execute(
            """SELECT category, COUNT(*) AS cnt
               FROM events WHERE date_only >= ? AND category IS NOT NULL
               GROUP BY category ORDER BY cnt DESC LIMIT 10""",
            (since,),
        ).fetchall()

        # Daily counts (last 30 days max for chart)
        daily = conn.execute(
            """SELECT date_only,
                 COUNT(*)                                      AS queries,
                 COUNT(DISTINCT sender_id)                     AS users,
                 SUM(CASE WHEN cache_hit=1 THEN 1 END)        AS cache_hits,
                 ROUND(AVG(latency_ms), 0)                    AS avg_latency_ms
               FROM events
               WHERE date_only >= ?
               GROUP BY date_only ORDER BY date_only""",
            (since,),
        ).fetchall()

        # Top questions (by normalized text)
        top_q = conn.execute(
            """SELECT normalized_q AS question, COUNT(*) AS cnt
               FROM events
               WHERE date_only >= ? AND normalized_q IS NOT NULL
               GROUP BY normalized_q ORDER BY cnt DESC LIMIT 20""",
            (since,),
        ).fetchall()

    total_queries = overview["total_queries"] or 0
    cache_hits    = cache_row["hits"]    or 0
    cache_lookups = cache_row["lookups"] or 0
    hit_rate = round(cache_hits / cache_lookups, 4) if cache_lookups else 0.0

    return {
        "period_days": days,
        "overview": {
            "total_events":       overview["total_events"],
            "unique_users":       overview["unique_users"],
            "total_queries":      total_queries,
            "voice_queries":      overview["voice_queries"] or 0,
            "errors":             overview["errors"]        or 0,
            "avg_latency_ms":     overview["avg_latency_ms"],
            "avg_response_length":overview["avg_response_length"],
        },
        "cache": {
            "hits":       cache_hits,
            "lookups":    cache_lookups,
            "hit_rate":   hit_rate,
        },
        "top_categories": [{"category": r["category"], "count": r["cnt"]} for r in categories],
        "daily_stats":    [dict(r) for r in daily],
        "top_questions":  [{"question": r["question"], "count": r["cnt"]} for r in top_q],
        "generated_at":   datetime.utcnow().isoformat(),
    }


@app.get("/top-queries")
async def top_queries(
    days:  int = Query(default=7,  ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=200),
):
    """Most frequently asked (normalized) questions."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    with _db() as conn:
        rows = conn.execute(
            """SELECT normalized_q AS question, COUNT(*) AS cnt
               FROM events WHERE date_only >= ? AND normalized_q IS NOT NULL
               GROUP BY normalized_q ORDER BY cnt DESC LIMIT ?""",
            (since, limit),
        ).fetchall()
    return {"results": [dict(r) for r in rows], "period_days": days}


@app.get("/daily-stats")
async def daily_stats(days: int = Query(default=14, ge=1, le=90)):
    """Per-day query counts for the last N days."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    with _db() as conn:
        rows = conn.execute(
            """SELECT date_only, COUNT(*) AS queries,
                 COUNT(DISTINCT sender_id) AS users
               FROM events WHERE date_only >= ?
               GROUP BY date_only ORDER BY date_only""",
            (since,),
        ).fetchall()
    return {"results": [dict(r) for r in rows]}


@app.get("/export")
async def export_events(days: int = Query(default=30, ge=1, le=365)):
    """Export raw events as JSON (for offline analysis)."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE created_at >= ? ORDER BY created_at",
            (since,),
        ).fetchall()
    data = [dict(r) for r in rows]
    return JSONResponse(content={"events": data, "count": len(data), "period_days": days})


@app.get("/health")
async def health():
    with _db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"status": "healthy", "service": "analytics-service", "total_events": total}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
