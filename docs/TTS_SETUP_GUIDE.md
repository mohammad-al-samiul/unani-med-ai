# Piper TTS Integration Guide

## Overview
এই গাইডে Piper TTS wrapper service এবং n8n workflow-এ voice response integration ব্যাখ্যা করা হয়েছে।

## Piper TTS Service Architecture

### তৈরি করা ফাইল:
- `tts_service.py` - FastAPI wrapper service for Piper TTS

### API Endpoints:

#### ১. POST `/text-to-speech`
Text থেকে audio file generate করে এবং file download করে।

**Request Body:**
```json
{
  "text": "Hello, this is a test",
  "model": "en_US-lessac-medium",
  "output_format": "ogg"
}
```

**Response:** Audio file (যেমন .ogg, .mp3, .wav)

#### ২. POST `/text-to-speech-base64`
Text থেকে audio generate করে base64 encoded string হিসেবে রিটার্ন করে।

**Request Body:** উপরের মতোই

**Response:**
```json
{
  "success": true,
  "audio_data": "base64_encoded_audio_string",
  "format": "mp3",
  "model": "en_US-lessac-medium"
}
```

#### ৩. GET `/models`
Available TTS models list করে।

#### ৪. GET `/health`
Service health check করে।

## Piper TTS Configuration

### Path Configuration (tts_service.py-এ):
```python
PIPER_PATH = r"C:\piper-tts\piper.exe"  # Piper executable path
MODEL_PATH = r"C:\piper-tts\models"     # Models directory
DEFAULT_MODEL = "en_US-lessac-medium"   # Default voice model
```

### গুরুত্বপূর্ণ: আপনার paths আপডেট করুন:
- `PIPER_PATH` - আপনার Piper executable এর actual path
- `MODEL_PATH` - আপনার voice models যেখানে আছে
- `DEFAULT_MODEL` - আপনার preferred voice model

## Setup Steps:

### ১. Piper TTS ইনস্টল চেক:
```powershell
# Piper executable path চেক করুন
Test-Path "C:\piper-tts\piper.exe"

# Models directory চেক করুন
Get-ChildItem "C:\piper-tts\models"
```

### ২. ভার্চুয়াল এনভায়রনমেন্ট সেটআপ:
```powershell
cd C:\Users\Admin\Documents\dev\office-dev\unani-med-ai
.\venv\Scripts\activate
```

### ৩. TTS Service রান করা:
```powershell
python tts_service.py
```

Service `http://localhost:8002`-এ রান করবে।

### ৪. Service টেস্ট করা:
```powershell
# Health check
curl http://localhost:8002/health

# Available models চেক করা
curl http://localhost:8002/models

# TTS test
curl -X POST http://localhost:8002/text-to-speech-base64 `
  -H "Content-Type: application/json" `
  -d '{"text": "Hello, this is a test", "model": "en_US-lessac-medium", "output_format": "mp3"}'
```

## n8n Workflow Update

### Voice Branch এ TTS Integration:

**পুরো Voice Flow:**
1. Set Voice Data → Call STT Service → Set Voice Input → Call Ollama (Voice) → Set Voice Response → Call TTS Service → Set TTS Result → Send Audio Placeholder to Messenger

### নতুন নোড কনফিগারেশন:

#### ১. **Set Voice Response** (আপডেটেড)
- `ai_response`: AI response text
- `sender_id`: Original sender ID
- `tts_text`: Text to convert to speech

#### ২. **Call TTS Service**
**বেসিক সেটিংস:**
- Method: POST
- URL: `http://localhost:8002/text-to-speech-base64`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "text": "={{ $json.tts_text }}",
  "model": "en_US-lessac-medium",
  "output_format": "mp3"
}
```

#### ৩. **Set TTS Result**
- `audio_base64`: Base64 encoded audio data
- `audio_format`: Audio format (mp3/ogg/wav)
- `sender_id`: Original sender ID

#### ৪. **Send Audio Placeholder to Messenger**
**বেসিক সেটিংস:**
- Method: POST
- URL: `https://graph.facebook.com/v18.0/me/messages`
- Authentication: Facebook Messenger Auth

**JSON Body:**
```json
{
  "recipient": { "id": "={{ $json.sender_id }}" },
  "message": {
    "text": "Voice response generated. Please check text response for details."
  }
}
```

## টেক্সট Branch (অপরিবর্তিত):

Text branch আগের মতোই কাজ করবে - সরাসরি text response পাঠাবে।

## Complete Workflow Logic:

### Text Message:
```
User Text → Set Text Input → Ollama → Set Text Response → Send Text to Messenger
```

### Voice Message:
```
User Voice → Set Voice Data → STT Service → Set Voice Input → Ollama → Set Voice Response → TTS Service → Set TTS Result → Send Audio Placeholder to Messenger
```

## Messenger Audio Upload সমস্যা সমাধান:

Facebook Messenger API সরাসরি base64 audio upload support করে না। সমাধান:

### অপশন ১: Public URL Upload (প্রস্তাবিত)
একটি temporary file server ব্যবহার করুন:

```python
# tts_service.py-এ একটি endpoint যোগ করুন
@app.post("/text-to-speech-url")
async def text_to_speech_url(request: TTSRequest):
    # Generate audio file
    # Save to public directory
    # Return public URL
    return {"audio_url": "https://your-server.com/audio/temp.mp3"}
```

### অপশন ২: Facebook Attachment Upload API
Facebook এর attachment upload API ব্যবহার করুন:

```json
{
  "recipient": { "id": "USER_ID" },
  "message": {
    "attachment": {
      "type": "audio", 
      "payload": {
        "url": "https://your-public-audio-url.com/audio.mp3"
      }
    }
  }
}
```

### অপশন ৩: Temporary Solution (বর্তমান workflow)
আপাতত text message পাঠানো হচ্ছে যে voice generated হয়েছে।

## Testing:

### ১. TTS Service Test:
```powershell
# Service রান করুন
python tts_service.py

# Separate terminal-এ test করুন
curl -X POST http://localhost:8002/text-to-speech-base64 `
  -H "Content-Type: application/json" `
  -d '{"text": "আপনার মাথা ব্যথা করলে বিশ্রাম নিন", "model": "en_US-lessac-medium", "output_format": "mp3"}'
```

### ২. n8n Workflow Test:
১. n8n ড্যাশবোর্ডে আপডেটেড workflow import করুন
২. Voice message পাঠান
৩. Execution log চেক করুন (STT → Ollama → TTS → Response)
৪. Messenger এ response পাবেন

## Docker Considerations:

যদি n8n Docker container-এ রান করে থাকে:

```json
// TTS service access
"url": "http://host.docker.internal:8002/text-to-speech-base64"
```

## Troubleshooting:

### Piper Path Issues:
- `PIPER_PATH` correct কিনা চেক করুন
- Piper executable properly installed আছে কিনা চেক করুন
- Windows path format correct কিনা চেক করুন

### Model Issues:
- Model files properly downloaded আছে কিনা চেক করুন
- Model filename correct কিনা চেক করুন (.onnx extension)
- `MODEL_PATH` correct কিনা চেক করুন

### Audio Format Issues:
- ffmpeg installed আছে কিনা চেক করুন (mp3/ogg conversion এর জন্য)
- যদি ffmpeg না থাকে, service WAV format রিটার্ন করবে

### Service Connection:
- Port 8002 available কিনা চেক করুন
- Service properly running আছে কিনা চেক করুন
- Firewall settings চেক করুন

## Next Steps:

### Voice Response Improvement:
- Audio file hosting solution implement করা
- Facebook attachment upload API properly use করা
- Bengali voice model add করা (যদি available থাকে)

### Performance:
- Audio caching implement করা
- Queue system for TTS requests
- Async processing for long texts

### Quality:
- Better voice models experiment করা
- Audio post-processing (noise reduction, normalization)
- Multiple voice options provide করা