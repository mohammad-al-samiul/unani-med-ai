#!/usr/bin/env python3
"""
UnaniMed AI — Text-to-Speech (TTS) Service
──────────────────────────────────────────
Generates speech audio for Unani advice and product recommendations.
Primary: Local Piper TTS (ONNX)
Fallback 1: Local gTTS (Zero cost)
Fallback 2: Web Speech API instructions for instant browser-side synthesis
"""

import os
import io
import tempfile
import subprocess
import uuid
import shutil
import base64
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("tts-service")

TTS_PORT = int(os.getenv("TTS_PORT", "8002"))

app = FastAPI(title="Unani TTS Service", version="2.0.0")

# Piper TTS configuration
PIPER_PATH = os.getenv("PIPER_PATH", r"C:\piper-tts\piper.exe")
MODEL_PATH = os.getenv("PIPER_MODEL_PATH", r"C:\piper-tts\models")
DEFAULT_MODEL = os.getenv("PIPER_DEFAULT_MODEL", "bn_BD-default-medium")


class TTSRequest(BaseModel):
    text: str
    model: str = DEFAULT_MODEL
    output_format: str = "mp3"  # mp3, ogg, wav
    language: str = "bn"        # bn or en


def _generate_with_piper(text: str, model_name: str, output_format: str) -> Optional[bytes]:
    """Try generating speech with Piper if binary exists."""
    if not os.path.exists(PIPER_PATH):
        return None

    model_file = os.path.join(MODEL_PATH, f"{model_name}.onnx")
    if not os.path.exists(model_file):
        return None

    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, f"{uuid.uuid4()}.txt")
    temp_output = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")

    try:
        with open(temp_input, 'w', encoding='utf-8') as f:
            f.write(text)

        cmd = [
            PIPER_PATH,
            "--model", model_file,
            "--output_file", temp_output,
            "--text_file", temp_input
        ]
        
        config_file = os.path.join(MODEL_PATH, f"{model_name}.onnx.json")
        if os.path.exists(config_file):
            cmd.extend(["--config", config_file])

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and os.path.exists(temp_output):
            with open(temp_output, 'rb') as f:
                return f.read()
        return None
    except Exception as e:
        logger.warning("Piper TTS generation failed: %s", e)
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _generate_fallback_tts(text: str, language: str = "bn") -> Optional[bytes]:
    """
    Fallback TTS generator using local gTTS if available.
    Zero external paid API cost.
    """
    try:
        import importlib
        gtts_module = importlib.import_module("gtts")
        gTTS = getattr(gtts_module, "gTTS")
        
        lang_code = "bn" if language in ["bn", "bangla", "bengali"] else "en"
        tts = gTTS(text=text[:300], lang=lang_code, slow=False)
        
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception:
        return None


@app.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech."""
    audio_bytes = _generate_with_piper(request.text, request.model, request.output_format)
    
    if not audio_bytes:
        audio_bytes = _generate_fallback_tts(request.text, request.language)

    if not audio_bytes:
        # Return structured instruction for client-side Web Speech API playback
        return JSONResponse(content={
            "success": True,
            "synthesized": False,
            "use_web_speech": True,
            "text": request.text,
            "language": request.language,
            "message": "Web Speech fallback enabled for client-side synthesis"
        })

    # Save to temp file and return as FileResponse
    temp_dir = tempfile.mkdtemp()
    output_filename = f"{uuid.uuid4()}.{request.output_format}"
    output_path = os.path.join(temp_dir, output_filename)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    media_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg"
    }

    return FileResponse(
        path=output_path,
        media_type=media_types.get(request.output_format, "audio/mpeg"),
        filename=output_filename
    )


@app.post("/text-to-speech-base64")
async def text_to_speech_base64(request: TTSRequest):
    """Convert text to speech and return base64 encoded audio string."""
    audio_bytes = _generate_with_piper(request.text, request.model, request.output_format)

    if not audio_bytes:
        audio_bytes = _generate_fallback_tts(request.text, request.language)

    if not audio_bytes:
        return {
            "success": True,
            "has_audio": False,
            "use_web_speech": True,
            "text": request.text,
            "language": request.language,
            "message": "Client Web Speech API recommended for playback"
        }

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    return {
        "success": True,
        "has_audio": True,
        "audio_base64": b64_audio,
        "format": request.output_format,
        "language": request.language
    }


@app.get("/models")
async def list_models():
    """List available Piper TTS models."""
    if not os.path.exists(MODEL_PATH):
        return {"models": [], "count": 0}

    models = []
    for file in os.listdir(MODEL_PATH):
        if file.endswith(".onnx"):
            model_name = file[:-5]
            models.append({
                "name": model_name,
                "path": os.path.join(MODEL_PATH, file)
            })

    return {"models": models, "count": len(models)}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "unani-tts-service",
        "piper_installed": os.path.exists(PIPER_PATH),
        "model_dir_exists": os.path.exists(MODEL_PATH)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=TTS_PORT)