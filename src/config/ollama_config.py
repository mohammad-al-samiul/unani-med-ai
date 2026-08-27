#!/usr/bin/env python3
"""
Ollama Keep-Alive Manager
──────────────────────────
Dynamically adjusts the keep_alive duration based on time-of-day and activity:

  • Peak hours (8 AM – 11 PM)  → keep_alive = 10m  (model stays warm)
  • Off-peak  (11 PM – 8 AM)  → keep_alive = 0     (unload immediately, free VRAM)
  • Manual warm/unload via FastAPI endpoints

Run standalone:
    python ollama_config.py

Or call the endpoints from n8n / other services:
    POST http://localhost:8009/warm   → load model now
    POST http://localhost:8009/unload → unload model now
    GET  http://localhost:8009/status → current keep_alive state
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME      = os.getenv("OLLAMA_MODEL", "unani-med")   # built from Modelfile
PEAK_START_H    = int(os.getenv("PEAK_START", "8"))        # 08:00
PEAK_END_H      = int(os.getenv("PEAK_END",   "23"))       # 23:00
POLL_INTERVAL   = int(os.getenv("POLL_SEC",   "300"))      # check every 5 min

KEEP_ALIVE_PEAK    = "10m"
KEEP_ALIVE_OFFPEAK = "0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ollama-config")

# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_peak() -> bool:
    hour = datetime.now().hour
    return PEAK_START_H <= hour < PEAK_END_H


async def _set_keep_alive(keep_alive: str) -> bool:
    """
    Ollama does not expose a standalone keep_alive endpoint,
    so we send a trivial generate request with keep_alive set.
    The model will stay loaded for the specified duration after this call.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": "",          # empty prompt — just keeps/unloads the model
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_predict": 1},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            resp.raise_for_status()
            logger.info("keep_alive set to %s for model '%s'.", keep_alive, MODEL_NAME)
            return True
    except Exception as exc:
        logger.error("Failed to set keep_alive: %s", exc)
        return False


async def _get_loaded_models() -> list:
    """Return list of currently loaded models from Ollama /api/ps."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/ps")
            resp.raise_for_status()
            return resp.json().get("models", [])
    except Exception:
        return []


# ── Background scheduler ───────────────────────────────────────────────────────

_current_keep_alive: str = KEEP_ALIVE_PEAK


async def _scheduler():
    """Background loop: adjust keep_alive every POLL_INTERVAL seconds."""
    global _current_keep_alive
    while True:
        desired = KEEP_ALIVE_PEAK if _is_peak() else KEEP_ALIVE_OFFPEAK
        if desired != _current_keep_alive:
            success = await _set_keep_alive(desired)
            if success:
                _current_keep_alive = desired
                logger.info(
                    "Switched to %s mode (keep_alive=%s).",
                    "PEAK" if desired != "0" else "OFF-PEAK",
                    desired,
                )
        await asyncio.sleep(POLL_INTERVAL)


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Ollama Keep-Alive Manager", version="1.0.0")


@app.on_event("startup")
async def startup():
    # Apply correct keep_alive immediately on start
    initial = KEEP_ALIVE_PEAK if _is_peak() else KEEP_ALIVE_OFFPEAK
    await _set_keep_alive(initial)
    asyncio.create_task(_scheduler())
    logger.info("Ollama keep-alive manager started.")


@app.post("/warm")
async def warm_model():
    """Force load the model into VRAM and keep it for peak duration."""
    global _current_keep_alive
    success = await _set_keep_alive(KEEP_ALIVE_PEAK)
    if success:
        _current_keep_alive = KEEP_ALIVE_PEAK
    return {"success": success, "keep_alive": KEEP_ALIVE_PEAK}


@app.post("/unload")
async def unload_model():
    """Immediately unload the model from VRAM."""
    global _current_keep_alive
    success = await _set_keep_alive(KEEP_ALIVE_OFFPEAK)
    if success:
        _current_keep_alive = KEEP_ALIVE_OFFPEAK
    return {"success": success, "keep_alive": KEEP_ALIVE_OFFPEAK}


@app.get("/status")
async def status() -> Dict[str, Any]:
    """Current keep_alive state and loaded models."""
    loaded = await _get_loaded_models()
    model_loaded = any(m.get("name", "").startswith(MODEL_NAME) for m in loaded)
    return {
        "current_keep_alive": _current_keep_alive,
        "mode": "peak" if _is_peak() else "off-peak",
        "peak_hours": f"{PEAK_START_H:02d}:00 – {PEAK_END_H:02d}:00",
        "model": MODEL_NAME,
        "model_loaded_in_vram": model_loaded,
        "loaded_models": [m.get("name") for m in loaded],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ollama-keep-alive-manager"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
