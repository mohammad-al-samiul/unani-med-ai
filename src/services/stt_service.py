from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import os
import tempfile
import shutil
import base64
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("stt-service")

app = FastAPI(title="Speech-to-Text Service", version="1.1.0")

import importlib

# Lazy-loaded faster-whisper model
_model = None

def get_whisper_model():
    global _model
    if _model is None:
        try:
            whisper_mod = importlib.import_module("faster_whisper")
            WhisperModel = getattr(whisper_mod, "WhisperModel")
            logger.info("Initializing faster-whisper model (base, cpu, int8)...")
            _model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("faster-whisper model loaded successfully.")
        except Exception as e:
            logger.info("faster-whisper not installed or failed to load (%s). Fallback STT active.", e)
            _model = None
    return _model


class AudioURLRequest(BaseModel):
    audio_url: str
    language: Optional[str] = None  # Optional: specify language like 'bn', 'en', etc. If None, auto-detect

class AudioBase64Request(BaseModel):
    audio_base64: str
    language: Optional[str] = None
    file_format: str = "webm"  # webm, wav, mp3, ogg


@app.post("/transcribe-url")
async def transcribe_from_url(request: AudioURLRequest):
    """Transcribe audio from a URL."""
    model = get_whisper_model()
    if not model:
        raise HTTPException(status_code=503, detail="Whisper model is not available")

    temp_dir = None
    temp_file_path = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        temp_filename = f"{uuid.uuid4()}.audio"
        temp_file_path = os.path.join(temp_dir, temp_filename)
        
        response = requests.get(request.audio_url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        segments, info = model.transcribe(
            temp_file_path,
            language=request.language if request.language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        transcribed_text = " ".join([segment.text for segment in segments])
        
        return JSONResponse(content={
            "success": True,
            "text": transcribed_text.strip(),
            "detected_language": info.language,
            "language_probability": info.language_probability
        })
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@app.post("/transcribe-base64")
async def transcribe_from_base64(request: AudioBase64Request):
    """Transcribe audio encoded in base64 string."""
    model = get_whisper_model()
    if not model:
        raise HTTPException(status_code=503, detail="Whisper model is not available")

    temp_dir = None
    temp_file_path = None

    try:
        raw_b64 = request.audio_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        audio_bytes = base64.b64decode(raw_b64)

        temp_dir = tempfile.mkdtemp()
        ext = f".{request.file_format}" if not request.file_format.startswith(".") else request.file_format
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")

        with open(temp_file_path, 'wb') as f:
            f.write(audio_bytes)

        segments, info = model.transcribe(
            temp_file_path,
            language=request.language if request.language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        transcribed_text = " ".join([segment.text for segment in segments])

        return JSONResponse(content={
            "success": True,
            "text": transcribed_text.strip(),
            "detected_language": info.language,
            "language_probability": info.language_probability
        })

    except Exception as e:
        logger.error("Base64 transcription error: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# Check multipart support
_has_multipart = False
try:
    import multipart
    _has_multipart = True
except ImportError:
    pass

@app.post("/transcribe-file")
async def transcribe_from_file(request: Request, language: Optional[str] = None):
    """Transcribe audio from uploaded file or raw audio body."""
    model = get_whisper_model()
    if not model:
        raise HTTPException(status_code=503, detail="Whisper model is not available")

    temp_dir = None
    temp_file_path = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        temp_filename = f"{uuid.uuid4()}.audio"
        temp_file_path = os.path.join(temp_dir, temp_filename)
        
        # Read body directly
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty audio payload")
            
        with open(temp_file_path, 'wb') as f:
            f.write(body)
        
        segments, info = model.transcribe(
            temp_file_path,
            language=language if language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        transcribed_text = " ".join([segment.text for segment in segments])
        
        return JSONResponse(content={
            "success": True,
            "text": transcribed_text.strip(),
            "detected_language": info.language,
            "language_probability": info.language_probability
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "speech-to-text",
        "whisper_ready": _model is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)