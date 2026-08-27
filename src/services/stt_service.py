from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import os
import tempfile
import shutil
from faster_whisper import WhisperModel
import uuid

app = FastAPI(title="Speech-to-Text Service", version="1.0.0")

# Initialize faster-whisper model
# Using a smaller model for faster processing, you can change to 'large-v3' for better accuracy
model = WhisperModel("base", device="cpu", compute_type="int8")

class AudioURLRequest(BaseModel):
    audio_url: str
    language: str = None  # Optional: specify language like 'bn', 'en', etc. If None, auto-detect

@app.post("/transcribe-url")
async def transcribe_from_url(request: AudioURLRequest):
    """
    Transcribe audio from a URL.
    
    Args:
        request: AudioURLRequest containing audio_url and optional language
    
    Returns:
        JSON with transcribed text and detected language
    """
    temp_dir = None
    temp_file_path = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_filename = f"{uuid.uuid4()}.audio"
        temp_file_path = os.path.join(temp_dir, temp_filename)
        
        # Download audio file from URL
        response = requests.get(request.audio_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Save to temporary file
        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Transcribe using faster-whisper
        segments, info = model.transcribe(
            temp_file_path,
            language=request.language if request.language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Combine all segments
        transcribed_text = " ".join([segment.text for segment in segments])
        
        # Get detected language
        detected_language = info.language
        language_probability = info.language_probability
        
        return JSONResponse(content={
            "success": True,
            "text": transcribed_text.strip(),
            "detected_language": detected_language,
            "language_probability": language_probability,
            "segments_count": len(list(segments))
        })
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Cleanup temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.post("/transcribe-file")
async def transcribe_from_file(
    file: UploadFile = File(...),
    language: str = None
):
    """
    Transcribe audio from uploaded file.
    
    Args:
        file: Audio file upload
        language: Optional language specification
    
    Returns:
        JSON with transcribed text and detected language
    """
    temp_dir = None
    temp_file_path = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Determine file extension
        file_extension = os.path.splitext(file.filename)[1] or '.audio'
        temp_filename = f"{uuid.uuid4()}{file_extension}"
        temp_file_path = os.path.join(temp_dir, temp_filename)
        
        # Save uploaded file
        with open(temp_file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Transcribe using faster-whisper
        segments, info = model.transcribe(
            temp_file_path,
            language=language if language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Combine all segments
        transcribed_text = " ".join([segment.text for segment in segments])
        
        # Get detected language
        detected_language = info.language
        language_probability = info.language_probability
        
        return JSONResponse(content={
            "success": True,
            "text": transcribed_text.strip(),
            "detected_language": detected_language,
            "language_probability": language_probability,
            "segments_count": len(list(segments))
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Cleanup temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "speech-to-text"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)