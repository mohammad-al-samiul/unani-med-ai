# UnaniMed AI - Comprehensive Test Plan

## Test Plan Overview
এই টেস্ট প্ল্যান UnaniMed AI system-এর সব প্রধান functionalities কভার করে এবং প্রতিটা কেসের জন্য detailed test steps, input examples, এবং expected outputs provide করে।

## Test Environment Setup

### Prerequisites:
- ✅ সব services running আছে (`start_all_services.bat`)
- ✅ n8n workflow imported এবং active
- ✅ Facebook Messenger webhook configured
- ✅ ChromaDB এ Unani books processed আছে
- ✅ Ollama models available (llama3.1:8b, nomic-embed-text)
- ✅ Cloudflare tunnel active (for webhook access)

### Services Status Check:
```powershell
# Verify all services are running
curl http://localhost:8001/health  # STT
curl http://localhost:8002/health  # TTS
curl http://localhost:8003/health  # Patient Profile
curl http://localhost:8004/health  # Safety Check
curl http://localhost:8005/health  # Semantic Cache
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:8000/api/v1/heartbeat  # ChromaDB
```

---

## Test Case 1: সাধারণ টেক্সট প্রশ্ন → RAG-গ্রাউন্ডেড উত্তর

### Test Steps:
1. Facebook Messenger এ বটে পাঠান: "মাথা ব্যথার জন্য কি করব?"
2. Wait for response (স্বাভাবিকভাবে 5-10 সেকেন্ড)
3. Response check করুন
4. Verify করুন যে response Unani books থেকে grounded আছে

### Input Examples:
```
টেস্ট ১.১: "মাথা ব্যথার জন্য কি করব?"
টেস্ট ১.২: "পেটের সমস্যার জন্য কি করব?"
টেস্ট ১.৩: "জ্বর কমানোর উপায় কি?"
টেস্ট ১.৪: "সর্দি সারানোর উপায় কি?"
টেস্ট ১.৫: "গায়ের ব্যথার জন্য কি করব?"
```

### Expected Output:
```
✅ Response: গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করলে মাথা ব্যথা উপশম হয়। এটি রক্ত সঞ্চালন বৃদ্ধি করে এবং ব্যথা কমায়। (সূত্র: canonical_medicine_guide - Page 45)

✅ Response contains:
- Medical information from Unani books
- Book reference (সূত্র)
- Page number
- Grounded content (no hallucination)

✅ Response time: 5-10 seconds (cold start)
✅ No safety warnings (normal query)
✅ Medical disclaimer present
```

### Verification Points:
- [ ] Response received within 10 seconds
- [ ] Response contains medical information
- [ ] Response includes book reference
- [ ] No generic/hallucinated content
- [ ] Medical disclaimer present
- [ ] Bengali language correct
- [ ] No safety blocking message

---

## Test Case 2: ভয়েস প্রশ্ন → Whisper → RAG → Piper → ভয়েস উত্তর

### Test Steps:
1. Facebook Messenger এ voice message পাঠান (record "মাথা ব্যথার জন্য কি করব?")
2. Wait for STT processing (3-5 seconds)
3. Verify text transcription appears
4. Wait for RAG + LLM processing (5-8 seconds)
5. Wait for TTS processing (2-3 seconds)
6. Check final response format

### Input Examples:
```
টেস্ট ২.১: Voice: "মাথা ব্যথার জন্য কি করব?"
টেস্ট ২.২: Voice: "পেটের সমস্যার জন্য কি করব?"
টেস্ট ২.৩: Voice: "জ্বর কমানোর উপায় কি?"
টেস্ট ২.৪: Voice: "সর্দি সারানোর উপায় কি?"
টেস্ট ২.৫: Voice: "গায়ের ব্যথার জন্য কি করব?"
```

### Expected Output:
```
✅ Step 1: STT Service Response
{
  "text": "মাথা ব্যথার জন্য কি করব?",
  "detected_language": "bn",
  "confidence": 0.92
}

✅ Step 2: RAG + LLM Response
গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করলে মাথা ব্যথা উপশম হয়...

✅ Step 3: TTS Service Response
{
  "audio_data": "base64_encoded_audio",
  "format": "mp3",
  "duration": 5.2
}

✅ Step 4: Final Messenger Response
"Voice response generated. Please check text response for details."

✅ Total Response Time: 10-15 seconds
✅ Bengali voice output quality: Good
✅ Transcription accuracy: >90%
```

### Verification Points:
- [ ] Voice message accepted
- [ ] STT transcription accurate (>90%)
- [ ] Language detected correctly (Bengali)
- [ ] RAG response generated
- [ ] TTS audio generated
- [ ] Audio quality acceptable
- [ ] Total response time <15 seconds
- [ ] Placeholder message sent for audio limitation

---

## Test Case 3: নতুন ইউজারের প্রথম মেসেজ → প্রোফাইলিং ফ্লো সম্পূর্ণ হওয়া

### Test Steps:
1. নতুন Facebook account দিয়ে bot start করুন (অথবা পুরানো user data clear করুন)
2. প্রথম message পাঠান: "মাথা ব্যথার জন্য কি করব?"
3. Wait for profiling flow শুরু হওয়া
4. Complete all profiling questions step by step
5. Verify final health question response after profiling complete

### Input Examples:
```
টেস্ট ৩.১: নতুন user প্রথম message: "মাথা ব্যথার জন্য কি করব?"

টেস্ট ৩.২: Profiling উত্তর:
Step 1: "26-35"
Step 2: "মহিলা"
Step 3: "না"
Step 4: "না"

টেস্ট ৩.৩: প্রোফাইলিং পর প্রশ্ন: "মাথা ব্যথার জন্য কি করব?"
```

### Expected Output:
```
✅ Step 1: Profile Check
{
  "exists": false,
  "profile": null
}

✅ Step 2: Start Profiling Flow
Bot: "আপনার বয়স কত? (উদাহরণ: ১৮-২৫, ২৬-৩৫, ৩৬-৪৫, ৪৬-৫৫, ৪৬+)"

✅ Step 3: Age Question
User: "26-35"
Bot: "আপনার লিঙ্গ কি? (পুরুষ/মহিলা/অন্যান্য)"

✅ Step 4: Gender Question
User: "মহিলা"
Bot: "আপনি কি বর্তমানে গর্ভবতী? (হ্যাঁ/না)"

✅ Step 5: Pregnancy Question (conditional)
User: "না"
Bot: "আপনার কোনো পূর্ববর্তী রোগ আছে কি? (যদি থাকে লিখুন, না থাকলে 'না' লিখুন)"

✅ Step 6: Prior Conditions Question
User: "না"
Bot: "আপনার প্রোফাইল সফলভাবে সেভ হয়েছে। এখন আপনি আপনার স্বাস্থ্য সমস্যা সম্পর্কে জিজ্ঞেস করতে পারেন।"

✅ Step 7: Database Verification
SQLite check:
SELECT * FROM patients WHERE sender_id = 'test_user_id';
Result: {
  "sender_id": "test_user_id",
  "age_range": "26-35",
  "gender": "মহিলা",
  "is_pregnant": false,
  "prior_conditions": "না",
  "created_at": "2024-08-26T10:00:00"
}

✅ Step 8: Final Health Question Response
User: "মাথা ব্যথার জন্য কি করব?"
Bot: [RAG response with patient context]
Response includes: [PATIENT CONTEXT]: বয়স: 26-35 | লিঙ্গ: মহিলা | গর্ভাবস্থা: গর্ভবতী নন | পূর্ববর্তী রোগ: না
```

### Verification Points:
- [ ] Profile check correctly identifies new user
- [ ] Profiling flow starts automatically
- [ ] All 4 questions asked sequentially
- [ ] Pregnancy question skipped for male users
- [ ] User responses stored correctly
- [ ] Profile saved to SQLite database
- [ ] Conversation state cleared after completion
- [ ] Completion message received
- [ ] Next question uses patient context
- [ ] Patient context included in RAG prompt

---

## Test Case 4: রেড-ফ্ল্যাগ কীওয়ার্ড থাকা প্রশ্ন → এসকেলেশন মেসেজ (LLM কল না হওয়া ভেরিফাই করাসহ)

### Test Steps:
1. High-risk keyword সহ question পাঠান
2. Wait for safety pre-check response
3. Verify no RAG + LLM processing occurs
4. Check service logs to confirm no LLM call
5. Verify escalation message received

### Input Examples:
```
টেস্ট ৪.১: "আমার গর্ভাবস্থা জটিলতা হচ্ছে"
টেস্ট ৪.২: "আমার তীব্র ব্যথা হচ্ছে"
টেস্ট ৪.৩: "আমার শ্বাসকষ্ট হচ্ছে"
টেস্ট ৪.৪: "আমি জ্ঞান হারাচ্ছি"
টেস্ট ৪.৫: "আমার শিশুর জ্বর হচ্ছে"
টেস্ট ৪.৬: "ওষুধ মিথস্ক্রিয়া প্রশ্ন"
```

### Expected Output:
```
✅ Step 1: Safety Pre-Check
{
  "should_block": true,
  "found_keywords": ["গর্ভাবস্থা জটিলতা"],
  "matched_categories": ["pregnancy_complications"],
  "block_message": "এই বিষয়ে অনুগ্রহ করে সরাসরি একজন হাকিম/ডাক্তারের পরামর্শ নিন।",
  "reason": "Found 1 high-risk keywords in 1 categories"
}

✅ Step 2: User Response
Bot: "এই বিষয়ে অনুগ্রহ করে সরাসরি একজন হাকিম/ডাক্তারের পরামর্শ নিন।"

✅ Step 3: Service Logs Verification
Check Ollama logs:
Expected: No LLM API calls for this request

Check ChromaDB logs:
Expected: No query operations for this request

Check n8n execution logs:
Expected: Workflow stops at safety pre-check, skips RAG + LLM nodes

✅ Step 4: Response Time
Expected: <2 seconds (no LLM processing)

✅ Step 5: Medical Disclaimer
Expected: Professional referral message only
```

### Verification Points:
- [ ] Safety pre-check detects keyword
- [ ] Block message received
- [ ] No RAG processing occurred
- [ ] No LLM call made (verify logs)
- [ ] No ChromaDB query made
- [ ] Response time <2 seconds
- [ ] Professional referral message
- [ ] No medical information provided
- [ ] No book references
- [ ] User directed to real doctor

---

## Test Case 5: একই প্রশ্ন দুইবার → দ্বিতীয়বার ক্যাশ থেকে দ্রুত উত্তর

### Test Steps:
1. প্রথম question পাঠান: "মাথা ব্যথার জন্য কি করব?"
2. Wait for response (cold start, 5-10 seconds)
3. Note response time and content
4. দ্বিতীয় time একই question পাঠান
5. Verify cached response (should be <1 second)
6. Check cache stats to confirm cache hit

### Input Examples:
```
টেস্ট ৫.১: প্রথম: "মাথা ব্যথার জন্য কি করব?"
টেস্ট ৫.২: দ্বিতীয়: "মাথা ব্যথার জন্য কি করব?"

টেস্ট ৫.৩: প্রথম: "পেটের সমস্যার জন্য কি করব?"
টেস্ট ৫.৪: দ্বিতীয়: "পেটের সমস্যার জন্য কি করব?"
```

### Expected Output:
```
✅ Step 1: First Request (Cold Start)
Request: "মাথা ব্যথার জন্য কি করব?"
Cache Check: {"cached": false}
RAG + LLM Processing: Yes
Response Time: 8-12 seconds
Response: গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করলে মাথা ব্যথা উপশম হয়...
Cache Store: {"success": true}

✅ Step 2: Second Request (Cache Hit)
Request: "মাথা ব্যথার জন্য কি করব?"
Cache Check: {
  "cached": true,
  "similarity": 0.98,
  "response": "গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করলে মাথা ব্যথা উপশম হয়...",
  "cached_at": "2024-08-26T10:05:00"
}
RAG + LLM Processing: No (skipped)
Response Time: <1 second
Response: গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করলে মাথা ব্যথা উপশম হয়...

✅ Step 3: Cache Stats Verification
Cache Stats: {
  "total_entries": 1,
  "similarity_threshold": 0.92,
  "collection_name": "semantic_cache"
}

✅ Performance Improvement:
First request: 8-12 seconds
Second request: <1 second
Speed improvement: 90%+
```

### Verification Points:
- [ ] First request processes normally (cold start)
- [ ] Response stored in cache successfully
- [ ] Second request returns cached response
- [ ] Response time <1 second for cached request
- [ ] Response content identical between requests
- [ ] No RAG + LLM processing for second request
- [ ] Cache similarity >0.92
- [ ] Cache stats updated correctly
- [ ] 90%+ performance improvement

---

## Test Case 6: Whisper ভুল/অস্পষ্ট শোনা → গ্রেসফুল fallback মেসেজ

### Test Steps:
1. Unclear voice message পাঠান (mumble, background noise, very quiet)
2. Wait for STT processing
3. Verify error handling
4. Check graceful fallback message
5. Test with partial audio/corrupted file

### Input Examples:
```
টেস্ট ৬.১: Voice: [mumbled unclear audio]
টেস্ট ৬.২: Voice: [background noise with faint speech]
টেস্ট ৬.৩: Voice: [very quiet audio]
টেস্ট ৬.৪: Voice: [partial/corrupted audio file]
টেস্ট ৬.৅: Voice: [non-Bengali language]
```

### Expected Output:
```
✅ Step 1: STT Error Handling
STT Service Response (low confidence):
{
  "text": "শব্দ অস্পষ্ট",
  "detected_language": "unknown",
  "confidence": 0.45,
  "error": "Low confidence transcription"
}

✅ Step 2: Graceful Fallback
Bot: "আপনার বক্তব্য স্পষ্ট হয়নি। অনুগ্রহ করে আবার স্পষ্টভাবে বলুন অথবা টেক্সট মেসেজ পাঠান।"

✅ Step 3: Error Logging
Service Log: "STT confidence low (0.45) for user message. Fallback triggered."

✅ Step 4: No RAG Processing
Expected: RAG + LLM skipped due to low confidence transcription

✅ Step 5: User Guidance
Bot provides clear instructions for retry
```

### Verification Points:
- [ ] STT service detects low confidence
- [ ] Error handled gracefully
- [ ] Fallback message user-friendly
- [ ] No RAG + LLM processing attempted
- [ ] User guided to retry
- [ ] Error logged for monitoring
- [ ] Response time reasonable (<5 seconds)
- [ ] System remains stable
- [ ] No crash or hang

---

## Test Case 7: n8n/PC রিস্টার্টের পর → Error Workflow দিয়ে queued মেসেজ রিকভারি

### Test Steps:
1. একটি message পাঠান during normal operation
2. n8n service restart করুন (বা simulate error)
3. Wait for system recovery
4. Check error workflow activation
5. Verify message processing after recovery
6. Check error log entries

### Input Examples:
```
টেস্ট ৭.১: নরমাল operation → n8n restart → message recovery
টেস্ট ৭.২: STT service down → error workflow → retry logic
টেস্ট ৭.৩: ChromaDB connection lost → error handling → recovery
টেস্ট ৭.৪: Ollama service down → error workflow → retry
টেস্ট ৭.৫: Multiple service failures → cascading error handling
```

### Expected Output:
```
✅ Step 1: Normal Operation
User: "মাথা ব্যথার জন্য কি করব?"
System: Normal response received

✅ Step 2: Simulate n8n Restart
Stop n8n service
Wait 10 seconds
Start n8n service

✅ Step 3: Error Workflow Activation
Error Log Entry:
{
  "timestamp": "2024-08-26T10:15:00",
  "workflow": "Facebook Messenger Webhook Handler",
  "node": "Call Ollama with RAG",
  "error": "Connection refused",
  "retry_count": 1
}

✅ Step 4: Retry Logic
First retry: Failed (service still down)
Second retry: Failed (service still down)
Third retry: Success (service recovered)

✅ Step 5: Message Recovery
After 3 retries, message processed successfully
User receives: Normal RAG response

✅ Step 6: Error Log
Error Log File (error_log.txt):
{"timestamp":"2024-08-26T10:15:00","workflow":"Facebook Messenger Webhook Handler","node":"Call Ollama with RAG","error":"Connection refused","retry_count":1,"status":"RETRYING"}
{"timestamp":"2024-08-26T10:15:10","workflow":"Facebook Messenger Webhook Handler","node":"Call Ollama with RAG","error":"Connection refused","retry_count":2,"status":"RETRYING"}
{"timestamp":"2024-08-26T10:15:20","workflow":"Facebook Messenger Webhook Handler","node":"Call Ollama with RAG","error":"Connection refused","retry_count":3,"status":"FAILED after 3 retries"}

✅ Step 7: User Experience
User perceives slight delay but receives response
No data loss
No system crash
```

### Verification Points:
- [ ] Error workflow activates correctly
- [ ] 3-retry logic implemented
- [ ] Error logged to local file
- [ ] Message queued during downtime
- [ ] Message processed after recovery
- [ ] User receives response eventually
- [ ] Error log contains proper details
- [ ] System recovers gracefully
- [ ] No data loss occurs
- [ ] Error message user-friendly (if any)

---

## Test Results Tracking Template

### Markdown Template:

```markdown
# UnaniMed AI Test Results

## Test Execution Summary
- **Test Date:** [DATE]
- **Tester:** [NAME]
- **Environment:** [DEV/STAGING/PROD]
- **Services Status:** [ALL RUNNING/PARTIAL DOWN]

## Test Case Results

### Test Case 1: সাধারণ টেক্সট প্রশ্ন → RAG-গ্রাউন্ডেড উত্তর
| Test ID | Input | Expected | Actual | Status | Notes |
|---------|-------|----------|--------|--------|-------|
| 1.1 | "মাথা ব্যথার জন্য কি করব?" | RAG response with book reference | [ACTUAL RESPONSE] | [PASS/FAIL] | [NOTES] |
| 1.2 | "পেটের সমস্যার জন্য কি করব?" | RAG response with book reference | [ACTUAL RESPONSE] | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 2: ভয়েস প্রশ্ন → Whisper → RAG → Piper → ভয়েস উত্তর
| Test ID | Input | Expected Time | Actual Time | STT Accuracy | TTS Quality | Status | Notes |
|---------|-------|---------------|-------------|--------------|-------------|--------|-------|
| 2.1 | Voice: "মাথা ব্যথার জন্য কি করব?" | 10-15s | [ACTUAL] | [ACCURACY%] | [QUALITY] | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 3: নতুন ইউজারের প্রথম মেসেজ → প্রোফাইলিং ফ্লো সম্পূর্ণ হওয়া
| Test ID | Step | Expected | Actual | Status | Notes |
|---------|------|----------|--------|--------|-------|
| 3.1 | Profile Check | exists: false | [ACTUAL] | [PASS/FAIL] | [NOTES] |
| 3.2 | Age Question | "আপনার বয়স কত?" | [ACTUAL] | [PASS/FAIL] | [NOTES] |
| 3.3 | Profile Save | Success | [ACTUAL] | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 4: রেড-ফ্ল্যাগ কীওয়ার্ড থাকা প্রশ্ন → এসকেলেশন মেসেজ
| Test ID | Input | Keyword Detected | LLM Call Made | Block Message | Status | Notes |
|---------|-------|------------------|---------------|---------------|--------|-------|
| 4.1 | "গর্ভাবস্থা জটিলতা" | Yes | No | Yes | [PASS/FAIL] | [NOTES] |
| 4.2 | "তীব্র ব্যথা" | Yes | No | Yes | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 5: একই প্রশ্ন দুইবার → দ্বিতীয়বার ক্যাশ থেকে দ্রুত উত্তর
| Test ID | First Request Time | Second Request Time | Cache Hit | Speed Improvement | Status | Notes |
|---------|-------------------|---------------------|-----------|------------------|--------|-------|
| 5.1 | [TIME] | [TIME] | Yes | [IMPROVEMENT%] | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 6: Whisper ভুল/অস্পষ্ট শোনা → গ্রেসফুল fallback মেসেজ
| Test ID | Input Type | STT Confidence | Fallback Message | RAG Skipped | Status | Notes |
|---------|------------|----------------|------------------|-------------|--------|-------|
| 6.1 | Unclear audio | <0.5 | Yes | Yes | [PASS/FAIL] | [NOTES] |
| 6.2 | Background noise | <0.5 | Yes | Yes | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

### Test Case 7: n8n/PC রিস্টার্টের পর → Error Workflow দিয়ে queued মেসেজ রিকভারি
| Test ID | Error Type | Retry Count | Recovery Success | Error Logged | Status | Notes |
|---------|------------|-------------|------------------|--------------|--------|-------|
| 7.1 | n8n restart | 3 | Yes | Yes | [PASS/FAIL] | [NOTES] |
| 7.2 | Service down | 3 | Yes | Yes | [PASS/FAIL] | [NOTES] |

**Overall Status:** [PASS/FAIL]

## Final Summary
- **Total Test Cases:** 7
- **Passed:** [COUNT]
- **Failed:** [COUNT]
- **Overall Status:** [PASS/FAIL]

## Issues Found
1. [ISSUE 1]
2. [ISSUE 2]

## Recommendations
1. [RECOMMENDATION 1]
2. [RECOMMENDATION 2]
```

### Spreadsheet Template (CSV Format):

```csv
Test Case ID,Test Name,Test Step,Input,Expected Output,Actual Output,Status,Response Time,Notes,Tester,Date
1.1,Text to RAG Response,Normal text question,"মাথা ব্যথার জন্য কি করব?",RAG response with book reference,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
1.2,Text to RAG Response,Normal text question,"পেটের সমস্যার জন্য কি করব?",RAG response with book reference,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
2.1,Voice to Voice Response,Voice message processing,Voice: "মাথা ব্যথার জন্য কি করব?",Full voice pipeline response,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
3.1,New User Profiling,Profile flow completion,First message: "মাথা ব্যথার জন্য কি করব?",Profile complete + health response,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
4.1,Red Flag Keywords,Safety blocking,"গর্ভাবস্থা জটিলতা",Escalation message no LLM,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
5.1,Cache Performance,Same question twice,First: "মাথা ব্যথার জন্য কি করব?",Second response <1s,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
6.1,STT Error Handling,Unclear audio,Unclear voice message,Fallback message,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
7.1,Error Recovery,n8n restart,Message during restart,Message recovered after retry,"[ACTUAL]",PASS/FAIL,"[TIME]","[NOTES]","[NAME]","[DATE]"
```

---

## Test Execution Checklist

### Pre-Test Setup:
- [ ] All services running
- [ ] n8n workflow imported and active
- [ ] Facebook webhook configured
- [ ] ChromaDB has processed books
- [ ] Test user account ready
- [ ] Error log file location noted
- [ ] Cache stats baseline recorded

### During Testing:
- [ ] Response times recorded
- [ ] Service logs monitored
- [ ] Error handling verified
- [ ] User experience documented
- [ ] Edge cases tested
- [ ] Performance metrics collected

### Post-Test Analysis:
- [ ] Results documented in template
- [ ] Issues categorized by severity
- [ ] Performance analysis completed
- [ ] Recommendations formulated
- [ ] Regression tests identified
- [ ] Test report finalized

---

## Performance Benchmarks

### Expected Performance Metrics:
- **Text Response Time:** 5-10 seconds (cold), <1 second (cached)
- **Voice Response Time:** 10-15 seconds (total pipeline)
- **Cache Hit Rate:** 40-60% (after warm-up)
- **Safety Check Time:** <2 seconds
- **Error Recovery Time:** <30 seconds
- **Profiling Flow Time:** 1-2 minutes (4 questions)

### System Capacity:
- **Concurrent Users:** 10-20 (free tier)
- **Cache Storage:** 1000+ entries
- **Database Size:** Growth with user profiles
- **Backup Time:** <5 minutes daily

---

## Success Criteria

### Test Pass Criteria:
- ✅ All 7 test cases pass
- ✅ Response times within benchmarks
- ✅ No critical errors
- ✅ Safety systems functioning
- ✅ Cache performance optimal
- ✅ Error handling robust

### System Readiness Criteria:
- ✅ All services stable
- ✅ Performance metrics met
- ✅ Safety measures effective
- ✅ User experience acceptable
- ✅ Monitoring operational
- ✅ Backup system functional

---

## Test Automation Opportunities

### Automated Tests:
- Service health checks
- API endpoint testing
- Cache performance validation
- Safety keyword detection
- Error workflow triggering

### Manual Tests:
- User experience validation
- Voice quality assessment
- Profiling flow interaction
- Edge case scenarios
- Integration testing

---

## Next Steps

### After Testing:
1. Analyze test results
2. Fix identified issues
3. Optimize performance bottlenecks
4. Update documentation
5. Plan regression testing
6. Schedule regular testing

### Continuous Testing:
- Weekly smoke tests
- Monthly full regression
- Performance monitoring
- User feedback collection
- System health checks

This comprehensive test plan ensures thorough validation of the UnaniMed AI system across all critical functionalities and edge cases.