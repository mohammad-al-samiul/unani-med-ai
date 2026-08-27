# Ollama Integration Guide for n8n Workflow

## Overview
এই গাইডে n8n workflow-এ Ollama LLM integration যোগ করার পদ্ধতি ব্যাখ্যা করা হয়েছে। এটি text এবং voice দুটি branch-এই কাজ করবে।

## Workflow Architecture

### Text Branch:
1. **Set Text Input** - User text message extract করে
2. **Call Ollama (Text)** - Ollama API কে call করে AI response নেয়
3. **Set Text Response** - AI response process করে
4. **Send Text to Messenger** - Messenger এ response পাঠায়

### Voice Branch:
1. **Set Voice Data** - Audio URL extract করে
2. **Call STT Service** - Whisper দিয়ে voice to text করে
3. **Set Voice Input** - Transcribed text prepare করে
4. **Call Ollama (Voice)** - Ollama API কে call করে AI response নেয়
5. **Set Voice Response** - AI response process করে
6. **Send Voice Response to Messenger** - Messenger এ response পাঠায়

## Ollama HTTP Request Node Configuration

### Call Ollama (Text) Node:

**বেসিক সেটিংস:**
- Method: POST
- URL: `http://localhost:11434/api/chat`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "model": "llama3.1:8b",
  "messages": [
    {
      "role": "system",
      "content": "তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও।"
    },
    {
      "role": "user",
      "content": "={{ $json.user_input }}"
    }
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

### Call Ollama (Voice) Node:

**বেসিক সেটিংস:**
- Method: POST
- URL: `http://localhost:11434/api/chat`
- Send Body: True
- Specify Body: JSON

**JSON Body:** (উপরের মতোই, কিন্তু voice input দিয়ে)
```json
{
  "model": "llama3.1:8b",
  "messages": [
    {
      "role": "system",
      "content": "তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও।"
    },
    {
      "role": "user",
      "content": "={{ $json.user_input }}"
    }
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

## Ollama API Parameters Explained:

### Model:
- `llama3.1:8b` - 8 billion parameter model, ভালো balance between speed and accuracy

### Messages:
- **System Message**: AI-এর behavior define করে (ইউনানী স্বাস্থ্য সহকারী)
- **User Message**: User input text (সরাসরি বা Whisper থেকে transcribed)

### Options:
- `stream: false` - Complete response একবারে পাবে (streaming নয়)
- `temperature: 0.7` - Creativity balance (0 = conservative, 1 = creative)
- `max_tokens: 500` - Maximum response length

## Prerequisites Check:

### ১. Ollama Running:
```powershell
# Ollama চালু আছে কিনা চেক করুন
curl http://localhost:11434/api/tags

# Model available কিনা চেক করুন
ollama list
```

### ২. Model Download:
```powershell
# যদি llama3.1:8b না থাকে
ollama pull llama3.1:8b
```

### ৩. Ollama API Test:
```powershell
# Direct API test
curl -X POST http://localhost:11434/api/chat `
  -H "Content-Type: application/json" `
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ],
    "stream": false
  }'
```

## n8n Workflow Import:

১. n8n ড্যাশবোর্ডে যান: http://localhost:5678
২. "Import from File" বাটনে ক্লিক করুন
৩. `facebook-messenger-webhook-workflow-with-ollama.json` ফাইল select করুন
৪. **গুরুত্বপূর্ণ কনফিগারেশন:**
   - `your_verify_token_here` কে আপনার actual verify token দিয়ে রিপ্লেস করুন
   - Facebook Messenger Auth credential সেটআপ করুন (Page Access Token)
   - Ollama URL চেক করুন (default: `http://localhost:11434`)
   - STT Service URL চেক করুন (default: `http://localhost:8001`)

## Docker Considerations:

যদি n8n Docker container-এ রান করে থাকে:

### Ollama Access:
```json
// Docker container থেকে Ollama access করতে
"url": "http://host.docker.internal:11434/api/chat"
```

### STT Service Access:
```json
// Docker container থেকে STT service access করতে  
"url": "http://host.docker.internal:8001/transcribe-url"
```

## Testing the Complete Flow:

### ১. Text Message Test:
- Facebook Messenger এ একটি text message পাঠান
- উদাহরণ: "আমার মাথা ব্যথা করছে, কি করব?"
- n8n execution log চেক করুন
- Messenger এ AI response পাবেন

### ২. Voice Message Test:
- Facebook Messenger এ একটি voice message পাঠান
- n8n execution log চেক করুন (STT → Ollama → Response)
- Messenger এ AI response পাবেন

## Response Format:

Ollama থেকে আসা response format:
```json
{
  "model": "llama3.1:8b",
  "created_at": "2024-08-26T00:00:00.000Z",
  "message": {
    "role": "assistant",
    "content": "AI response text here..."
  },
  "done": true
}
```

n8n-এ আমরা `$json.message.content` extract করে Messenger এ পাঠাচ্ছি।

## System Prompt Explanation:

**বাংলা System Prompt:**
```
"তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও।"
```

**Purpose:**
- AI-কে ইউনানী স্বাস্থ্য সহকারী হিসেবে define করে
- Medical advice দেওয়ার limitation সেট করে
- Serious cases-এ real hakim/doctor দেখানোর পরামর্শ দিতে বাধ্য করে

## Troubleshooting:

### Ollama Connection Failed:
- Ollama running আছে কিনা চেক করুন: `ollama serve`
- Port 11434 open আছে কিনা চেক করুন
- Docker container হলে `host.docker.internal` ব্যবহার করুন

### Model Not Found:
- Model properly installed আছে কিনা চেক করুন: `ollama list`
- Model name correct কিনা চেক করুন

### Slow Response:
- Model size কমানোর চেষ্টা করুন (llama3.1:8b → tinyllama)
- Max tokens কমানোর চেষ্টা করুন
- Ollama GPU acceleration enable করুন (যদি available থাকে)

### Bengali Text Issues:
- Model properly support করে কিনা চেক করুন
- System prompt বাংলায় দেওয়ায় response বাংলায় আসবে

## Next Steps (Phase 2):

এই সফল integration এর পর:
- RAG system যোগ করা (ChromaDB + nomic-embed-text)
- Piper TTS দিয়ে voice response generation
- উন্নত error handling ও logging
- Context management for conversations