# Patient Profile Management Guide

## Overview
এই গাইডে n8n workflow-এ patient profile management system ব্যাখ্যা করা হয়েছে যা SQLite database ব্যবহার করে user profiling এবং context-aware responses provide করে।

## Patient Profile Service Architecture

### Database Schema:
```sql
CREATE TABLE patients (
    sender_id TEXT PRIMARY KEY,
    age_range TEXT,
    gender TEXT,
    is_pregnant BOOLEAN,
    prior_conditions TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE conversation_state (
    sender_id TEXT PRIMARY KEY,
    current_step TEXT,
    collected_data TEXT,
    started_at TIMESTAMP,
    last_activity TIMESTAMP
);
```

### Profile Collection Flow:
```
User Message → Check Profile → No Profile → Start Conversation Flow
Age Question → Gender Question → Pregnancy Check → Prior Conditions → Complete
```

## Patient Profile Service (FastAPI)

### File: `patient_profile_service.py`

### API Endpoints:

#### ১. POST `/check-profile`
Check if profile exists for sender_id.

**Request:**
```json
{
  "sender_id": "123456789"
}
```

**Response:**
```json
{
  "exists": true,
  "profile": {
    "sender_id": "123456789",
    "age_range": "26-35",
    "gender": "মহিলা",
    "is_pregnant": false,
    "prior_conditions": "কোনো নেই",
    "created_at": "2024-08-26T10:00:00",
    "updated_at": "2024-08-26T10:00:00"
  }
}
```

#### ২. POST `/start-profile-flow`
Start profile collection conversation flow.

**Request:**
```json
{
  "sender_id": "123456789"
}
```

**Response:**
```json
{
  "status": "started",
  "current_step": "age_range",
  "question": "আপনার বয়স কত? (উদাহরণ: ১৮-২৫, ২৬-৩৫, ৩৬-৪৫, ৪৬-৫৫, ৪৬+)"
}
```

#### ৩. POST `/process-answer`
Process user answer in profile collection flow.

**Request:**
```json
{
  "sender_id": "123456789",
  "answer": "26-35"
}
```

**Response:**
```json
{
  "status": "continue",
  "question": "আপনার লিঙ্গ কি? (পুরুষ/মহিলা/অন্যান্য)",
  "current_step": "gender"
}
```

#### ৪. POST `/get-conversation-state`
Get current conversation state.

**Request:**
```json
{
  "sender_id": "123456789"
}
```

**Response:**
```json
{
  "current_step": "gender",
  "collected_data": {
    "age_range": "26-35"
  },
  "started_at": "2024-08-26T10:00:00",
  "last_activity": "2024-08-26T10:01:00"
}
```

#### ৫. POST `/format-patient-context`
Format patient profile for RAG context.

**Request:**
```json
{
  "sender_id": "123456789"
}
```

**Response:**
```json
{
  "context": "বয়স: 26-35 | লিঙ্গ: মহিলা | গর্ভাবস্থা: গর্ভবতী নন | পূর্ববর্তী রোগ: কোনো নেই"
}
```

## Conversation Flow Questions

### Step 1: Age Range
**Question:** "আপনার বয়স কত? (উদাহরণ: ১৮-২৫, ২৬-৩৫, ৩৬-৪৫, ৪৬-৫৫, ৪৬+)"
**Next Step:** gender
**Field:** age_range

### Step 2: Gender
**Question:** "আপনার লিঙ্গ কি? (পুরুষ/মহিলা/অন্যান্য)"
**Next Step:** pregnancy_check
**Field:** gender

### Step 3: Pregnancy Check (Conditional)
**Question:** "আপনি কি বর্তমানে গর্ভবতী? (হ্যাঁ/না)"
**Next Step:** prior_conditions
**Field:** is_pregnant
**Note:** Skipped for male users

### Step 4: Prior Conditions
**Question:** "আপনার কোনো পূর্ববর্তী রোগ আছে কি? (যদি থাকে লিখুন, না থাকলে 'না' লিখুন)"
**Next Step:** complete
**Field:** prior_conditions

## n8n Workflow Integration

### Profile Check Flow:
```
Webhook POST → Extract Message Data → Check Patient Profile → IF Profile Exists
├─ Yes → Switch Message Type → Main RAG Flow
└─ No → Get Conversation State → IF Conversation Active
    ├─ Active → Process Profile Answer → Continue/Complete
    └─ Not Active → Start Profile Flow → First Question
```

### Key n8n Nodes:

#### ১. **Check Patient Profile**
- Method: POST
- URL: `http://localhost:8003/check-profile`
- JSON Body: `{"sender_id": "={{ $json.sender_id }}"}`

#### ২. **IF Profile Exists**
- Condition: `$json.exists == true`
- True: Main RAG flow
- False: Profile collection flow

#### ৃ. **Get Conversation State**
- Method: POST
- URL: `http://localhost:8003/get-conversation-state`
- JSON Body: `{"sender_id": "={{ $json.sender_id }}"}`

#### ৪. **IF Conversation Active**
- Condition: `$json.current_step` is not empty
- True: Process answer
- False: Start new flow

#### ৫. **Process Profile Answer**
- Method: POST
- URL: `http://localhost:8003/process-answer`
- JSON Body: `{"sender_id": "={{ $json.sender_id }}", "answer": "={{ $json.content }}"}`

#### ৬. **IF Profile Complete**
- Condition: `$json.status == "complete"`
- True: Completion message
- False: Next question

#### ৭. **Format Patient Context (Text/Voice)**
- Method: POST
- URL: `http://localhost:8003/format-patient-context`
- JSON Body: `{"sender_id": "={{ $json.sender_id }}"}`

## Enhanced RAG Integration

### Updated Augmented Prompt Template:
```
[PATIENT CONTEXT]: বয়স: 26-35 | লিঙ্গ: মহিলা | গর্ভাবস্থা: গর্ভবতী নন | পূর্ববর্তী রোগ: কোনো নেই

নিচের রেফারেন্স অংশগুলো ব্যবহার করে প্রশ্নের উত্তর দাও। রেফারেন্সে না থাকলে অনুমান করে বানিয়ে বোলো না, বরং জানাও যে এই বিষয়ে নির্দিষ্ট তথ্য নেই:

[Book Name - Page X]:
chunk content 1

[Book Name - Page Y]:
chunk content 2

প্রশ্ন: user_question
```

### Updated System Prompt:
```
"তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও। তুমি শুধুমাত্র প্রদত্ত রেফারেন্স বইয়ের অংশ থেকে তথ্য ব্যবহার করবে। রেফারেন্সে না থাকলে অনুমান করে উত্তর দেবে না। পেশেন্টের প্রোফাইল তথ্য বিবেচনা করে উত্তর দেবে।"
```

## Setup Instructions

### ১. Patient Profile Service Setup:
```powershell
cd C:\Users\Admin\Documents\dev\office-dev\unani-med-ai
.\venv\Scripts\activate

# Dependencies install করুন
pip install fastapi uvicorn

# Service রান করুন
python patient_profile_service.py
```

Service `http://localhost:8003`-এ রান করবে।

### ২. n8n Workflow Import:
```powershell
# n8n ড্যাশবোর্ডে যান
# facebook-messenger-webhook-workflow-final.json import করুন
# Configuration আপডেট করুন
```

### ৩. Service URLs Configuration:
- Patient Profile Service: `http://localhost:8003`
- STT Service: `http://localhost:8001`
- TTS Service: `http://localhost:8002`
- Ollama: `http://localhost:11434`
- ChromaDB: `http://localhost:8000`

## Testing the Complete Flow

### নতুন User (No Profile):
```
User: "মাথা ব্যথার জন্য কি করব?"

Bot: "আপনার বয়স কত? (উদাহরণ: ১৮-২৫, ২৬-৩৫, ৩৬-৪৫, ৪৬-৫৫, ৪৬+)"

User: "26-35"

Bot: "আপনার লিঙ্গ কি? (পুরুষ/মহিলা/অন্যান্য)"

User: "মহিলা"

Bot: "আপনি কি বর্তমানে গর্ভবতী? (হ্যাঁ/না)"

User: "না"

Bot: "আপনার কোনো পূর্ববর্তী রোগ আছে কি? (যদি থাকে লিখুন, না থাকলে 'না' লিখুন)"

User: "না"

Bot: "আপনার প্রোফাইল সফলভাবে সেভ হয়েছে। এখন আপনি আপনার স্বাস্থ্য সমস্যা সম্পর্কে জিজ্ঞেস করতে পারেন।"

User: "মাথা ব্যথার জন্য কি করব?"

Bot: [RAG response with patient context consideration]
```

### Existing User (Profile Exists):
```
User: "মাথা ব্যথার জন্য কি করব?"

Bot: [Direct RAG response with patient context]
```

## Database Management

### View Profiles:
```python
# SQLite browser দিয়ে patient_profiles.db ফাইল ওপেন করুন
# অথবা Python script দিয়ে
import sqlite3
conn = sqlite3.connect('patient_profiles.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM patients")
print(cursor.fetchall())
conn.close()
```

### Reset Profile:
```python
# Individual user reset
cursor.execute("DELETE FROM patients WHERE sender_id = ?", (sender_id,))

# All profiles reset
cursor.execute("DELETE FROM patients")
```

### Backup Database:
```powershell
# Database file backup করুন
copy patient_profiles.db patient_profiles_backup.db
```

## Advanced Features

### ১. Profile Update:
Existing users can update their profile by restarting the collection flow.

### ২. Context-Aware Responses:
LLM considers patient demographics and medical history in responses.

### ৩. Conditional Questions:
Pregnancy question only asked to female users.

### ৪. Data Privacy:
All patient data stored locally in SQLite database.

## Troubleshooting

### Service Not Running:
```powershell
# Check if service is running
curl http://localhost:8003/health

# Restart service
python patient_profile_service.py
```

### Database Locked:
```powershell
# Check for multiple service instances
# Only one instance should run at a time
```

### Profile Not Saving:
```python
# Check database permissions
# Ensure write access to patient_profiles.db
```

### Conversation State Issues:
```python
# Reset stuck conversation states
cursor.execute("DELETE FROM conversation_state")
```

## Privacy and Security

### Data Protection:
- All patient data stored locally
- No cloud transmission of personal health information
- SQLite file can be encrypted if needed

### Compliance:
- HIPAA considerations for healthcare applications
- Data retention policies can be implemented
- Patient consent mechanisms can be added

## Future Enhancements

### ১. Advanced Profile Fields:
- Allergies
- Current medications
- Lifestyle factors
- Family medical history

### ২. Profile Analytics:
- Common demographics analysis
- Treatment effectiveness tracking
- Health outcome monitoring

### ৩. Integration Features:
- Appointment scheduling
- Reminders and follow-ups
- Health education content

This patient profile system enables personalized, context-aware health responses while maintaining privacy and data security.