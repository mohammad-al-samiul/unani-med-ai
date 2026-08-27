from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import tempfile
import subprocess
import uuid
import shutil

app = FastAPI(title="Piper TTS Service", version="1.0.0")

# Piper TTS configuration - UPDATE THESE PATHS BASED ON YOUR INSTALLATION
PIPER_PATH = r"C:\piper-tts\piper.exe"  # Adjust this path based on your installation
MODEL_PATH = r"C:\piper-tts\models"     # Adjust this path based on your model location
DEFAULT_MODEL = "en_US-lessac-medium"   # Default voice model

class TTSRequest(BaseModel):
    text: str
    model: str = DEFAULT_MODEL
    output_format: str = "ogg"  # ogg or mp3

@app.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using Piper TTS.
    
    Args:
        request: TTSRequest containing text, model name, and output format
    
    Returns:
        FileResponse with the generated audio file
    """
    temp_dir = None
    temp_input_file = None
    temp_output_file = None
    final_output_file = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Check if Piper exists
        if not os.path.exists(PIPER_PATH):
            raise HTTPException(status_code=500, detail=f"Piper executable not found at {PIPER_PATH}")
        
        # Check if model exists
        model_file = os.path.join(MODEL_PATH, f"{request.model}.onnx")
        if not os.path.exists(model_file):
            raise HTTPException(status_code=400, detail=f"Model file not found: {model_file}")
        
        # Create temporary input text file
        temp_input_file = os.path.join(temp_dir, f"{uuid.uuid4()}.txt")
        with open(temp_input_file, 'w', encoding='utf-8') as f:
            f.write(request.text)
        
        # Generate output filename
        temp_output_file = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
        
        # Run Piper TTS
        model_dir = os.path.dirname(model_file)
        model_name = os.path.basename(model_file).replace('.onnx', '')
        
        cmd = [
            PIPER_PATH,
            "--model", model_file,
            "--output_file", temp_output_file,
            "--text_file", temp_input_file
        ]
        
        # Add model config if exists
        config_file = os.path.join(model_dir, f"{model_name}.onnx.json")
        if os.path.exists(config_file):
            cmd.extend(["--config", config_file])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Piper TTS failed: {result.stderr}")
        
        # Check if output file was created
        if not os.path.exists(temp_output_file):
            raise HTTPException(status_code=500, detail="Piper TTS did not generate output file")
        
        # Convert to requested format if needed
        if request.output_format == "mp3":
            final_output_file = os.path.join(temp_dir, f"{uuid.uuid4()}.mp3")
            # Convert WAV to MP3 using ffmpeg (if available)
            try:
                subprocess.run([
                    "ffmpeg", "-i", temp_output_file, 
                    "-codec:a", "libmp3lame", "-qscale:a", "2",
                    final_output_file
                ], capture_output=True, check=True, timeout=30)
                temp_output_file = final_output_file
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If ffmpeg is not available, return WAV instead
                request.output_format = "wav"
        
        elif request.output_format == "ogg":
            final_output_file = os.path.join(temp_dir, f"{uuid.uuid4()}.ogg")
            try:
                subprocess.run([
                    "ffmpeg", "-i", temp_output_file,
                    "-c:a", "libopus", "-b:a", "64k",
                    final_output_file
                ], capture_output=True, check=True, timeout=30)
                temp_output_file = final_output_file
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If ffmpeg is not available, return WAV instead
                request.output_format = "wav"
        
        # Return the audio file
        return FileResponse(
            temp_output_file,
            media_type=f"audio/{request.output_format}",
            filename=f"tts_output.{request.output_format}"
        )
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="TTS processing timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
    finally:
        # Cleanup temporary files (but keep the output file for the response)
        if temp_input_file and os.path.exists(temp_input_file):
            os.remove(temp_input_file)
        # Note: We don't clean up temp_dir here because FileResponse needs the file
        # The file will be cleaned up after the response is sent

@app.post("/text-to-speech-base64")
async def text_to_speech_base64(request: TTSRequest):
    """
    Convert text to speech and return as base64 encoded string.
    Useful for systems that can't handle file downloads.
    
    Args:
        request: TTSRequest containing text, model name, and output format
    
    Returns:
        JSON with base64 encoded audio data
    """
    temp_dir = None
    temp_input_file = None
    temp_output_file = None
    final_output_file = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Check if Piper exists
        if not os.path.exists(PIPER_PATH):
            raise HTTPException(status_code=500, detail=f"Piper executable not found at {PIPER_PATH}")
        
        # Check if model exists
        model_file = os.path.join(MODEL_PATH, f"{request.model}.onnx")
        if not os.path.exists(model_file):
            raise HTTPException(status_code=400, detail=f"Model file not found: {model_file}")
        
        # Create temporary input text file
        temp_input_file = os.path.join(temp_dir, f"{uuid.uuid4()}.txt")
        with open(temp_input_file, 'w', encoding='utf-8') as f:
            f.write(request.text)
        
        # Generate output filename
        temp_output_file = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
        
        # Run Piper TTS
        cmd = [
            PIPER_PATH,
            "--model", model_file,
            "--output_file", temp_output_file,
            "--text_file", temp_input_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Piper TTS failed: {result.stderr}")
        
        # Read and encode the audio file
        with open(temp_output_file, 'rb') as f:
            audio_data = f.read()
        
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "success": True,
            "audio_data": audio_base64,
            "format": request.output_format,
            "model": request.model
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
    finally:
        # Cleanup temporary files
        if temp_input_file and os.path.exists(temp_input_file):
            os.remove(temp_input_file)
        if temp_output_file and os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.get("/models")
async def list_models():
    """List available TTS models"""
    try:
        models = []
        if os.path.exists(MODEL_PATH):
            for file in os.listdir(MODEL_PATH):
                if file.endswith('.onnx'):
                    models.append(file.replace('.onnx', ''))
        
        return {
            "success": True,
            "models": models,
            "default_model": DEFAULT_MODEL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    piper_available = os.path.exists(PIPER_PATH)
    models_available = os.path.exists(MODEL_PATH)
    
    return {
        "status": "healthy",
        "service": "piper-tts",
        "piper_available": piper_available,
        "models_available": models_available,
        "piper_path": PIPER_PATH,
        "model_path": MODEL_PATH
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)