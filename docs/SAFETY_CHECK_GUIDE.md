# Safety Check System Guide

## Overview
এই গাইডে n8n workflow-এ safety check system ব্যাখ্যা করা হয়েছে যা medical AI responses-এর জন্য pre-check এবং post-check filtering provide করে।

## Safety Check Service

### File: `safety_check_service.py`
- FastAPI service on port 8004
- Configurable keyword and regex patterns
- Pre-check for high-risk queries
- Post-check for dosage information filtering

### Configuration File: `safety_config.json`

#### Pre-Check Keywords:
```json
{
  "pregnancy_complications": ["গর্ভাবস্থা জটিলতা", "গর্ভনিরোধক", "miscarriage"],
  "severe_pain": ["তীব্র ব্যথা", "অসহনীয় ব্যথা", "unbearable pain"],
  "breathing_difficulty": ["শ্বাসকষ্ট", "shortness of breath", "choking"],
  "consciousness_loss": ["জ্ঞান হারানো", "fainting", "unconscious"],
  "child_related": ["শিশু", "বাচ্চা", "child", "baby", "infant"],
  "medication_interaction": ["ওষুধ মিথস্ক্রিয়া", "drug interaction"]
}
```

#### Post-Check Regex Patterns:
```json
{
  "dosage_patterns": [
    "\\d+\\s*(গ্রাম|মিলিগ্রাম|মিলি|এমজি|ট্যাবলেট|চামচ)",
    "\\d+\\s*-\\s*\\d+\\s*(গ্রাম|মিলিগ্রাম|মিলি)",
    "\\d+\\s*times\\s*a\\s*day",
    "take\\s+\\d+\\s*(গ্রাম|মিলিগ্রাম|ট্যাবলেট)"
  ],
  "specific_medication": [
    "paracetamol\\s*\\d+\\s*mg",
    "ibuprofen\\s*\\d+\\s*mg",
    "antibiotic\\s*\\d+\\s*(গ্রাম|মিলিগ্রাম)"
  ],
  "frequency_patterns": [
    "প্রতি\\s*\\d+\\s*ঘন্টা",
    "every\\s*\\d+\\s*hours",
    "সকাল\\s*ও\\s*সন্ধ্যা"
  ]
}
```

## n8n Workflow Integration

### Safety Check Flow:

#### Text Branch:
```
Set Text Input → Safety Pre-Check → IF Should Block
├─ Yes → Set Block Response → Send to Messenger
└─ No → Embed Question → RAG Flow → LLM → Safety Post-Check → IF Should Modify
    ├─ Yes → Set Safe Response → Send to Messenger
    └─ No → Set Original Response → Send to Messenger
```

#### Voice Branch:
```
Set Voice Input → Safety Pre-Check → IF Should Block
├─ Yes → Set Block Response → Send to Messenger
└─ No → Embed Question → RAG Flow → LLM → Safety Post-Check → IF Should Modify
    ├─ Yes → Set Safe Response → TTS → Send to Messenger
    └─ No → Set Original Response → TTS → Send to Messenger
```

### Key n8n Nodes:

#### ১. **Safety Pre-Check (Text/Voice)**
- Method: POST
- URL: `http://localhost:8004/pre-check`
- JSON Body: `{"text": "user_input"}`

**Response:**
```json
{
  "should_block": true,
  "found_keywords": ["তীব্র ব্যথা"],
  "matched_categories": ["severe_pain"],
  "block_message": "এই বিষযে অনুগ্রহ করে সরাসরি একজন হাকিম/ডাক্তারের পরামর্শ নিন।",
  "reason": "Found 1 high-risk keywords in 1 categories"
}
```

#### ২. **IF Should Block (Text/Voice)**
- Condition: `$json.should_block == true`
- True: Send block message
- False: Continue to RAG flow

#### ৩. **Safety Post-Check (Text/Voice)**
- Method: POST
- URL: `http://localhost:8004/post-check`
- JSON Body: `{"text": "ai_response"}`

**Response:**
```json
{
  "should_modify": true,
  "found_patterns": [
    {
      "pattern": "\\d+\\s*(গ্রাম|মিলিগ্রাম)",
      "match": "500 মিলিগ্রাম",
      "start": 15,
      "end": 25
    }
  ],
  "modifications_made": 1,
  "original_text": "প্রতিদিন 500 মিলিগ্রাম খান...",
  "modified_text": "প্রতিদিন [ডোজ তথ্য সরিয়ে দেওয়া হয়েছে]...\n\nনোট: নির্দিষ্ট ডোজ বা পরিমাণ সম্পর্কে তথ্য সরিয়ে দেওয়া হয়েছে। ঔষধ সেবনের আগে অবশ্যই একজন হাকিম/ডাক্তারের পরামর্শ নিন।",
  "disclaimer_added": true
}
```

#### ৪. **IF Should Modify (Text/Voice)**
- Condition: `$json.should_modify == true`
- True: Use modified text with disclaimer
- False: Use original AI response

## Configuration Management

### Update Keywords:
```json
// safety_config.json-এ নতুন keywords যোগ করুন
{
  "pre_check_keywords": {
    "new_category": ["keyword1", "keyword2"]
  }
}
```

### Reload Configuration:
```powershell
# API call to reload config without restarting service
curl -X POST http://localhost:8004/reload-config
```

### Test Configuration:
```powershell
# Get current configuration
curl http://localhost:8004/config
```

## Testing Safety Checks

### Pre-Check Test:
```powershell
# High-risk query
curl -X POST http://localhost:8004/pre-check `
  -H "Content-Type: application/json" `
  -d '{"text": "আমার গর্ভাবস্থা জটিলতা হচ্ছে"}'

# Expected: should_block = true
```

### Post-Check Test:
```powershell
# Response with dosage information
curl -X POST http://localhost:8004/post-check `
  -H "Content-Type: application/json" `
  -d '{"text": "প্রতিদিন 500 মিলিগ্রাম প্যারাসিটামল খান"}'

# Expected: should_modify = true, dosage removed
```

## Setup Instructions

### ১. Safety Check Service Setup:
```powershell
cd C:\Users\Admin\Documents\dev\office-dev\unani-med-ai
.\venv\Scripts\activate

# Service রান করুন
python safety_check_service.py
```

Service `http://localhost:8004`-এ রান করবে।

### ২. n8n Workflow Import:
```powershell
# n8n ড্যাশবোর্ডে যান
# facebook-messenger-webhook-workflow-safety.json import করুন
# Configuration আপডেট করুন
```

### ৩. Service URLs Configuration:
- Safety Check Service: `http://localhost:8004`
- Patient Profile Service: `http://localhost:8003`
- STT Service: `http://localhost:8001`
- TTS Service: `http://localhost:8002`
- Ollama: `http://localhost:11434`
- ChromaDB: `http://localhost:8000`

## Testing Complete Flow

### High-Risk Query:
```
User: "আমার গর্ভাবস্থা জটিলতা হচ্ছে"

Bot: "এই বিষযয় অনুগ্রহ করে সরাসরি একজন হাকিম/ডাক্তারের পরামর্শ নিন।"
```

### Normal Query with Dosage:
```
User: "মাথা ব্যথার জন্য কি ওষুধ খাব?"

AI Response: "প্রতিদিন 500 মিগ্রাম প্যারাসিটামল খান..."

Safety Filtered: "প্রতিদিন [ডোজ তথ্য সরিয়ে দেওয়া হয়েছে]...

ব্যবহারকরে নোট: নির্দিষ্ট ডোজ বা পরিমাণ সম্পর্কে তথ্য সরিয়ে দেওয়া হয়েছে। ঔষধ সেবনের আগে অবশ্যই একজন হাকিম/ডাক্তারের পরামর্শ নিন।"
```

### Normal Query without Dosage:
```
User: "মাথা ব্যথার জন্য কি করব?"

AI Response: "গোলমরিচের ফোঁটা দিয় মালিশ করলে উপকার পাবেন..."

No modification needed, sent as-is
```

## Safety Features

### ১. **High-Risk Query Detection:**
- Pregnancy complications
- Severe pain symptoms
- Breathing difficulties
- Consciousness loss
- Child-related queries
- Medication interactions

### ২. **Dosage Information Filtering:**
- Specific dosages (e.g., "500 mg")
- Ranges (e.g., "250-500 mg")
- Frequency patterns (e.g., "twice daily")
- Specific medication mentions

### ৃ. **Configurable:**
- Easy to update keywords and patterns
- Runtime configuration reload
- Separate config file for maintenance

### ৪. **Medical Disclaimer:**
- Automatic disclaimer addition for filtered content
- Clear medical guidance warnings
- Professional referral messaging

## Advanced Configuration

### Custom Keywords:
```json
{
  "pre_check_keywords": {
    "custom_emergency": ["জরুরি", "emergency", "immediate help"],
    "chronic_conditions": ["দীর্ঘস্থায়ী", "chronic", "long-term"]
  }
}
```

### Custom Regex Patterns:
```json
{
  "post_check_regex": {
    "time_patterns": ["\\d+\\s*(am|pm)", "\\d+:\\d+"],
    "volume_patterns": ["\\d+\\s*(মিলি|লিটার|ml|liter)"]
  }
}
```

### Threshold Settings:
```json
{
  "threshold_settings": {
    "min_match_count": 2,
    "case_sensitive": true,
    "whole_word_match": true
  }
}
```

## Monitoring and Logs

### Safety Check Logs:
```python
# Add logging to safety_check_service.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log blocked queries
logger.warning(f"Blocked high-risk query: {text} - Keywords: {found_keywords}")

# Log filtered responses
logger.info(f"Filtered dosage information: {len(found_patterns)} patterns removed")
```

### Statistics Tracking:
- Blocked queries count
- Modified responses count
- False positive rates
- User feedback collection

## Troubleshooting

### Service Not Running:
```powershell
# Check service status
curl http://localhost:8004/health

# Restart service
python safety_check_service.py
```

### Configuration Not Loading:
```powershell
# Check config file exists
Test-Path safety_config.json

# Verify JSON format
Get-Content safety_config.json | ConvertFrom-Json
```

### Keywords Not Matching:
```powershell
# Check case sensitivity settings
# Update threshold_settings in config
# Test individual keywords via API
```

### Regex Not Working:
```powershell
# Test regex patterns
# Use regex101.com for validation
# Escape special characters properly
```

## Compliance and Ethics

### Medical Safety:
- Prevents dangerous medical advice
- Ensures professional referral
- Reduces liability risks

### Data Privacy:
- No query logging by default
- Optional audit logging
- Configurable retention policies

### Regulatory Compliance:
- HIPAA considerations
- Medical device regulations
- Telemedicine guidelines

This safety system ensures your AI healthcare assistant provides appropriate, safe responses while protecting users from potentially harmful medical advice and ensuring professional medical consultation when needed.