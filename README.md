# UnaniMed AI

Facebook Messenger-এর জন্য তৈরি একটি Unani healthcare assistant। এটি n8n workflow-এর মাধ্যমে text ও voice message গ্রহণ করে, safety checks চালায়, patient profile ব্যবহার করে এবং প্রয়োজন হলে Unani বইয়ের তথ্য ও Ollama LLM-এর সাহায্যে উত্তর তৈরি করে।

> **গুরুত্বপূর্ণ:** এটি চিকিৎসকের বিকল্প নয়। উচ্চ-ঝুঁকির উপসর্গ, জরুরি অবস্থা বা dosage সংক্রান্ত সিদ্ধান্তে ব্যবহারকারীকে qualified healthcare professional-এর কাছে পাঠাতে হবে। Production ব্যবহারের আগে পুরো safety flow পরীক্ষা করুন।

## কী কী আছে

- Facebook Messenger webhook integration
- বাংলা text ও voice input
- Faster-Whisper ভিত্তিক Speech-to-Text
- Piper ভিত্তিক Text-to-Speech
- Pre-check ও post-check safety filtering
- Patient profile-এর জন্য SQLite storage
- ChromaDB-ভিত্তিক RAG
- Ollama local LLM integration
- Semantic response cache
- Retry, backup এবং monitoring workflow

## Architecture

```text
Facebook Messenger
        |
        v
      n8n
   /    |    \
 STT  Safety  Profile
        |
   Cache -> RAG/ChromaDB -> Ollama
        |
   Safety post-check
        |
 Messenger response / TTS
```

## Repository structure

```text
unani-med-ai/
├── src/                         # Services, configuration ও utilities
├── scripts/                     # Book processing, backup ও startup scripts
├── workflows/                   # n8n workflow JSON files
├── data/                        # Books ও local databases
├── chromadb_persist/            # ChromaDB persistent storage
├── docs/                        # বিস্তারিত setup ও operation guides
├── requirements.txt
└── Modelfile
```

## Service ports

| Service | Port | Purpose |
|---|---:|---|
| n8n | 5678 | Workflow orchestration |
| ChromaDB | 8000 | Vector database |
| STT | 8001 | Voice-to-text |
| TTS | 8002 | Text-to-speech |
| Patient Profile | 8003 | Patient data ও conversation profile |
| Safety Check | 8004 | Risk ও dosage filtering |
| Semantic Cache | 8005 | Similar response cache |
| Ollama | 11434 | Local LLM ও embeddings |

## Prerequisites

- Windows এবং Python 3.10 বা পরের version
- Node.js এবং npm
- Ollama
- Docker, যদি ChromaDB container হিসেবে চালান
- Facebook Developer App ও একটি Facebook Page
- Public HTTPS endpoint, যেমন Cloudflare Tunnel বা ngrok

Python dependencies ইনস্টল করুন:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ollama model প্রস্তুত করুন:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Local services চালু করা

প্রথমে Ollama ও ChromaDB চালু আছে কি না নিশ্চিত করুন। তারপর project directory থেকে:

```powershell
.\scripts\start_all_services.bat
```

বন্ধ করতে:

```powershell
.\scripts\stop_all_services.bat
```

Health check:

```powershell
Invoke-WebRequest http://localhost:8001/health
Invoke-WebRequest http://localhost:8002/health
Invoke-WebRequest http://localhost:8003/health
Invoke-WebRequest http://localhost:8004/health
Invoke-WebRequest http://localhost:8005/health
```

## n8n workflow setup

1. n8n চালু করুন:

   ```powershell
   npx n8n start
   ```

2. ব্রাউজারে `http://localhost:5678` খুলুন।
3. **Workflows → Import from File** নির্বাচন করুন।
4. শুরু করার জন্য import করুন:

   `workflows/facebook-messenger-webhook-workflow-safety.json`

5. **IF Webhook Verification** node-এ নিজের একটি `VERIFY_TOKEN` বসান। এটি Page Access Token নয়।
6. Workflow save করে activate করুন।

### Facebook webhook verification

Safety workflow-তে GET এবং POST দুটোই `webhook` path ব্যবহার করে। তাই n8n-এর Production URL সাধারণত হবে:

```text
https://YOUR_PUBLIC_DOMAIN/webhook/webhook
```

Facebook Developer Dashboard-এ যান:

**App → Messenger → Webhooks → Add Callback URL**

```text
Callback URL: https://YOUR_PUBLIC_DOMAIN/webhook/webhook
Verify Token: n8n workflow-এ দেওয়া একই VERIFY_TOKEN
```

এরপর **Verify and Save** চাপুন এবং Page-এর `messages` subscription চালু করুন। Facebook `localhost`-এ পৌঁছাতে পারে না, তাই public HTTPS URL আবশ্যক।

Local verification test:

```powershell
Invoke-WebRequest "http://localhost:5678/webhook/webhook?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test123"
```

সফল হলে response হবে `test123`।

## Secret ও credential policy

নিচের secret কখনও source file, README, chat বা git repository-তে রাখবেন না:

- Facebook Page Access Token
- Telegram Bot Token ও Chat ID
- n8n password, encryption key বা tunnel token

n8n-এ Facebook credential তৈরি করুন:

**Credentials → New Credential → HTTP Header Auth**

```text
Name: Facebook Messenger Auth
Header Name: Authorization
Header Value: Bearer YOUR_FACEBOOK_PAGE_ACCESS_TOKEN
```

Token-এর জায়গায় আসল token শুধু n8n credential store-এ বসাবেন।

## Docker network note

n8n যদি Docker container-এর ভিতরে চলে, তাহলে `localhost` আপনার Windows host নয়, container-কে বোঝায়। প্রয়োজন হলে service URL-এ ব্যবহার করুন:

```text
http://host.docker.internal:8000
http://host.docker.internal:8001
http://host.docker.internal:8002
http://host.docker.internal:8003
http://host.docker.internal:8004
http://host.docker.internal:8005
http://host.docker.internal:11434
```

## RAG বই প্রস্তুত করা

1. Unani বই `data/books/` directory-তে রাখুন।
2. [Book Processing Guide](docs/BOOK_PROCESSING_GUIDE.md) অনুসরণ করুন।
3. Processed chunks ChromaDB-তে load করুন।
4. Workflow-এ collection name ও ChromaDB URL যাচাই করুন।

Default collection হিসেবে `unani_books` ব্যবহার করা হয়, তবে workflow ও database-এর নাম একই হতে হবে।

## Current limitation

বর্তমান safety workflow TTS output তৈরি করে, কিন্তু Messenger-এ audio attachment পাঠানোর বদলে একটি text placeholder পাঠায়। Text response flow কার্যকর; প্রকৃত voice reply চালু করতে audio hosting/upload ধাপ আলাদাভাবে সম্পূর্ণ করতে হবে।

## Backup ও maintenance

Manual backup:

```powershell
python .\scripts\backup_script.py
```

প্রস্তাবিত routine:

- প্রতিদিন: service health, error log ও backup যাচাই
- প্রতি সপ্তাহে: cache hit rate ও workflow executions পরীক্ষা
- প্রতি মাসে: পুরোনো cache, database ও configuration review

## Documentation

- [Safety Check Guide](docs/SAFETY_CHECK_GUIDE.md)
- [RAG Integration Guide](docs/RAG_INTEGRATION_GUIDE.md)
- [Ollama Integration Guide](docs/OLLAMA_INTEGRATION_GUIDE.md)
- [STT Setup Guide](docs/STT_SETUP_GUIDE.md)
- [TTS Setup Guide](docs/TTS_SETUP_GUIDE.md)
- [Patient Profile Guide](docs/PATIENT_PROFILE_GUIDE.md)
- [Go-live Checklist](docs/GO_LIVE_CHECKLIST.md)
- [Optimization Guide](docs/OPTIMIZATION_GUIDE.md)

## Troubleshooting

- n8n থেকে service call ব্যর্থ হলে আগে সংশ্লিষ্ট `/health` endpoint পরীক্ষা করুন।
- Facebook verification ব্যর্থ হলে callback URL, `VERIFY_TOKEN`, workflow activation এবং public HTTPS endpoint মিলিয়ে দেখুন।
- Docker ব্যবহার করলে `localhost`-এর বদলে `host.docker.internal` প্রয়োজন কি না পরীক্ষা করুন।
- Ollama response না এলে model নাম ও Ollama service status যাচাই করুন।
- RAG ফলাফল না এলে ChromaDB চালু আছে কি না এবং collection-এ processed chunks আছে কি না পরীক্ষা করুন।

## License and responsibility

এই repository-এর code clinical diagnosis, emergency response বা prescription-এর বিকল্প নয়। বাস্তব ব্যবহার, data retention, access control এবং medical review-এর দায়িত্ব deployment team-এর।
