# STT সার্ভিস সেটআপ গাইড

## FastAPI STT মাইক্রোসার্ভিস

### ফাইল স্ট্রাকচার:
- `stt_service.py` - FastAPI মাইক্রোসার্ভিস
- `requirements.txt` - Python dependencies

### সেটআপ ধাপ:

১. **ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও এক্টিভেট:**
```powershell
cd C:\Users\Admin\Documents\dev\office-dev\unani-med-ai
python -m venv venv
.\venv\Scripts\activate
```

২. **Dependencies ইনস্টল:**
```powershell
pip install -r requirements.txt
```

৩. **সার্ভিস রান করা:**
```powershell
python stt_service.py
```

সার্ভিস `http://localhost:8001`-এ রান করবে।

### API এন্ডপয়েন্ট:

#### ১. POST `/transcribe-url`
Audio URL থেকে transcription করে।

**Request Body:**
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "language": "bn"  // অপশনাল - null দিলে auto-detect হবে
}
```

**Response:**
```json
{
  "success": true,
  "text": "transcribed text here",
  "detected_language": "bn",
  "language_probability": 0.95,
  "segments_count": 5
}
```

#### ২. POST `/transcribe-file`
Uploaded audio file থেকে transcription করে।

**Request:** Multipart form data with audio file

**Response:** উপরের মতো একই format

#### ৩. GET `/health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "speech-to-text"
}
```

## n8n Workflow আপডেট

### নতুন নোড যোগ করা হয়েছে:

১. **Set Voice Data** - Voice branch-এ audio URL ও sender ID extract করে
২. **Call STT Service** - FastAPI সার্ভিসকে call করে transcription এর জন্য
৩. **Set STT Result** - Transcription result process করে response text তৈরি করে

### HTTP Request নোড কনফিগারেশন (Call STT Service):

**বেসিক সেটিংস:**
- Method: POST
- URL: `http://localhost:8001/transcribe-url`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "audio_url": "={{ $json.audio_url }}",
  "language": null
}
```

**অপশনাল সেটিংস:**
- Timeout: 300 seconds (বড় audio files এর জন্য)
- Response Format: JSON

### n8n-এ Workflow Import করা:

১. n8n ড্যাশবোর্ডে যান: http://localhost:5678
২. "Import from File" বাটনে ক্লিক করুন
৩. `facebook-messenger-webhook-workflow-with-stt.json` ফাইল select করুন
৪. **গুরুত্বপূর্ণ কনফিগারেশন:**
   - `your_verify_token_here` কে আপনার actual verify token দিয়ে রিপ্লেস করুন
   - Facebook Messenger Auth credential সেটআপ করুন (Page Access Token)
   - STT Service URL চেক করুন (default: `http://localhost:8001`)

## টেস্টিং

### ১. STT সার্ভিস টেস্ট:
```powershell
# Health check
curl http://localhost:8001/health

# Transcription test (curl দিয়ে)
curl -X POST http://localhost:8001/transcribe-url `
  -H "Content-Type: application/json" `
  -d "{\"audio_url\": \"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3\", \"language\": null}"
```

### ২. n8n Workflow টেস্ট:
১. n8n ড্যাশবোর্ডে workflow টি active করুন
২. Facebook Messenger থেকে একটি voice message পাঠান
৩. n8n execution log চেক করুন
৪. Messenger এ response পাবেন: "আপনার ভয়েস মেসেজ পেয়েছি: [transcribed text] (ভাষা: [detected language])"

## ট্রাবলশুটিং

### STT সার্ভিস চালু হচ্ছে না:
- চেক করুন port 8001 অন্য কোনো সার্ভিস ব্যবহার করছে কিনা
- Python dependencies সঠিকভাবে ইনস্টল হয়েছে কিনা চেক করুন
- faster-whisper model প্রথমবার download হতে পারে, তাই ধৈর্য ধরুন

### n8n থেকে STT service call ব্যর্থ হচ্ছে:
- STT service ঠিকমতো রান হচ্ছে কিনা চেক করুন (`http://localhost:8001/health`)
- n8n Docker container থেকে localhost access পাচ্ছে কিনা চেক করুন
- Docker container এর জন্য URL পরিবর্তন করতে হতে পারে: `http://host.docker.internal:8001`

### Facebook audio URL থেকে download ব্যর্থ হচ্ছে:
- Facebook audio URLs expire হয়ে যেতে পারে
- Access token সঠিক কিনা চেক করুন
- Audio file format supported কিনা চেক করুন (mp3, wav, m4a supported)

## পরবর্তী ধাপ (Phase 2):

Voice branch সফলভাবে কাজ করলে পরবর্তী ধাপে:
- Transcribed text কে Ollama LLM-এ পাঠানো
- AI response generate করা
- Piper TTS দিয়ে voice response generate করা
- Messenger এ voice file পাঠানো