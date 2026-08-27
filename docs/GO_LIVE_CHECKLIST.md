# UnaniMed AI - Go-Live Checklist

## Go-Live Checklist Overview
এই checklist UnaniMed AI system-এর production deployment এর জন্য সব essential steps কভার করে। প্রতিটা সেকশন complete করার পর চেকমার্ক দিন এবং production deployment এর আগে সব কিছু verify করুন।

---

## Phase 1: Cloudflare Tunnel Configuration

### ১.১ Temporary Tunnel থেকে Named Tunnel এ Convert করা

#### Current State:
```
Temporary Tunnel URL: https://your-username-random.workers.dev/webhook
```

#### Steps for Named Tunnel:

**Step 1: Cloudflare Dashboard-এ যান**
```
1. Cloudflare Dashboard এ লগইন করুন
2. Your domain select করুন
3. "Zero Trust" → "Networks" → "Tunnels" এ যান
```

**Step 2: Named Tunnel Create করুন**
```
1. "Create a tunnel" ক্লিক করুন
2. Tunnel Type: "Cloudflared" select করুন
3. Tunnel Name: "unanimed-ai-bot" (বা your preferred name)
4. Click "Next"
```

**Step 3: Subdomain Configuration**
```
1. Subdomain: "unanimed" (বা your preferred subdomain)
2. Domain: Select your domain
3. Full URL: https://unanimed.yourdomain.com
4. Click "Save tunnel"
```

**Step 4: Install Cloudflared**
```powershell
# Windows-এ cloudflared install করুন
# Download from: https://github.com/cloudflare/cloudflared/releases/latest

# অথবা winget ব্যবহার করুন
winget install --id Cloudflare.cloudflared

# Verify installation
cloudflared --version
```

**Step 5: Cloudflared Authentication**
```powershell
# Cloudflare login করুন
cloudflared tunnel login

# Browser এ আপনার domain select করুন
# Authentication successful হলে proceed করুন
```

**Step 6: Configure Tunnel**
```powershell
# Tunnel run করুন
cloudflared tunnel run unanimed-ai-bot

# অথবা service হিসেবে run করুন
cloudflared tunnel service install
```

**Step 7: Public Hostname Configure করুন**
```
1. Cloudflare Dashboard → Tunnels → unanimed-ai-bot
2. "Public Hostname" tab এ যান
3. "Add a public hostname" ক্লিক করুন
4. Subdomain: "unanimed"
5. Domain: yourdomain.com
6. Service: HTTP
7. URL: http://localhost:5678 (n8n default port)
8. Save করুন
```

**Step 8: Test Named Tunnel**
```powershell
# Named tunnel test করুন
curl https://unanimed.yourdomain.com/webhook

# Expected: n8n webhook response
```

#### Verification Checklist:
- [ ] Named tunnel created successfully
- [ ] Subdomain working correctly
- [ ] DNS propagation complete
- [ ] SSL certificate active
- [ ] Webhook URL accessible publicly
- [ ] Temporary tunnel বন্ধ করা হয়েছে
- [ ] Cloudflared service running

#### Backup Configuration:
```powershell
# Tunnel configuration export করুন
cloudflared tunnel token > tunnel-token.txt

# Save for disaster recovery
```

---

## Phase 2: n8n Security Configuration

### ২.১ Environment Variables Security

#### Create .env File:
```powershell
# n8n এর root directory-এ .env file create করুন
cd C:\Users\Admin\n8n
notepad .env
```

#### .env File Content:
```env
# n8n Configuration
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_PATH=/
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_secure_password_here

# Database
DB_TYPE=sqlite
DB_SQLITE_VACUUM_ON_STARTUP=true

# Security
N8N_ENCRYPTION_KEY=your_random_encryption_key_here
N8N_JWT_HEADER=authorization
N8N_JWT_AUTH_HEADER=authorization
N8N_JWT_ISSUER=n8n
N8N_JWT_AUDIENCE=n8n
N8N_JWT_TOKEN_SIGNING_ALGORITHM=HS256
N8N_JWT_TOKEN_SIGNING_VALUE=your_jwt_secret_here

# External Services
WEBHOOK_URL=https://unanimed.yourdomain.com/webhook
CLOUDFLARE_TUNNEL_URL=https://unanimed.yourdomain.com

# Rate Limiting
N8N_PAYLOAD_SIZE_MAX=16
EXECUTIONS_TIMEOUT=3600
EXECUTIONS_TIMEOUT_MAX=7200

# Logging
N8N_LOG_LEVEL=info
N8N_LOG_OUTPUT=file
N8N_LOG_FILE_LOCATION=./logs/n8n.log
```

#### Generate Secure Keys:
```powershell
# Encryption key generate করুন
openssl rand -base64 32

# JWT secret generate করুন
openssl rand -base64 32
```

### ২.২ Credentials Security

#### n8n Credential Store ব্যবহার করুন:

**Hardcoded Credentials Remove করুন:**
```
❌ DON'T: Directly in workflow JSON
✅ DO: Use n8n credential store
```

**Facebook Messenger Credential Setup:**
```
1. n8n Dashboard → Credentials
2. "Add Credential" ক্লিক করুন
3. Type: "HTTP Header Auth"
4. Name: "Facebook Messenger Auth"
5. Header Name: "Authorization"
6. Header Value: "Bearer YOUR_FACEBOOK_PAGE_ACCESS_TOKEN"
7. Save করুন
```

**Ollama Credential Setup:**
```
1. n8n Dashboard → Credentials
2. "Add Credential" ক্লিক করুন
3. Type: "HTTP Header Auth" (if needed)
4. Configure for Ollama API access
5. Save করুন
```

**Service URL Credentials:**
```
❌ DON'T: Hardcode localhost URLs
✅ DO: Use environment variables or credential store
```

### ২.ৃ Workflow Security Updates

#### Update All Workflows:
```json
// Replace hardcoded values with credential references
{
  "credentials": {
    "httpHeaderAuth": {
      "id": "facebook-messenger-auth",
      "name": "Facebook Messenger Auth"
    }
  }
}
```

#### Remove Sensitive Data:
```
❌ Remove: API keys, tokens, passwords from workflow JSON
❌ Remove: IP addresses, localhost URLs
❌ Remove: Personal information
✅ Replace: With credential references
✅ Replace: With environment variables
```

### ২.৪ Security Best Practices

#### Encryption Enable করুন:
```powershell
# n8n এ encryption enable করুন
# Settings → Security → Encryption
# Use the N8N_ENCRYPTION_KEY from .env
```

#### Access Control:
```
1. n8n Dashboard → Settings → User Management
2. Admin account শুধুমাত্র trusted users এর জন্য
3. Two-factor authentication enable করুন (if available)
4. Password complexity requirements সেট করুন
```

#### Audit Logging:
```
1. Settings → Logs
2. Enable workflow execution logging
3. Enable error logging
4. Set log retention period
```

#### Verification Checklist:
- [ ] .env file created with all variables
- [ ] No hardcoded credentials in workflows
- [ ] All credentials in n8n credential store
- [ ] Encryption enabled
- [ ] JWT authentication configured
- [ ] Basic auth enabled
- [ ] Sensitive data removed from JSON files
- [ ] Credentials rotated (if needed)
- [ ] Backup of credentials stored securely

---

## Phase 3: Facebook App Review Preparation

### ৩.১ Facebook Developer Console Setup

#### Step 1: App Configuration
```
1. Facebook Developers Dashboard এ যান
2. Your app select করুন
3. "App Review" tab এ যান
```

#### Step 2: Required Permissions

**Essential Permissions:**
```
✅ pages_messaging
  - Purpose: Send and receive messages
  - Review: Required for production

✅ pages_read_engagement
  - Purpose: Read page engagement data
  - Review: May be required

✅ pages_manage_metadata
  - Purpose: Manage page metadata
  - Review: May be required
```

**Add Permissions:**
```
1. "App Review" → "Permissions and Features"
2. "Request Permission" ক্লিক করুন
3. Search: "pages_messaging"
4. Add permission
5. Explain your use case
6. Submit for review
```

### ৩.২ Use Case Description

#### pages_messaging Use Case:
```
Title: Unani Medicine AI Health Assistant

Description:
"আমরা একটি AI-powered Unani medicine health assistant তৈরি করেছি যা 
Facebook Messenger এর মাধ্যমে ব্যবহারকারীদের সাধারণ স্বাস্থ্য তথ্য 
provide করে। এটি স্বাস্থ্য সম্পর্কিত সাধারণ প্রশ্নের উত্তর দেয়, 
Unani medicine সম্পর্কে তথ্য provide করে, এবং জটিল সমস্যায়ের ক্ষেত্রে 
professional medical consultation এর পরামর্শ দেয়।"

How people use your app:
"ব্যবহারকারীরা আমাদের Facebook page এ message পাঠায় এবং AI 
assistant স্বাস্থ্য সম্পর্কিত প্রশ্নের উত্তর দেয়।"

Screenshots needed:
- App screenshot
- Message flow example
- Privacy policy page
```

### ৩.৩ Privacy Policy Setup

#### Create Privacy Policy Page:
```html
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UnaniMed AI - Privacy Policy</title>
</head>
<body>
    <h1>UnaniMed AI - গোপনীয়তা নীতি</h1>
    
    <h2>তথ্য সংগ্রহ</h2>
    <p>আমরা শুধুমাত্র স্বাস্থ্য সম্পর্কিত প্রশ্ন এবং সাধারণ জনসংখ্যাগত তথ্য সংগ্রহ করি।</p>
    
    <h2>তথ্য ব্যবহার</h2>
    <p>সংগৃহীত তথ্য শুধুমাত্র স্বাস্থ্য তথ্য provide করার জন্য ব্যবহৃত হয়।</p>
    
    <h2>তথ্য সুরক্ষা</h2>
    <p>সব তথ্য locally stored এবং encrypted। আমরা কোনো personal health information বাইরের সার্ভিসে পাঠাই না।</p>
    
    <h2>তৃতীয় পক্ষের শেয়ারিং</h2>
    <p>আমরা কোনো তথ্য তৃতীয় পক্ষের সাথে শেয়ার করি না।</p>
    
    <h2>ব্যবহারকারী অধিকার</h2>
    <p>ব্যবহারকারীরা তাদের তথ্য delete করতে পারেন এবং service বন্ধ করতে পারেন।</p>
    
    <h2>চিকিৎসা দায়িত্ব</h2>
    <p>এই AI assistant কোনো ডাক্তার বা হাকিমের বিকল্প নয়। সবসময় প্রকৃত চিকিৎসকের পরামর্শ নিন।</p>
    
    <h2>যোগাযোগ</h2>
    <p>প্রশ্ন থাকলে: support@unanimed.ai</p>
</body>
</html>
```

#### Host Privacy Policy:
```
1. Privacy policy কে আপনার website এ host করুন
2. URL: https://yourdomain.com/privacy-policy
3. অথবা GitHub Pages এ host করুন
4. URL add করুন Facebook app settings এ
```

### ৩.৪ App Review Submission

#### Pre-Submission Checklist:
```
✅ Privacy policy URL provided
✅ Use case description complete
✅ Screenshots uploaded
✅ App icon uploaded
✅ Terms of service provided (if required)
✅ Contact information provided
✅ All required permissions requested
✅ Testing instructions provided
```

#### Submit for Review:
```
1. Facebook Developers Dashboard
2. App Review → Submit for Review
3. Provide all required information
4. Wait for Facebook review (usually 2-5 business days)
```

#### Verification Checklist:
- [ ] Privacy policy page live and accessible
- [ ] Use case description clear and detailed
- [ ] Screenshots uploaded
- [ ] All required permissions requested
- [ ] App testing instructions provided
- [ ] Contact information up to date
- [ ] Terms of service available (if needed)
- [ ] App icon uploaded
- [ ] App submitted for review
- [ ] Review status tracked

---

## Phase 4: Load Testing Plan

### ৪.১ Load Test Scenarios

#### Scenario 1: Sequential Messages
```
Test: 10 messages sequentially from single user
Expected: All messages processed correctly
Time: <60 seconds total
```

#### Scenario 2: Concurrent Users
```
Test: 5 users sending messages simultaneously
Expected: All messages processed without errors
Time: <30 seconds per message
```

#### Scenario 3: Rapid Fire
```
Test: 10 messages within 10 seconds from single user
Expected: Queue handled, all processed eventually
Time: May take longer due to queuing
```

#### Scenario 4: Mixed Input Types
```
Test: 5 text + 5 voice messages concurrently
Expected: All processed correctly
Time: Text faster, voice takes longer
```

#### Scenario 5: New User Onboarding
```
Test: 5 new users starting profile flow simultaneously
Expected: All profile flows complete successfully
Time: 1-2 minutes per user
```

### ৪.২ Load Test Execution

#### Manual Load Test:
```powershell
# Test Tool: Postman অথবা curl

# Test 1: Sequential messages
for ($i=1; $i -le 10; $i++) {
    curl -X POST https://unanimed.yourdomain.com/webhook `
      -H "Content-Type: application/json" `
      -d '{"object":"page","entry":[{"messaging":[{"message":{"text":"মাথা ব্যথার জন্য কি করব?"}}]}]}'
    Start-Sleep -Seconds 2
}

# Test 2: Concurrent users (simulated with multiple terminals)
# Open 5 separate PowerShell windows and run simultaneously
```

#### Automated Load Test (Optional):
```powershell
# Apache JMeter ব্যবহার করুন for advanced load testing
# Create test plan with:
# - 10 concurrent users
# - 100 requests per user
# - Ramp-up time: 10 seconds
# - Duration: 5 minutes
```

### ৪.৩ Performance Metrics

#### Expected Performance:
```
✅ Single message: <10 seconds (text), <15 seconds (voice)
✅ 5 concurrent users: <15 seconds per message
✅ 10 concurrent users: <20 seconds per message
✅ 50 messages per minute: Sustainable
✅ Error rate: <1%
✅ Memory usage: <4GB
✅ CPU usage: <80%
```

#### Monitoring During Load Test:
```
✅ Service response times
✅ Error rates
✅ System resource usage
✅ Database performance
✅ Cache hit rates
✅ n8n execution queue
```

### ৪.ৄ Load Test Results Verification

#### Success Criteria:
```
✅ All messages processed successfully
✅ No system crashes
✅ No data corruption
✅ Response times within acceptable limits
✅ Error rate <1%
✅ System resources stable
✅ No memory leaks
✅ Database performance acceptable
```

#### Failure Handling:
```
❌ If errors >1%: Investigate bottlenecks
❌ If system crashes: Increase resources
❌ If database slow: Optimize queries
❌ If cache miss high: Warm up cache
```

#### Verification Checklist:
- [ ] Sequential messages test passed
- [ ] Concurrent users test passed
- [ ] Rapid fire test passed
- [ ] Mixed input types test passed
- [ ] New user onboarding test passed
- [ ] Performance metrics within limits
- [ ] Error rate <1%
- [ ] System resources stable
- [ ] No memory leaks detected
- [ ] Database performance acceptable

---

## Phase 5: Monitoring & Alerts Verification

### ৫.১ UptimeRobot Monitoring Check

#### Verify Monitoring Setup:
```
1. UptimeRobot Dashboard এ যান
2. Monitor status check করুন
3. Verify webhook URL: https://unanimed.yourdomain.com/webhook
4. Check monitoring interval: 5 minutes
5. Verify alert contacts: Telegram bot
```

#### Test Alert System:
```
1. n8n service temporarily stop করুন
2. Wait 5-10 minutes
3. Check Telegram alert received
4. n8n service restart করুন
5. Verify recovery alert received
```

### ৫.২ Service Health Monitoring

#### All Services Health Check:
```powershell
# Health check script রান করুন
# services_health_check.ps1

$services = @{
    "STT" = "http://localhost:8001/health"
    "TTS" = "http://localhost:8002/health"
    "Patient Profile" = "http://localhost:8003/health"
    "Safety Check" = "http://localhost:8004/health"
    "Semantic Cache" = "http://localhost:8005/health"
    "Ollama" = "http://localhost:11434/api/tags"
    "ChromaDB" = "http://localhost:8000/api/v1/heartbeat"
}

foreach ($service in $services.GetEnumerator()) {
    try {
        $response = Invoke-RestMethod -Uri $service.Value -Method Get
        Write-Host "$($service.Key): Healthy" -ForegroundColor Green
    }
    catch {
        Write-Host "$($service.Key): Unhealthy" -ForegroundColor Red
    }
}
```

### ৫.৩ Error Monitoring Setup

#### Error Log Monitoring:
```powershell
# Error log monitoring script
# monitor_error_logs.ps1

$errorLog = "C:\Users\Admin\Documents\dev\office-dev\unani-med-ai\error_log.txt"

if (Test-Path $errorLog) {
    $recentErrors = Get-Content $errorLog | Select-Object -Last 10
    Write-Host "Recent 10 errors:"
    $recentErrors
} else {
    Write-Host "No error log file found"
}
```

#### Backup Verification:
```powershell
# Verify latest backup
$backupDir = "C:\Users\Admin\Documents\dev\office-dev\unani-med-ai\backups"
$latestBackup = Get-ChildItem $backupDir -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "Latest backup: $($latestBackup.FullName)"
Write-Host "Backup time: $($latestBackup.LastWriteTime)"
Write-Host "Backup size: $([math]::Round($latestBackup.Length / 1MB, 2)) MB"
```

### ৫.ৄ Verification Checklist:
- [ ] UptimeRobot monitor active
- [ ] Webhook URL correct
- [ ] Telegram bot connected
- [ ] Alert system tested
- [ ] All services healthy
- [ ] Error monitoring active
- [ ] Backup system working
- [ ] Health check scripts functional
- [ ] Monitoring dashboards accessible
- [ ] Alert notifications working

---

## Phase 6: Manual Review Process Setup

### ৬.১ Review Team Setup

#### Review Roles:
```
✅ Primary Reviewer: You (System Owner)
✅ Safety Reviewer: Medical/Health domain expert
✅ Technical Reviewer: System administrator
✅ Quality Reviewer: User experience expert
```

#### Review Schedule:
```
Week 1: Daily reviews (all responses)
Week 2: Sample reviews (20% random sample)
Week 3+: Weekly reviews (anomaly detection)
```

### ৬.২ Review Process

#### Daily Review Process:
```
1. Review Day Previous Responses:
   - Access error_log.txt
   - Check safety triggers
   - Review any flagged responses

2. Sample Quality Check:
   - Random 10 responses review
   - Check medical accuracy
   - Verify safety compliance
   - Assess response quality

3. System Health Check:
   - Service status
   - Error rates
   - Performance metrics
   - User feedback (if any)
```

#### Review Template:
```markdown
# Daily Review Log - [DATE]

## Safety Review
- High-risk queries blocked: [COUNT]
- Dosage information filtered: [COUNT]
- Escalation messages sent: [COUNT]
- Safety issues found: [YES/NO]

## Quality Review
- Sample responses reviewed: [COUNT]
- Accurate responses: [COUNT]
- Grounded responses: [COUNT]
- Issues found: [YES/NO]

## System Health
- Services status: [ALL HEALTHY/SOME DOWN]
- Error rate: [PERCENTAGE]
- Response time average: [SECONDS]
- Cache hit rate: [PERCENTAGE]

## Issues Logged
1. [ISSUE 1]
2. [ISSUE 2]

## Actions Taken
1. [ACTION 1]
2. [ACTION 2]

## Notes
[ADDITIONAL NOTES]
```

### ৬.৩ Safety Review Focus

#### Critical Safety Items:
```
✅ High-risk keyword detection accuracy
✅ Dosage filtering effectiveness
✅ Medical disclaimer presence
✅ Professional referral messages
✅ Grounded response verification
✅ No hallucination detection
```

#### Review Checklist:
```
For each response:
- [ ] Medical information accurate
- [ ] Source references present
- [ ] No dangerous advice
- [ ] Medical disclaimer included
- [ ] Patient context considered
- [ ] Response appropriate for query
- [ ] No harmful content
- [ ] No sexual/inappropriate content
```

### ৬.৪ User Feedback Collection

#### Feedback Mechanism:
```
✅ Add feedback option to responses
✅ "Was this helpful?" button
✅ "Report issue" option
✅ User satisfaction rating
```

#### Feedback Collection:
```
1. Response এ এ add করুন:
   "এই উত্তর কি সহায়ক ছিল? (হ্যাঁ/না)"

2. Negative feedback handle করুন:
   - Log the feedback
   - Review the response
   - Improve system
```

### ৬.৫ Escalation Process

#### When to Escalate:
```
❌ Safety system failure
❌ Medical inaccuracy found
❌ User complains about advice
❌ System error causing issues
❌ Unexpected behavior
```

#### Escalation Steps:
```
1. Immediate: Disable problematic feature
2. Log the issue with details
3. Review by medical expert
4. System fix or improvement
5. Resume service after validation
```

### ৬.৬ Review Verification Checklist:
- [ ] Review team identified
- [ ] Review schedule established
- [ ] Review template created
- [ ] Safety review process defined
- [ ] Quality review process defined
- [ ] User feedback mechanism setup
- [ ] Escalation process defined
- [ ] Review tracking system ready
- [ ] Daily review script prepared
- [ ] Weekly review process planned

---

## Final Go-Live Checklist

### Pre-Go-Live Verification:

#### Infrastructure:
- [ ] Cloudflare named tunnel active
- [ ] SSL certificate valid
- [ ] DNS propagation complete
- [ ] All services running
- [ ] Database backups working
- [ ] System resources adequate

#### Security:
- [ ] Environment variables configured
- [ ] Credentials secured
- [ ] Encryption enabled
- [ ] Access control configured
- [ ] Audit logging active
- [ ] No hardcoded secrets

#### Facebook:
- [ ] Privacy policy live
- [ ] App review submitted
- [ ] Permissions requested
- [ ] Webhook configured
- [ ] Page access token valid
- [ ] Testing complete

#### Performance:
- [ ] Load testing completed
- [ ] Performance metrics met
- [ ] Cache system active
- [ ] Error handling tested
- [ ] System stable under load

#### Monitoring:
- [ ] UptimeRobot active
- [ ] Telegram alerts working
- [ ] Health checks functional
- [ ] Error monitoring active
- [ ] Backup system verified

#### Review Process:
- [ ] Review team ready
- [ ] Review schedule set
- [ ] Review templates prepared
- [ ] Escalation process defined
- [ ] Feedback mechanism ready

### Go-Live Decision:

#### Go Criteria:
```
✅ All pre-go-live items checked
✅ No critical issues found
✅ Performance acceptable
✅ Security measures in place
✅ Monitoring operational
✅ Review process ready
✅ Team available for support
```

#### Rollback Plan:
```
❌ If critical issues found:
1. Revert to previous stable version
2. Disable new features
3. Communicate with users
4. Fix issues
5. Re-test
6. Re-deploy
```

### Post-Go-Live Monitoring:

#### First 24 Hours:
```
✅ Monitor service health hourly
✅ Check error logs frequently
✅ Review user feedback
✅ Verify all systems stable
✅ Prepare for quick fixes
```

#### First Week:
```
✅ Daily system health review
✅ Daily safety review
✅ Performance monitoring
✅ User feedback collection
✅ Issue tracking and resolution
```

#### First Month:
```
✅ Weekly system review
✅ Monthly performance analysis
✅ User satisfaction survey
✅ System optimization based on data
✅ Planning for improvements
```

---

## Contact Information

### Support Team:
```
Primary: [Your Name]
Email: [your-email@domain.com]
Phone: [your-phone-number]
```

### Emergency Contacts:
```
Technical: [technical-contact]
Medical: [medical-contact]
Facebook: [facebook-contact]
```

### Documentation:
```
System Overview: README.md
Test Plan: TEST_PLAN.md
Optimization Guide: OPTIMIZATION_GUIDE.md
Safety Guide: SAFETY_CHECK_GUIDE.md
```

---

## Sign-Off

### Pre-Go-Live Sign-Off:
```
System Owner: ________________ Date: ________
Technical Lead: ________________ Date: ________
Medical Advisor: ________________ Date: ________
Quality Assurance: _____________ Date: ________
```

### Go-Live Authorization:
```
Authorized by: ________________ Date: ________
Position: ______________________
Signature: _____________________
```

---

## Post-Go-Live Review

### 30-Day Review:
```
Review Date: ________________
System Performance: _____________
User Satisfaction: ______________
Issues Resolved: ________________
Improvements Made: ______________
Next Review Date: _______________
```

This checklist ensures a systematic and safe transition to production environment with proper security, monitoring, and quality assurance measures in place.